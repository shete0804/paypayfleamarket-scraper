#!/usr/bin/env python3
"""
PayPay フリマ MEGA シリーズ カード価格モニター
============================================

対象カードごとに PayPay フリマ検索を実行し、「販売中」かつ「価格の安い順」で
上位 3 件（カード名・価格・URL）を取得して Discord に Embed 形式で通知する。

GitHub Actions から 6 時間ごとに実行される想定。

必要な環境変数:
    DISCORD_WEBHOOK_URL   Discord Incoming Webhook の URL

必要なライブラリ:
    selenium              ブラウザ自動化
    requests              HTTP リクエスト送信
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1550012278592638996/_ecmZfZm4Xq7cOwWPEVrp-iXSVs1t7B2Kv3PKERsMpC0T9tzSPxUMfiGxTvMo0BvjyHb").strip()

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


@dataclass
class Listing:
    card: str
    price: int
    url: str


# ---------------------------------------------------------------------------
# 商品フィルタリング
# ---------------------------------------------------------------------------


def is_single_card(title: str) -> bool:
    title_lower = title.lower()
    return not any(keyword in title_lower for keyword in EXCLUDE_KEYWORDS)


# ---------------------------------------------------------------------------
# PayPay フリマ検索
# ---------------------------------------------------------------------------


def search_card(keyword: str) -> list[Listing]:
    listings: list[Listing] = []

    try:
        print(f"検索中: {keyword}", file=sys.stderr)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/usr/bin/chromium-browser"

        driver = webdriver.Chrome(options=chrome_options)

        try:
            url = f"https://www.paypayfleamarket.yahoo.co.jp/search?keyword={urlencode({'q': keyword})}&sort=score"
            driver.get(url)

            wait = WebDriverWait(driver, 10)
            wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".ProductCard__title")
                )
            )

            items = driver.find_elements(By.CSS_SELECTOR, ".ProductCard")

            for item in items:
                if len(listings) >= TOP_N:
                    break

                try:
                    title_elem = item.find_element(By.CSS_SELECTOR, ".ProductCard__title")
                    title = title_elem.text

                    if not is_single_card(title):
                        print(f"除外: {title}", file=sys.stderr)
                        continue

                    price_elem = item.find_element(
                        By.CSS_SELECTOR, ".ProductCard__priceWrapper"
                    )
                    price_text = price_elem.text.replace("¥", "").replace(",", "")

                    try:
                        price = int(price_text)
                    except ValueError:
                        print(f"無効な価格: {title} ({price_text})", file=sys.stderr)
                        continue

                    link_elem = item.find_element(By.CSS_SELECTOR, "a")
                    url = link_elem.get_attribute("href")

                    if not url.startswith("http"):
                        url = "https://www.paypayfleamarket.yahoo.co.jp" + url

                    listings.append(Listing(card=keyword, price=price, url=url))
                    print(
                        f"取得: {title} - ¥{price:,}",
                        file=sys.stderr,
                    )

                except Exception as e:
                    print(
                        f"アイテム処理エラー ({keyword}): {type(e).__name__}: {e}",
                        file=sys.stderr,
                    )
                    continue

            print(f"完了: {keyword} ({len(listings)} 件)", file=sys.stderr)

        finally:
            driver.quit()

    except Exception as e:
        print(
            f"検索エラー ({keyword}): {type(e).__name__}: {e}",
            file=sys.stderr,
        )

    return listings


def fetch_all() -> tuple[dict[str, list[Listing]], dict[str, str]]:
    results: dict[str, list[Listing]] = {}
    errors: dict[str, str] = {}

    for keyword in CARD_KEYWORDS:
        try:
            result = search_card(keyword)
            results[keyword] = result
        except Exception as e:
            errors[keyword] = str(e)

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

