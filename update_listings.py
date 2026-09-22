#!/usr/bin/env python3
"""PayPay Flea Market - JSON-LD スキーマから価格取得"""

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
    "メガカイリューex SAR メガドリームex",
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
FALLBACK_DATA = {}

def scrape_card(keyword: str) -> list:
    """PayPay から JSON-LD スキーマを使って価格取得"""
    try:
        url = f"https://paypayfleamarket.yahoo.co.jp/search?keyword={quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        print(f"Fetching {keyword}...", file=sys.stderr)
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html_text = response.text
        json_ld_match = re.search(r'<script type="application/ld\+json">([^<]+)</script>', html_text)

        if not json_ld_match:
            print(f"JSON-LD not found for {keyword}", file=sys.stderr)
            return []

        try:
            schemas = json.loads(json_ld_match.group(1))
            if not isinstance(schemas, list):
                schemas = [schemas]
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}", file=sys.stderr)
            return []

        item_urls = []
        for schema in schemas:
            if schema.get("@type") == "ItemList" and "itemListElement" in schema:
                for item in schema["itemListElement"]:
                    if "url" in item:
                        item_urls.append(item["url"])

        print(f"Found {len(item_urls)} URLs from JSON-LD", file=sys.stderr)

        results = []
        for item_url in item_urls[:10]:
            if len(results) >= TOP_N:
                break

            try:
                item_response = requests.get(item_url, headers=headers, timeout=15)
                item_soup = BeautifulSoup(item_response.content, "html.parser")

                title_tag = item_soup.find("h1")
                title = title_tag.get_text(strip=True) if title_tag else "Unknown"

                price_match = re.search(r"¥([\d,]+)", item_soup.get_text())
                if not price_match:
                    continue

                if any(kw in title for kw in EXCLUDE_KEYWORDS):
                    continue

                price = int(price_match.group(1).replace(",", ""))
                results.append({
                    "title": title[:50],
                    "price": price,
                    "url": item_url,
                })

            except Exception as e:
                print(f"Error processing {item_url}: {e}", file=sys.stderr)
                continue

        print(f"✓ {keyword}: {len(results)} items", file=sys.stderr)
        return results

    except Exception as e:
        print(f"Error ({keyword}): {e}", file=sys.stderr)
        return []

def main():
    data = {}
    success_count = 0

    for i, keyword in enumerate(CARD_KEYWORDS):
        print(f"Processing ({i+1}/{len(CARD_KEYWORDS)}): {keyword}", file=sys.stderr)
        results = scrape_card(keyword)
        if results:
            data[keyword] = results
            success_count += 1
        else:
            data[keyword] = FALLBACK_DATA.get(keyword, [])
        time.sleep(1)

    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK: {success_count}/{len(CARD_KEYWORDS)} scraped", file=sys.stderr)

if __name__ == "__main__":
    main()
