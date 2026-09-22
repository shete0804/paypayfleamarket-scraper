#!/usr/bin/env python3
"""PayPay フリマから実数値を取得（Playwright 並列処理版）"""

import asyncio
import json
import re
import sys
from urllib.parse import quote

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

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
MAX_CONCURRENT = 5

async def scrape_card_with_playwright(browser, keyword: str) -> list:
    """Playwright でブラウザレンダリングを使用して価格を取得"""
    context = None
    page = None
    try:
        print(f"処理中: {keyword}", file=sys.stderr)
        context = await browser.new_context()
        page = await context.new_page()

        # 検索ページにアクセス
        url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
        await page.goto(url, wait_until="networkidle", timeout=10000)

        # 商品リンクを抽出
        item_links = await page.evaluate("""
            () => {
                return Array.from(document.querySelectorAll('a[href*="/item/"]'))
                    .map(a => a.href)
                    .filter(url => url.includes('/item/'))
                    .slice(0, 15);
            }
        """)
        print(f"見つかったリンク: {len(item_links)} 件", file=sys.stderr)

        results = []
        for href in item_links:
            if len(results) >= TOP_N:
                break

            try:
                await page.goto(href, wait_until="networkidle", timeout=8000)

                # ページテキストを取得
                text_content = await page.text_content("body")

                # タイトルを取得
                title_element = await page.query_selector("h1")
                if not title_element:
                    continue
                title = await title_element.text_content()
                title = title.strip() if title else ""

                # キーワード確認
                first_word = keyword.split()[0]
                if first_word not in title:
                    continue

                # 除外キーワード確認
                if any(kw in title.lower() for kw in EXCLUDE_KEYWORDS):
                    continue

                # 価格取得（¥XXXXX パターン）
                price_match = re.search(r"¥([\d,]+)", text_content)
                if not price_match:
                    continue

                try:
                    price = int(price_match.group(1).replace(",", ""))
                except ValueError:
                    continue

                if price == 0:
                    continue

                results.append({
                    "title": title[:50],
                    "price": price,
                    "url": href,
                })
                print(f"✓ {title[:40]} - ¥{price}", file=sys.stderr)

            except PlaywrightTimeoutError:
                print(f"⏱️ タイムアウト: {href[:60]}", file=sys.stderr)
                continue
            except Exception as e:
                print(f"❌ {str(e)[:50]}", file=sys.stderr)
                continue

        print(f"完了: {keyword} - {len(results)}/{TOP_N} 件", file=sys.stderr)
        return results

    except Exception as e:
        print(f"エラー ({keyword}): {str(e)[:80]}", file=sys.stderr)
        return []
    finally:
        if page:
            await page.close()
        if context:
            await context.close()

async def update_listings_async():
    """非同期で listings.json を更新"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        data = {}
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def scrape_with_semaphore(keyword):
            async with semaphore:
                result = await scrape_card_with_playwright(browser, keyword)
                return keyword, result

        tasks = [scrape_with_semaphore(keyword) for keyword in CARD_KEYWORDS]
        results = await asyncio.gather(*tasks)

        for keyword, listings in results:
            data[keyword] = listings

        await browser.close()

    # listings.json に保存
    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ listings.json を更新しました", file=sys.stderr)

def update_listings():
    """同期ラッパー"""
    asyncio.run(update_listings_async())

if __name__ == "__main__":
    update_listings()
