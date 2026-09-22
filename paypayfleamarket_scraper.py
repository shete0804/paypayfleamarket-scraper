#!/usr/bin/env python3
"""PayPay フリマ スクレイパー（requests + HTML 直接解析）"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import time

import requests
from bs4 import BeautifulSoup

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
MAX_RETRIES = 3
RETRY_WAIT = 3

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def is_single_card(title: str) -> bool:
    """タイトルからシングルカードかどうか判定"""
    title_lower = title.lower()
    for word in EXCLUDE_KEYWORDS:
        if word in title_lower:
            return False
    return True

def scrape_card(keyword: str) -> list:
    """1 カード分を requests で取得"""
    url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"

    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept-Language": "ja-JP,ja;q=0.9",
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            results = []

            # 複数のセレクタを試す
            for item_elem in soup.find_all("a", href=re.compile(r"/item/|フリマ")):
                if len(results) >= TOP_N:
                    break

                href = item_elem.get("href", "")
                if not href or "/item/" not in href:
                    continue

                # タイトルと価格を抽出
                text = item_elem.get_text(separator=" ", strip=True)

                if not text:
                    continue

                # シングルカード判定
                if not is_single_card(text):
                    continue

                # 価格を抽出（¥XXXX 形式）
                price_match = re.search(r"¥([\d,]+)", text)
                if not price_match:
                    continue

                try:
                    price = int(price_match.group(1).replace(",", ""))
                except ValueError:
                    continue

                # URL を完成させる
                if not href.startswith("http"):
                    href = f"https://paypayfleamarket.yahoo.co.jp{href}"

                results.append({
                    "title": text[:50],  # タイトルを最初の 50 文字に制限
                    "price": price,
                    "url": href,
                })

            if results:
                return results

        except requests.exceptions.RequestException as e:
            print(f"[retry {attempt + 1}/{MAX_RETRIES}] {keyword}: {type(e).__name__}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_WAIT)
        except Exception as e:
            print(f"[retry {attempt + 1}/{MAX_RETRIES}] {keyword}: {type(e).__name__}: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_WAIT)

    return []

def fetch_all() -> dict:
    """全カードを取得"""
    results = {}
    for i, keyword in enumerate(CARD_KEYWORDS):
        print(f"取得中 ({i+1}/{len(CARD_KEYWORDS)}): {keyword}", file=sys.stderr)
        results[keyword] = scrape_card(keyword)
        time.sleep(1)  # サーバー負荷軽減
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
    if not DISCORD_WEBHOOK_URL:
        print("環境変数 DISCORD_WEBHOOK_URL が必要です", file=sys.stderr)
        return 1

    print("PayPay フリマをスクレイピング中...", file=sys.stderr)
    results = fetch_all()

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
