#!/usr/bin/env python3
"""PayPay Flea Market scraper (Playwright - JavaScript対応)"""

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


async def scrape_keyword(browser, keyword: str) -> list:
    """キーワード検索のスクレイピング"""
    try:
        page = await browser.new_page()
        page.set_default_timeout(30000)

        search_url = f"https://www.paypayfleamarket.yahoo.co.jp/search?query={quote(keyword)}"
        log_print(f"[LOAD] {search_url}")
        await page.goto(search_url, wait_until="networkidle")
        log_print(f"[WAIT] JavaScript レンダリング待機中...")
        await page.wait_for_timeout(3000)

        # __NEXT_DATA__ を取得
        script_content = await page.evaluate(
            """() => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? el.textContent : null;
            }"""
        )

        if not script_content:
            log_print(f"[FAIL] __NEXT_DATA__ が見つかりません")
            await page.close()
            return []

        log_print(f"[PARSE] JSON データを解析中...")
        data = json.loads(script_content)

        # 検索結果を抽出
        results = []
        try:
            # PayPay Flea Market の JSON 構造から出品情報を抽出
            items = data.get("props", {}).get("pageProps", {}).get("results", [])

            for item in items:
                title = item.get("title", "")
                price = item.get("price", None)
                url = item.get("url", "") or f"https://www.paypayfleamarket.yahoo.co.jp/item/{item.get('id', '')}"

                # フィルタリング
                if not title or price is None:
                    continue
                if any(kw in title for kw in EXCLUDE_KEYWORDS):
                    continue

                results.append({
                    "title": title[:50],
                    "price": int(price),
                    "url": url if url.startswith("http") else f"https://www.paypayfleamarket.yahoo.co.jp{url}",
                })

                if len(results) >= TOP_N:
                    break

        except (KeyError, TypeError) as e:
            log_print(f"[PARSE_ERROR] {type(e).__name__}: {str(e)[:100]}")

        log_print(f"[SUCCESS] {len(results)} 件取得")
        await page.close()
        return results

    except Exception as e:
        log_print(f"[ERROR] {type(e).__name__}: {str(e)[:100]}")
        try:
            await page.close()
        except:
            pass
        return []


async def main():
    """メイン処理"""
    log_print("[START] PayPay Flea Market スクレイピング開始")
    log_print(f"[INFO] {len(CARD_KEYWORDS)} 個のキーワードを処理")

    data = {}
    success_count = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",  # GitHub Actions 対応
        ])

        for i, keyword in enumerate(CARD_KEYWORDS, 1):
            log_print(f"\n[{i}/{len(CARD_KEYWORDS)}] {keyword}")
            results = await scrape_keyword(browser, keyword)

            if results:
                data[keyword] = results
                success_count += 1

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
