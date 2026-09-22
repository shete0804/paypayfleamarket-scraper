#!/usr/bin/env python3
"""PayPay フリマから最新値段を自動取得して listings.json を更新"""

import json
import re
import sys
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

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
]

TOP_N = 3

def scrape_card(keyword: str) -> list:
    """PayPay から最新値段を取得"""
    try:
        url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        response = requests.get(url, headers=headers, timeout=10)
        print(f"DEBUG: Status={response.status_code}, Content-Length={len(response.content)}", file=sys.stderr)

        soup = BeautifulSoup(response.content, "html.parser")

        items = soup.find_all("a", href=re.compile(r"/item/"))
        print(f"DEBUG: 見つかった <a> タグ数: {len(items)}", file=sys.stderr)

        if len(items) == 0:
            # HTML の最初の 500 文字をデバッグ出力
            print(f"DEBUG: HTML の最初の 500 文字: {response.content[:500].decode('utf-8', errors='ignore')}", file=sys.stderr)

        results = []
        for i, item in enumerate(items):
            if len(results) >= TOP_N:
                break

            text = item.get_text(strip=True)
            print(f"DEBUG: アイテム {i+1}: {text[:60]}", file=sys.stderr)

            # 除外キーワード判定
            if any(kw in text.lower() for kw in EXCLUDE_KEYWORDS):
                print(f"DEBUG:   → 除外キーワード検出", file=sys.stderr)
                continue

            # 価格を抽出
            price_match = re.search(r"¥([\d,]+)", text)
            if not price_match:
                print(f"DEBUG:   → 価格パターン不一致", file=sys.stderr)
                continue

            print(f"DEBUG:   → 価格マッチ成功", file=sys.stderr)
            price = int(price_match.group(1).replace(",", ""))
            href = item.get("href", "")

            if not href.startswith("http"):
                href = f"https://paypayfleamarket.yahoo.co.jp{href}"

            results.append({
                "title": text[:50],
                "price": price,
                "url": href,
            })

        return results
    except Exception as e:
        print(f"エラー ({keyword}): {e}", file=sys.stderr)
        return []

def update_listings():
    """listings.json を最新値段で更新"""
    data = {}

    for i, keyword in enumerate(CARD_KEYWORDS):
        print(f"取得中 ({i+1}/{len(CARD_KEYWORDS)}): {keyword}", file=sys.stderr)
        data[keyword] = scrape_card(keyword)
        time.sleep(0.5)

    # listings.json に保存
    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("listings.json を更新しました", file=sys.stderr)

if __name__ == "__main__":
    update_listings()
