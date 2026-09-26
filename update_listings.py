#!/usr/bin/env python3
"""PayPay Flea Market scraper (Playwright - Chromium で実数値取得)"""

import asyncio
import json
import re
import sys
from urllib.parse import quote

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


def log_print(msg):
    """ログ出力"""
    print(msg, file=sys.stderr)


async def scrape_keyword(page, keyword: str) -> list:
    """キーワード検索のスクレイピング"""
    try:
        search_url = f"https://www.paypayfleamarket.yahoo.co.jp/search?query={quote(keyword)}"
        log_print(f"[LOAD] {search_url}")
        await page.goto(search_url, wait_until="networkidle")

        # ページ読み込み待機
        log_print(f"[WAIT] ページ読み込み中...")
        await page.wait_for_timeout(2000)

        results = []

        # 商品リスト要素を探す（複数のセレクタを試す）
        selectors = [
            "div[data-testid='product-card']",
            "div[class*='ProductCard']",
            "li[class*='product']",
            "article",
        ]

        items = None
        for selector in selectors:
            try:
                items = await page.query_selector_all(selector)
                if items:
                    log_print(f"[FOUND] セレクタ '{selector}' で {len(items)} 件見つかりました")
                    break
            except:
                continue

        if not items:
            log_print(f"[FAIL] 商品要素が見つかりません")
            return []

        # 価格情報を抽出
        for item in items[:20]:
            try:
                # テキスト取得
                text = await item.text_content()
                if not text:
                    continue

                # 価格抽出
                price_match = re.search(r'¥([\d,]+)', text)
                if not price_match:
                    continue

                price = int(price_match.group(1).replace(",", ""))

                # タイトル抽出
                title_elem = await item.query_selector("h2, h3, [class*='title'], a")
                if title_elem:
                    title = await title_elem.text_content()
                    title = (title or "").strip()[:50]
                else:
                    title = text.split('\n')[0][:50]

                if not title:
                    continue

                # URL抽出
                link = await item.query_selector("a")
                url = ""
                if link:
                    url = await link.get_attribute("href") or ""

                if not url.startswith("http"):
                    url = f"https://www.paypayfleamarket.yahoo.co.jp{url}"

                # フィルタリング
                if any(kw in title for kw in EXCLUDE_KEYWORDS):
                    continue

                results.append({
                    "title": title,
                    "price": price,
                    "url": url,
                })

                if len(results) >= TOP_N:
                    break

            except Exception as e:
                continue

        log_print(f"[SUCCESS] {len(results)} 件取得")
        return results

    except Exception as e:
        log_print(f"[ERROR] {type(e).__name__}: {str(e)[:100]}")
        return []


async def main():
    """メイン処理"""
    log_print("[START] PayPay Flea Market スクレイピング開始")
    log_print(f"[INFO] {len(CARD_KEYWORDS)} 個のキーワードを処理")

    data = {}
    success_count = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            for i, keyword in enumerate(CARD_KEYWORDS, 1):
                log_print(f"\n[{i}/{len(CARD_KEYWORDS)}] {keyword}")
                results = await scrape_keyword(page, keyword)

                if results:
                    data[keyword] = results
                    success_count += 1

        finally:
            await context.close()
            await browser.close()

    # 結果を保存
    log_print(f"\n[END] 合計 {success_count}/{len(CARD_KEYWORDS)} 件成功")

    if success_count > 0:
        with open("listings.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_print("[SAVE] listings.json を更新しました")
    else:
        log_print("[KEEP] スクレイピング失敗のため、既存の listings.json を保持")


if __name__ == "__main__":
    asyncio.run(main())
