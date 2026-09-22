#!/usr/bin/env python3
"""
PayPay フリマ スクレイパー
========================

Playwright を使用して PayPay Flea Market の実数値を取得し、
Discord に通知する。

GitHub Actions から 6 時間ごとに実行される想定。

必要な環境変数:
    DISCORD_WEBHOOK_URL   Discord Incoming Webhook の URL

必要なライブラリ:
    requests              HTTP リクエスト送信
    playwright            Playwright for Python
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from datetime import datetime, timedelta, timezone

import requests
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

CARD_KEYWORDS: list[str] = [
    "メガルカリオex MUR メガブレイブ",
    "リーリエの決心 SAR メガブレイブ",
    "メガサーナイトex MUR メガシンフォニア",
    "メガサーナイトex SAR メガシンフォニア",
    "メガリザードンXex MUR インフェルノX",
    "メガリザードンXex SAR インフェルノX",
    "メガカイリューex MUR MEGAドリームex",
    "ピカチュウex SAR MEGAドリームex",
    "ロケット団のミュウツーex SAR MEGAドリームex",
    "メガゲンガーex SAR MEGAドリームex",
    "メガカイリューex SAR MEGAドリームex",
    "メガジガルデex MUR ムニキスゼロ",
    "ニャースex SAR ムニキスゼロ",
    "メイのはげまし SAR ムニキスゼロ",
    "メガゲッコウガex MUR ニンジャスピナー",
    "メガゲッコウガex SAR ニンジャスピナー",
    "メガダークライex MUR アビスアイ",
    "メガダークライex SAR アビスアイ",
]

TOP_N = 3

JST = timezone(timedelta(hours=9))

NAV_TIMEOUT_MS = 60000
RETRY_WAIT_SEC = 2
MAX_RETRIES = 2
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

EXCLUDE_KEYWORDS: set[str] = {
    "セット",
    "2枚",
    "3枚",
    "4枚",
    "5枚",
    "10枚",
    "20枚",
    "5パック",
    "10パック",
    "Box",
    "ボックス",
    "まとめ売り",
    "福袋",
    "構築済みデッキ",
    "デッキ",
    "旧裏",
    "おまけ",
    "2P",
    "3P",
    "4P",
    "5P",
}


class Listing:
    def __init__(self, card: str, price: int, url: str):
        self.card = card
        self.price = price
        self.url = url


# ---------------------------------------------------------------------------
# 商品フィルタリング
# ---------------------------------------------------------------------------


def is_single_card(title: str) -> bool:
    title_lower = title.lower()
    return not any(keyword in title_lower for keyword in EXCLUDE_KEYWORDS)


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------


def build_search_url(keyword: str) -> str:
    """PayPay Flea Market の検索 URL を構築"""
    escaped = keyword.replace(" ", "%20")
    return f"https://paypayfleamarket.yahoo.co.jp/search/{escaped}"


def extract_price(text: str) -> int:
    """テキストから価格を抽出（¥XXXXX 形式）"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        match = re.search(r"(\d+(?:,\d+)*)\s*円", line)
        if match:
            price_str = match.group(1).replace(",", "")
            try:
                return int(price_str)
            except ValueError:
                continue
    return 0


def parse_listings(page, keyword: str) -> list[Listing]:
    """PayPay ページから商品リスティングを抽出"""
    results = []
    processed = 0

    try:
        links = page.locator('a[href*="/item/"]')
        count = links.count()
        print(f"  見つかったリンク数: {count}", file=sys.stderr)

        for index in range(count):
            if processed >= TOP_N:
                break

            try:
                link = links.nth(index)
                href = link.get_attribute("href") or ""

                # タイトルを取得（img の alt 属性）
                img = link.locator("img[alt]").first
                title = (img.get_attribute("alt") or "").strip()

                if not title or not is_single_card(title):
                    processed += 1
                    continue

                # URL を絶対 URL に変換
                if href.startswith("http"):
                    url = href
                else:
                    url = f"https://paypayfleamarket.yahoo.co.jp{href}"

                # 価格を取得
                price_text = link.inner_text(timeout=5000)
                price = extract_price(price_text)

                if price > 0:
                    results.append(Listing(card=keyword, price=price, url=url))
                    processed += 1

            except Exception as e:
                print(f"  アイテムパース失敗: {e}", file=sys.stderr)
                continue

    except Exception as e:
        print(f"  ページパース失敗: {e}", file=sys.stderr)

    return results[:TOP_N]


