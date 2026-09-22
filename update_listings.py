#!/usr/bin/env python3
"""PayPay Flea Market scraper (requests + BeautifulSoup - simple HTML structure)"""

import json
import re
import sys
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
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def scrape_search_results(keyword: str) -> list:
    """検索ページから出品情報を抽出"""
    try:
        search_url = f"https://www.paypayfleamarket.yahoo.co.jp/search?query={quote(keyword)}"
        print(f"Scraping {keyword}...", file=sys.stderr)

        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"  Status {response.status_code}", file=sys.stderr)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # 価格情報を含むパターンを探す
        for item_elem in soup.find_all(["div", "li"], limit=10):
            text = item_elem.get_text(strip=True)

            # 価格パターンを抽出
            price_match = re.search(r'¥([\d,]+)', text)
            if not price_match:
                continue

            price = int(price_match.group(1).replace(",", ""))

            # タイトル抽出
            title_elem = item_elem.find("a")
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)[:50]

            # 除外キーワード確認
            if any(kw in title for kw in EXCLUDE_KEYWORDS):
                continue

            url = title_elem.get("href", search_url)
            if not url.startswith("http"):
                url = f"https://www.paypayfleamarket.yahoo.co.jp{url}"

            results.append({
                "title": title,
                "price": price,
                "url": url,
            })

            if len(results) >= TOP_N:
                break

        print(f"  ✓ {len(results)} items", file=sys.stderr)
        return results

    except Exception as e:
        print(f"  Error: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
        return []

def main():
    """メイン処理"""
    data = {}
    success_count = 0

    for i, keyword in enumerate(CARD_KEYWORDS, 1):
        print(f"({i}/{len(CARD_KEYWORDS)}) {keyword}", file=sys.stderr)
        results = scrape_search_results(keyword)
        if results:
            data[keyword] = results
            success_count += 1

    # スクレイピング結果がある場合のみ更新
    if success_count > 0:
        with open("listings.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"OK: {success_count}/{len(CARD_KEYWORDS)} scraped", file=sys.stderr)
    else:
        print(f"WARNING: No data scraped, keeping existing listings.json", file=sys.stderr)

if __name__ == "__main__":
    main()
