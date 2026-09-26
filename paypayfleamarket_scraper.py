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

def load_listings_paypay():
    """listings.json（PayPay）から価格を読み込み"""
    try:
        with open("listings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"listings.json の読み込みエラー: {e}", file=sys.stderr)
        return {}

def load_listings_mercari():
    """listings_mercari.json（メルカリ）から価格を読み込み"""
    try:
        with open("listings_mercari.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"listings_mercari.json の読み込みエラー: {e}", file=sys.stderr)
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

    paypay_listings = load_listings_paypay()
    mercari_listings = load_listings_mercari()

    if not paypay_listings and not mercari_listings:
        print("listings.json が見つかりません", file=sys.stderr)
        return 1

    fields = []
    for keyword in CARD_KEYWORDS:
        paypay_items = paypay_listings.get(keyword, [])
        mercari_items = mercari_listings.get(keyword, [])

        value_lines = []

        # PayPay 価格
        if paypay_items:
            paypay_prices = " / ".join(f"{fmt_price(item['price'])}" for item in paypay_items[:TOP_N])
            value_lines.append(f"🤖 PayPay: {paypay_prices}")

        # メルカリ価格
        if mercari_items:
            mercari_prices = " / ".join(f"{fmt_price(item['price'])}" for item in mercari_items[:TOP_N])
            value_lines.append(f"📱 メルカリ: {mercari_prices}")

        # 差額計算（最安値で比較）
        if paypay_items and mercari_items:
            paypay_min = min(item['price'] for item in paypay_items)
            mercari_min = min(item['price'] for item in mercari_items)
            diff = mercari_min - paypay_min
            if diff > 0:
                value_lines.append(f"💰 差額: PayPay が {fmt_price(diff)} 安い")
            elif diff < 0:
                value_lines.append(f"💰 差額: メルカリが {fmt_price(-diff)} 安い")
            else:
                value_lines.append(f"💰 差額: 同じ価格")

        if value_lines:
            value = "\n".join(value_lines)
        else:
            value = "登録なし"

        fields.append({"name": keyword, "value": value, "inline": False})

    embed = {
        "title": "PayPay × メルカリ カード価格比較",
        "description": f"最安値比較 / {now_jst()}",
        "color": 0x003DA5,
        "fields": fields[:25],
        "footer": {"text": "6 時間ごと自動実行"},
    }

    send_discord({"embeds": [embed]})
    print("Done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
