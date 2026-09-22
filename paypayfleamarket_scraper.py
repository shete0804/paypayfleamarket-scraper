#!/usr/bin/env python3
"""PayPay フリマ 価格レポート（listings.json から読み込み）"""

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
    """listings.json から価格を読み込み"""
    try:
        with open("listings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"listings.json の読み込みエラー: {e}", file=sys.stderr)
        return {}

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
    if not DISCORD_WEBHOOK_URL:
        print("環境変数 DISCORD_WEBHOOK_URL が必要です", file=sys.stderr)
        return 1

    listings = load_listings()
    if not listings:
        print("listings.json が見つかりません", file=sys.stderr)
        return 1

    fields = []
    for keyword in CARD_KEYWORDS:
        items = listings.get(keyword, [])
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
