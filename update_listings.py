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
    """PayPay から最新値段を取得（JSON-LDスキーマから URL 抽出）"""
    try:
        url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        response = requests.get(url, headers=headers, timeout=10)
        print(f"DEBUG: Status={response.status_code}", file=sys.stderr)

        html_text = response.content.decode('utf-8', errors='ignore')
        json_ld_match = re.search(r'<script type="application/ld\+json">([^<]+)</script>', html_text)

        if not json_ld_match:
            print(f"DEBUG: JSON-LD スキーマが見つかりません", file=sys.stderr)
            return []

        try:
            schemas = json.loads(json_ld_match.group(1))
            if not isinstance(schemas, list):
                schemas = [schemas]
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON パースエラー: {e}", file=sys.stderr)
            return []

        item_urls = []
        for schema in schemas:
            if schema.get("@type") == "ItemList" and "itemListElement" in schema:
                for item in schema["itemListElement"]:
                    if "url" in item:
                        item_urls.append(item["url"])

        print(f"DEBUG: JSON-LD から {len(item_urls)} 個の URL を抽出", file=sys.stderr)

        results = []
        for item_url in item_urls[:10]:
            if len(results) >= TOP_N:
                break

            try:
                item_response = requests.get(item_url, headers=headers, timeout=10)
                item_soup = BeautifulSoup(item_response.content, "html.parser")

                title_tag = item_soup.find("h1")
                title = title_tag.get_text(strip=True) if title_tag else "Unknown"

                price_match = re.search(r"¥([\d,]+)", item_soup.get_text())
                if not price_match:
                    continue

                if any(kw in title.lower() for kw in EXCLUDE_KEYWORDS):
                    continue

                price = int(price_match.group(1).replace(",", ""))
                results.append({
                    "title": title[:50],
                    "price": price,
                    "url": item_url,
                })

            except Exception as e:
                print(f"DEBUG: アイテム {item_url} 処理エラー: {e}", file=sys.stderr)
                continue

        print(f"DEBUG: 最終的に {len(results)} 個のアイテムを取得", file=sys.stderr)
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
