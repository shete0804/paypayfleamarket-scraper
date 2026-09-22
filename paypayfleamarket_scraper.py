#!/usr/bin/env python3
"""PayPay フリマ スクレイパー（requests + __NEXT_DATA__ 直接抽出）"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

CARD_KEYWORDS = [
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

EXCLUDE_KEYWORDS = [
    "セット", "2枚", "3枚", "4枚", "5枚", "10枚", "20枚",
    "5パック", "10パック", "Box", "ボックス", "まとめ売り",
    "福袋", "構築済みデッキ", "デッキ", "旧裏", "おまけ",
    "2P", "3P", "4P", "5P",
]

TOP_N = 3
JST = timezone(timedelta(hours=9))
TIMEOUT_SEC = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

def extract_next_data(html: str) -> dict:
    """HTML から __NEXT_DATA__ JSON を抽出"""
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}

def get_listings_from_next_data(next_data: dict, keyword: str) -> list:
    """__NEXT_DATA__ から商品一覧を抽出"""
    results = []
    try:
        props = next_data.get("props", {}).get("pageProps", {})
        items = props.get("searchResults", {}).get("items", [])

        for item in items:
            if len(results) >= TOP_N:
                break

            title = item.get("title", "").lower()

            # 除外キーワード判定
            if any(kw in title for kw in EXCLUDE_KEYWORDS):
                continue

            price = item.get("price")
            if not price:
                continue

            url = item.get("url", "")
            if not url.startswith("http"):
                url = f"https://paypayfleamarket.yahoo.co.jp{url}"

            results.append({
                "title": item.get("title", ""),
                "price": int(price) if isinstance(price, (int, float)) else 0,
                "url": url,
            })
    except Exception as e:
        print(f"Error parsing __NEXT_DATA__: {e}", file=sys.stderr)

    return results

def scrape_card(keyword: str) -> list:
    """1 カード分を取得"""
    try:
        url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
        headers = {"User-Agent": USER_AGENT}

        response = requests.get(url, headers=headers, timeout=TIMEOUT_SEC)
        response.raise_for_status()

        next_data = extract_next_data(response.text)
        if not next_data:
            print(f"警告: {keyword} - __NEXT_DATA__ が見つかりません", file=sys.stderr)
            return []

        return get_listings_from_next_data(next_data, keyword)
    except Exception as e:
        print(f"スクレイピングエラー ({keyword}): {type(e).__name__}: {e}", file=sys.stderr)
        return []

def fetch_all() -> dict:
    """全カードを取得"""
    results = {}
    for keyword in CARD_KEYWORDS:
        results[keyword] = scrape_card(keyword)
    return results

def fmt_price(price):
    return f"¥{price:,}"

def now_jst():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

def send_discord(payload):
    if not DISCORD_WEBHOOK_URL:
        print("Discord webhook not set, skipping send", file=sys.stderr)
        return
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print("Discord sent OK")
    except Exception as e:
        print(f"Discord send error: {e}", file=sys.stderr)

def main():
    results = fetch_all()

    if not any(results.values()):
        print("No listings found", file=sys.stderr)

    fields = []
    for keyword in CARD_KEYWORDS:
        items = results.get(keyword, [])
        if items:
            value = "\n".join(f"[{fmt_price(item['price'])}]({item['url']})" for item in items[:TOP_N])
        else:
            value = "登録なし"
        fields.append({"name": keyword, "value": value, "inline": False})

    embed = {
        "title": "PayPay フリマ MEGA シリーズ 価格情報",
        "description": f"最安 {TOP_N} 件 / {now_jst()}",
        "color": 0x003DA5,
        "fields": fields[:25],
        "footer": {"text": "6 時間ごと自動実行"},
    }

    send_discord({"embeds": [embed]})
    print("Done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
