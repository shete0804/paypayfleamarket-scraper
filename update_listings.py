#!/usr/bin/env python3
"""PayPay Flea Market scraper (requests + BeautifulSoup - simple HTML structure)"""

import json
import re
import sys
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

# リトライ戦略
RETRIES = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
ADAPTER = HTTPAdapter(max_retries=RETRIES)

# ヘッダー（複数パターン）
HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja-JP,ja;q=0.9",
        "Referer": "https://www.yahoo.co.jp/",
    },
    {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja-JP,ja;q=0.9",
    },
]

def get_session(header_index=0):
    """リトライ機能付きセッションを作成"""
    session = requests.Session()
    session.mount("https://", ADAPTER)
    session.mount("http://", ADAPTER)
    session.headers.update(HEADERS_LIST[header_index % len(HEADERS_LIST)])
    return session

def scrape_search_results(keyword: str, header_index: int = 0) -> list:
    """検索ページから出品情報を抽出（リトライ＆セッション管理）"""
    try:
        search_url = f"https://www.paypayfleamarket.yahoo.co.jp/search?query={quote(keyword)}"
        print(f"[DEBUG] URL: {search_url}", file=sys.stderr)

        session = get_session(header_index)
        print(f"[DEBUG] Session created with header_index={header_index}", file=sys.stderr)

        print(f"[DEBUG] Making request...", file=sys.stderr)
        response = session.get(search_url, timeout=15)
        response.encoding = 'utf-8'

        print(f"[DEBUG] Response status: {response.status_code}", file=sys.stderr)
        if response.status_code != 200:
            print(f"[FAIL] Status {response.status_code}", file=sys.stderr)
            return []

        print(f"[DEBUG] Parsing HTML (length: {len(response.text)})", file=sys.stderr)
        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # 価格情報を含むパターンを探す
        for item_elem in soup.find_all(["div", "li", "a"], limit=20):
            text = item_elem.get_text(strip=True)

            # 価格パターンを抽出
            price_match = re.search(r'¥([\d,]+)', text)
            if not price_match:
                continue

            price = int(price_match.group(1).replace(",", ""))

            # タイトル抽出
            if item_elem.name == "a":
                title = item_elem.get_text(strip=True)[:50]
                url = item_elem.get("href", search_url)
            else:
                title_elem = item_elem.find("a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)[:50]
                url = title_elem.get("href", search_url)

            # 除外キーワード確認
            if any(kw in title for kw in EXCLUDE_KEYWORDS):
                continue

            if not url.startswith("http"):
                url = f"https://www.paypayfleamarket.yahoo.co.jp{url}"

            results.append({
                "title": title,
                "price": price,
                "url": url,
            })

            if len(results) >= TOP_N:
                break

        print(f"[SUCCESS] {len(results)} items found", file=sys.stderr)
        return results

    except Exception as e:
        import traceback
        print(f"[ERROR] {type(e).__name__}: {str(e)}", file=sys.stderr)
        print(f"[TRACEBACK]\n{traceback.format_exc()}", file=sys.stderr)
        return []

def main():
    """メイン処理"""
    # ログファイルに出力も同時に行う
    log_file = open("update_listings_debug.log", "w", encoding="utf-8")

    def log_print(msg):
        print(msg, file=sys.stderr)
        print(msg, file=log_file)
        log_file.flush()

    data = {}
    success_count = 0

    log_print(f"[START] Scraping {len(CARD_KEYWORDS)} cards")
    for i, keyword in enumerate(CARD_KEYWORDS, 1):
        log_print(f"({i}/{len(CARD_KEYWORDS)}) {keyword}")
        results = scrape_search_results(keyword)
        if results:
            data[keyword] = results
            success_count += 1
            log_print(f"  ✓ Success: {len(results)} items")
        else:
            log_print(f"  ✗ Failed: 0 items")

    # スクレイピング結果がある場合のみ更新
    log_print(f"[END] Total success: {success_count}/{len(CARD_KEYWORDS)}")
    if success_count > 0:
        with open("listings.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_print(f"✅ listings.json updated")
    else:
        log_print(f"⚠️ No data scraped, keeping existing listings.json")

    log_file.close()

if __name__ == "__main__":
    main()
