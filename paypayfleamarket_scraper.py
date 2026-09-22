#!/usr/bin/env python3
"""PayPay フリマ スクレイパー（JSON ベース）"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

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

TOP_N = 3
JST = timezone(timedelta(hours=9))

def load_listings():
    """listings.json を読み込む"""
    try:
        with open("listings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR loading listings.json: {e}")
        return {}

def fmt_price(price):
    return f"¥{price:,}"

def now_jst():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

def send_discord(payload):
    if not DISCORD_WEBHOOK_URL:
        print("Discord webhook not set, skipping send")
        return
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print(f"Discord sent OK")
    except Exception as e:
        print(f"Discord send error: {e}")

def main():
    listings = load_listings()
    if not listings:
        print("No listings data")
        return 1

    # Build embed
    fields = []
    for keyword in CARD_KEYWORDS:
        if keyword in listings:
            items = listings[keyword][:TOP_N]
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
