#!/usr/bin/env python3
"""PayPay フリマから実数値を取得（Playwright で JavaScript レンダリング対応）"""

import json
import re
import sys
import asyncio
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

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

async def scrape_card(page, keyword: str) -> list:
    """Playwright で JavaScript レンダリング後に価格を取得"""
    try:
        url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
        print(f"検索中: {keyword}", file=sys.stderr)

        # ページロード
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # 商品リンク取得
        items = await page.locator('a[href*="/item/"]').all()
        print(f"見つかった商品: {len(items)} 件", file=sys.stderr)

        results = []
        for item in items[:10]:  # 最初の 10 個を試す
            if len(results) >= TOP_N:
                break

            try:
                # アイテムページへのリンク取得
                href = await item.get_attribute("href")
                if not href or "/item/" not in href:
                    continue

                item_url = f"https://paypayfleamarket.yahoo.co.jp{href}"

                # アイテムページを開く
                await page.goto(item_url, wait_until="networkidle", timeout=30000)

                # ページコンテンツ取得
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # タイトル取得
                title_tag = soup.find("h1")
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

                # 価格取得
                price_match = re.search(r"¥([\d,]+)", soup.get_text())
                if not price_match:
                    continue

                price = int(price_match.group(1).replace(",", ""))
                results.append({
                    "title": title[:50],
                    "price": price,
                    "url": item_url,
                })
                print(f"✓ {title[:40]} - ¥{price}", file=sys.stderr)

            except Exception as e:
                print(f"アイテム処理エラー: {e}", file=sys.stderr)
                continue

        print(f"最終: {keyword} - {len(results)}/{TOP_N} 件取得", file=sys.stderr)
        return results

    except Exception as e:
        print(f"エラー ({keyword}): {e}", file=sys.stderr)
        return []

async def main():
    """Playwright ブラウザで全カード取得"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        data = {}
        for i, keyword in enumerate(CARD_KEYWORDS):
            print(f"処理中 ({i+1}/{len(CARD_KEYWORDS)}): {keyword}", file=sys.stderr)
            data[keyword] = await scrape_card(page, keyword)

        await browser.close()

        # listings.json に保存
        with open("listings.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("listings.json を更新しました", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