def scrape_card(page, keyword: str) -> list[Listing]:
    """1 カード分を最大 MAX_RETRIES 回リトライして取得する"""
    last_err: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            page.goto(
                build_search_url(keyword),
                wait_until="domcontentloaded",
                timeout=NAV_TIMEOUT_MS,
            )
            page.wait_for_timeout(2000)

            return parse_listings(page, keyword)

        except Exception as err:
            last_err = err
            print(f"[retry {attempt}/{MAX_RETRIES}] {keyword}: {err}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                import time
                time.sleep(RETRY_WAIT_SEC)

    raise RuntimeError(
        f"{keyword!r} を {MAX_RETRIES} 回試行して取得失敗: {last_err}"
    )


def fetch_all() -> tuple[dict[str, list[Listing]], dict[str, str]]:
    """全カードを順に Playwright で取得する"""
    results: dict[str, list[Listing]] = {}
    errors: dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        page = context.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)

        try:
            for keyword in CARD_KEYWORDS:
                try:
                    print(f"取得中: {keyword}", file=sys.stderr)
                    results[keyword] = scrape_card(page, keyword)
                    print(f"  {len(results[keyword])}件取得", file=sys.stderr)
                except Exception as err:
                    error_msg = f"取得失敗: {type(err).__name__}: {str(err)[:100]}"
                    errors[keyword] = error_msg
                    print(f"  {error_msg}", file=sys.stderr)
        finally:
            try:
                browser.close()
            except Exception as e:
                print(f"ブラウザクローズエラー: {e}", file=sys.stderr)

    return results, errors


# ---------------------------------------------------------------------------
# Discord 通知
# ---------------------------------------------------------------------------


def _now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def _fmt_price(price: int) -> str:
    return f"¥{price:,}"


def _send(payload: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL 未設定のため送信をスキップ", file=sys.stderr)
        return
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    resp.raise_for_status()


def post_report(results: dict[str, list[Listing]], errors: dict[str, str]) -> None:
    fields = []
    for keyword in CARD_KEYWORDS:
        listings = results.get(keyword, [])
        if listings:
            value = "\n".join(f"[{_fmt_price(l.price)}]({l.url})" for l in listings)
        elif keyword in errors:
            value = f"⚠️ 取得失敗: {errors[keyword][:200]}"
        else:
            value = "販売中の出品なし"
        fields.append({"name": keyword, "value": value, "inline": False})

    embed = {
        "title": "PayPay フリマ MEGA シリーズ 最安値レポート",
        "description": f"販売中・最安 {TOP_N} 件 / {_now_jst()}",
        "color": 0x003DA5,
        "fields": fields[:25],
        "footer": {"text": "6 時間ごと自動実行"},
    }
    _send({"embeds": [embed]})


def post_failure(title: str, detail: str) -> None:
    embed = {
        "title": title,
        "description": f"```\n{detail[:3800]}\n```",
        "color": 0xFF0000,
        "footer": {"text": _now_jst()},
    }
    _send({"embeds": [embed]})


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def main() -> int:
    if not DISCORD_WEBHOOK_URL:
        print("環境変数 DISCORD_WEBHOOK_URL が必要です", file=sys.stderr)
        return 1

    try:
        results, errors = fetch_all()
    except Exception:
        post_failure("スクレイピング失敗", traceback.format_exc())
        return 1

    if errors and len(errors) == len(CARD_KEYWORDS):
        detail = "\n".join(f"- {k}: {v}" for k, v in errors.items())
        post_failure("スクレイピング失敗", detail)
        return 1

    post_report(results, errors)

    if errors:
        print(f"{len(errors)} 件のカードで取得失敗", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
