#!/usr/bin/env python3
"""
PayPay フリマ MEGA シリーズ カード価格モニター
=============================================

Playwright を使用して PayPay Flea Market から実数値を取得し、
Discord に Embed 形式で通知する。

GitHub Actions から 6 時間ごとに実行される想定。

必要な環境変数:
    DISCORD_WEBHOOK_URL   Discord Incoming Webhook の URL

必要なライブラリ:
    requests              HTTP リクエスト送信
    playwright            Playwright for Python
"""

from __future__ import annotations

import os
import re
import sys
import time
import traceback
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

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
MAX_RETRIES = 3
NAV_TIMEOUT_MS = 30_000
RETRY_WAIT_SEC = 5

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

JST = timezone(timedelta(hours=9))

# 除外キーワード（セット販売、複数枚販売など）
EXCLUDE_KEYWORDS: list[str] = [
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
]

# PayPay Flea Market の検索 URL
SEARCH_URL_TEMPLATE = (
    "https://paypayfleamarket.yahoo.co.jp/search/{keyword}"
)


class PayPayBlockedError(RuntimeError):
    """PayPay のアクセスがブロックされた場合に送出する。"""


@dataclass
class Listing:
    card: str
    price: int
    url: str


# ---------------------------------------------------------------------------
# スクレイピング
# ---------------------------------------------------------------------------

def build_search_url(keyword: str) -> str:
    """PayPay Flea Market の検索 URL を構築"""
    escaped = urllib.parse.quote(keyword)
    return SEARCH_URL_TEMPLATE.format(keyword=escaped)


def looks_blocked(page: Page) -> bool:
    """bot 対策 / ブロック時に現れる特徴を検出する。"""
    if any(token in page.url.lower() for token in ("captcha", "datadome", "blocked")):
        return True

    body = page.content().lower()
    markers = (
        "captcha-delivery.com",
        "geo.captcha-delivery.com",
        "please enable javascript and cookies",
        "アクセスが集中しています",
        "一時的に利用できません",
    )
    return any(marker in body for marker in markers)


def is_single_card(title: str) -> bool:
    """タイトルからシングルカードかどうか判定する。"""
    title_lower = title.lower()

    for word in EXCLUDE_KEYWORDS:
        if word in title_lower:
            return False

    return True


def parse_listings(page: Page, card: str) -> list[Listing]:
    """検索結果ページから最大 TOP_N 件を取り出す。"""
    results: list[Listing] = []

    try:
        # PayPay のセレクタ複数候補
        selectors = [
            'a[href*="/item/"]',
            '[class*="itemCell"]',
            '[class*="item"][class*="card"]',
            'div[class*="item"]',
        ]

        items = None
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=5000)
                items = page.locator(selector)
                item_count = items.count()
                if item_count > 0:
                    print(f"セレクタ成功: {selector} (件数: {item_count})", file=sys.stderr)
                    break
            except Exception as e:
                print(
                    f"セレクタ失敗: {selector} - {type(e).__name__}",
                    file=sys.stderr,
                )
                items = None
                continue

        if items is None or items.count() == 0:
            print(
                f"警告: {card} - 有効なセレクタが見つかりません。",
                file=sys.stderr,
            )
            return results

        for i in range(items.count()):
            if len(results) >= TOP_N:
                break

            try:
                item = items.nth(i)

                # タイトルを取得
                title = ""
                try:
                    title = item.inner_text(timeout=1000)
                except Exception:
                    pass

                if not title:
                    continue

                # シングルカード判定
                if not is_single_card(title):
                    continue

                # URL を取得
                href = ""
                try:
                    href = item.get_attribute("href") or ""
                except Exception:
                    pass

                if not href:
                    try:
                        href = item.locator("a").first.get_attribute("href") or ""
                    except Exception:
                        pass

                if not href:
                    continue

                if href.startswith("/"):
                    href = "https://paypayfleamarket.yahoo.co.jp" + href

                # 価格を取得
                price_text = item.inner_text(timeout=1000).strip()
                match = re.search(r'(\d+(?:,\d+)*)\s*円', price_text)
                if not match:
                    continue

                try:
                    price = int(match.group(1).replace(',', ''))
                except ValueError:
                    continue

                results.append(Listing(card=card, price=price, url=href))

            except Exception as e:
                print(
                    f"アイテム処理エラー ({card}, インデックス {i}): {type(e).__name__}",
                    file=sys.stderr,
                )
                continue

    except Exception as e:
        print(
            f"parse_listings エラー ({card}): {type(e).__name__} - {e}",
            file=sys.stderr,
        )

    return results


def scrape_card(page: Page, keyword: str) -> list[Listing]:
    """1 カード分を最大 MAX_RETRIES 回リトライして取得する。"""
    last_err: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            page.goto(
                build_search_url(keyword),
                wait_until="networkidle",
                timeout=NAV_TIMEOUT_MS,
            )

            if looks_blocked(page):
                raise PayPayBlockedError(f"ブロックを検知 (keyword={keyword!r})")

            # ページが十分読み込まれるまで待機
            page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)

            return parse_listings(page, keyword)

        except PayPayBlockedError:
            raise
        except Exception as err:
            last_err = err
            print(
                f"[retry {attempt}/{MAX_RETRIES}] {keyword}: {type(err).__name__}: {err}",
                file=sys.stderr,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SEC)

    raise RuntimeError(f"{keyword!r} を {MAX_RETRIES} 回試行して取得失敗: {last_err}")


def fetch_all() -> tuple[dict[str, list[Listing]], dict[str, str]]:
    """全カードを順に取得する。ブロック検知時は即座に例外を送出する。"""
    results: dict[str, list[Listing]] = {}
    errors: dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="ja-JP")
        page = context.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)

        try:
            for keyword in CARD_KEYWORDS:
                try:
                    results[keyword] = scrape_card(page, keyword)
                except PayPayBlockedError:
                    raise
                except Exception as err:
                    errors[keyword] = str(err)
        finally:
            browser.close()

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
    """カードごとに最安 TOP_N 件をまとめた Embed を 1 通送る。"""
    fields = []
    for keyword in CARD_KEYWORDS:
        listings = results.get(keyword, [])
        if listings:
            value = "\n".join(
                f"[{_fmt_price(l.price)}]({l.url})" for l in listings
            )
        elif keyword in errors:
            value = f"⚠️ 取得失敗: {errors[keyword][:200]}"
        else:
            value = "販売中の出品なし"
        fields.append({"name": keyword, "value": value, "inline": False})

    embed = {
        "title": "PayPay フリマ MEGA シリーズ 最安値レポート",
        "description": f"販売中・最安 {TOP_N} 件 / {_now_jst()}",
        "color": 0x003DA5,
        "fields": fields[:25],  # Discord の Embed field 上限
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
    except PayPayBlockedError as err:
        post_failure(
            "PayPay 取得失敗",
            f"{err}\n\nBot 対策によりブロックされた可能性があります。",
        )
        return 1
    except Exception:
        post_failure("スクレイピング失敗", traceback.format_exc())
        return 1

    # 全カード失敗 = 実質的な失敗として扱う
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
