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
    """PayPay から最新値段を取得（シンプルな URL 抽出）"""
    try:
        url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        response = requests.get(url, headers=headers, timeout=10)
        print(f"検索中: {keyword} - Status {response.status_code}", file=sys.stderr)

        html_text = response.content.decode('utf-8', errors='ignore')

        # /item/ パターンのURLを抽出
        item_links = re.findall(r'href="(/item/\w+)"', html_text)
        print(f"DEBUG: 見つかった /item/ リンク: {len(item_links)}", file=sys.stderr)

        if not item_links:
            # 別パターン: シングルクォート
            item_links = re.findall(r"href='(/item/\w+)'", html_text)
            print(f"DEBUG: シングルクォート検索: {len(item_links)}", file=sys.stderr)

        results = []
        for item_path in item_links[:10]:  # 最初の10個を試す
            if len(results) >= TOP_N:
                break

            try:
                item_url = f"https://paypayfleamarket.yahoo.co.jp{item_path}"
                item_response = requests.get(item_url, headers=headers, timeout=10)

                if item_response.status_code != 200:
                    continue

                item_soup = BeautifulSoup(item_response.content, "html.parser")

                # タイトル取得
                title_tag = item_soup.find("h1")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)

                # キーワード確認（大まかに）
                first_word = keyword.split()[0]
                if first_word not in title:
                    continue

                # 除外キーワード確認
                if any(kw in title.lower() for kw in EXCLUDE_KEYWORDS):
                    continue

                # 価格取得
                price_match = re.search(r"¥([\d,]+)", item_soup.get_text())
                if not price_match:
                    continue

                price = int(price_match.group(1).replace(",", ""))
                results.append({
                    "title": title[:50],
                    "price": price,
                    "url": item_url,
                })
                print(f"DEBUG: ✓ {title[:40]} - ¥{price}", file=sys.stderr)

            except Exception as e:
                print(f"DEBUG: アイテム処理エラー: {e}", file=sys.stderr)
                continue

        print(f"最終結果: {keyword} - {len(results)}/{TOP_N} 件取得", file=sys.stderr)
        return results

    except Exception as e:
        print(f"エラー ({keyword}): {e}", file=sys.stderr)
        return []

def update_listings():
    """listings.json を最新値段で更新"""
    data = {}

    for i, keyword in enumerate(CARD_KEYWORDS):
        data[keyword] = scrape_card(keyword)
        time.sleep(0.5)

    # listings.json に保存
    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("listings.json を更新しました", file=sys.stderr)

if __name__ == "__main__":
    update_listings()
