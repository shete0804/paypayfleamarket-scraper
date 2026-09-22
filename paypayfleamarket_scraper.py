#!/usr/bin/env python3
"""PayPay フリマ スクレイパー（Apify を使用）"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "").strip()

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

def is_single_card(title: str) -> bool:
    """タイトルからシングルカードかどうか判定"""
    title_lower = title.lower()
    for word in EXCLUDE_KEYWORDS:
        if word in title_lower:
            return False
    return True

def call_apify(keyword: str) -> list:
    """Apify で PayPay フリマを検索"""
    if not APIFY_TOKEN:
        print(f"警告: APIFY_TOKEN が設定されていません", file=sys.stderr)
        return []

    try:
        url = "https://api.apify.com/v2/acts/youfuxu~paypay-flea-japan-scraper/run-sync-get-dataset-items"

        params = {
            "token": APIFY_TOKEN,
        }

        payload = {
            "searchKeywords": [keyword],
            "maxItems": 10,
        }

        response = requests.post(url, json=payload, params=params, timeout=60)
        response.raise_for_status()

        items = response.json() if isinstance(response.json(), list) else []

        results = []
        for item in items[:TOP_N]:
            if not is_single_card(item.get("title", "")):
                continue

            price = item.get("price")
            if not price:
                continue

            results.append({
                "title": item.get("title", ""),
                "price": int(price) if isinstance(price, (int, float)) else 0,
                "url": item.get("url", ""),
            })

        return results[:TOP_N]
    except Exception as e:
        print(f"Apify エラー ({keyword}): {type(e).__name__}: {e}", file=sys.stderr)
        return []

def fetch_all() -> dict:
    """全カードを取得"""
    results = {}
    for keyword in CARD_KEYWORDS:
        print(f"取得中: {keyword}", file=sys.stderr)
        results[keyword] = call_apify(keyword)
    return results

def fmt_price(price):
    return f"¥{price:,}"

def now_jst():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

def send_discord(payload):
    if not DISCORD_WEBHOOK_URL:
        print("Discord webhook not set", file=sys.stderr)
        return
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print("Discord sent OK")
    except Exception as e:
        print(f"Discord error: {e}", file=sys.stderr)

def main():
    if not APIFY_TOKEN:
        print("環境変数 APIFY_TOKEN が必要です", file=sys.stderr)
        return 1

    if not DISCORD_WEBHOOK_URL:
        print("環境変数 DISCORD_WEBHOOK_URL が必要です", file=sys.stderr)
        return 1

    results = fetch_all()

    fields = []
    for keyword in CARD_KEYWORDS:
        items = results.get(keyword, [])
        if items:
            value = "\n".join(f"[{fmt_price(item['price'])}]({item['url']})" for item in items)
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
