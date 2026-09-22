#!/usr/bin/env python3
"""PayPay フリマから実数値を取得（requests + BeautifulSoup 最適化版）"""

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
    "メガカイリューex SAR MEガドリームex",
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
    """PayPay フリマから実数値を取得（最適化版）"""
    try:
        url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
        print(f"検索中: {keyword}", file=sys.stderr)

        # リクエスト（タイムアウト短縮）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja-JP,ja;q=0.9",
        }

        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        print(f"Status: {response.status_code}", file=sys.stderr)

        # BeautifulSoup で解析
        soup = BeautifulSoup(response.content, "html.parser")

        # すべてのリンクを探す
        all_links = soup.find_all("a", href=True)
        item_links = [link["href"] for link in all_links if "/item/" in link["href"]]
        print(f"見つかったリンク: {len(item_links)} 件", file=sys.stderr)

        results = []
        for href in item_links[:15]:  # 最初の 15 個を試す
            if len(results) >= TOP_N:
                break

            try:
                if not href.startswith("http"):
                    href = f"https://paypayfleamarket.yahoo.co.jp{href}"

                # アイテムページ取得
                item_response = session.get(href, headers=headers, timeout=10)
                if item_response.status_code != 200:
                    continue

                item_soup = BeautifulSoup(item_response.content, "html.parser")

                # タイトル取得
                title_tag = item_soup.find("h1")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # キーワード確認
                first_word = keyword.split()[0]
                if first_word not in title:
                    continue

                # 除外キーワード確認
                if any(kw in title.lower() for kw in EXCLUDE_KEYWORDS):
                    continue

                # 価格取得（複数マッチから最初の価格）
                price_text = item_soup.get_text()
                price_match = re.search(r"¥([\d,]+)", price_text)
                if not price_match:
                    continue

                try:
                    price = int(price_match.group(1).replace(",", ""))
                except ValueError:
                    continue

                if price == 0:  # ¥0 は無効
                    continue

                results.append({
                    "title": title[:50],
                    "price": price,
                    "url": href,
                })
                print(f"✓ {title[:40]} - ¥{price}", file=sys.stderr)

            except Exception as e:
                print(f"アイテム処理: {str(e)[:50]}", file=sys.stderr)
                continue

        print(f"最終: {keyword} - {len(results)}/{TOP_N} 件", file=sys.stderr)
        return results

    except Exception as e:
        print(f"エラー ({keyword}): {str(e)[:80]}", file=sys.stderr)
        return []

def update_listings():
    """listings.json を更新"""
    data = {}

    for i, keyword in enumerate(CARD_KEYWORDS):
        print(f"処理中 ({i+1}/{len(CARD_KEYWORDS)}): {keyword}", file=sys.stderr)
        data[keyword] = scrape_card(keyword)
        time.sleep(0.3)  # rate limit 対策

    # listings.json に保存
    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("listings.json を更新しました", file=sys.stderr)

if __name__ == "__main__":
    update_listings()
