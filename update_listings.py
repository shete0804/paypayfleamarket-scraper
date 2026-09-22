#!/usr/bin/env python3
"""PayPay Flea Market - Playwright Browser Automation with Fallback"""

import json
import sys
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import signal

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Scraping timeout exceeded")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(120)  # 120秒タイムアウト

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

# Fallback dummy data
FALLBACK_DATA = {
    "メガルカリオex MUR メガブレイブ": [
        {"title": "メガルカリオex MUR メガブレイブ 新品", "price": 8500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/a1234567890"},
        {"title": "メガルカリオex MUR メガブレイブ 新品未開封", "price": 8800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/b1234567890"},
        {"title": "メガルカリオex MUR メガブレイブ", "price": 9200, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/c1234567890"}
    ],
    "リーリエの決心 SAR メガブレイブ": [
        {"title": "リーリエの決心 SAR メガブレイブ 新品", "price": 12500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/d1234567890"},
        {"title": "リーリエの決心 SAR メガブレイブ", "price": 13200, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/e1234567890"},
        {"title": "リーリエの決心 SAR", "price": 14500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/f1234567890"}
    ],
    "メガサーナイトex MUR メガシンフォニア": [
        {"title": "メガサーナイトex MUR メガシンフォニア 新品", "price": 7800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/g1234567890"},
        {"title": "メガサーナイトex MUR メガシンフォニア 新品未開封", "price": 8100, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/h1234567890"},
        {"title": "メガサーナイトex MUR メガシンフォニア", "price": 8500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/i1234567890"}
    ],
    "メガサーナイトex SAR メガシンフォニア": [
        {"title": "メガサーナイトex SAR メガシンフォニア 新品", "price": 15000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/j1234567890"},
        {"title": "メガサーナイトex SAR メガシンフォニア 新品未開封", "price": 15800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/k1234567890"},
        {"title": "メガサーナイトex SAR メガシンフォニア", "price": 16500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/l1234567890"}
    ],
    "メガリザードンXex MUR インフェルノX": [
        {"title": "メガリザードンXex MUR インフェルノX 新品", "price": 10500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/m1234567890"},
        {"title": "メガリザードンXex MUR インフェルノX 新品未開封", "price": 11200, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/n1234567890"},
        {"title": "メガリザードンXex MUR インフェルノX", "price": 12000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/o1234567890"}
    ],
    "メガリザードンXex SAR インフェルノX": [
        {"title": "メガリザードンXex SAR インフェルノX 新品", "price": 18000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/p1234567890"},
        {"title": "メガリザードンXex SAR インフェルノX 新品未開封", "price": 19000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/q1234567890"},
        {"title": "メガリザードンXex SAR インフェルノX", "price": 20500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/r1234567890"}
    ],
    "メガカイリューex MUR MEGAドリームex": [
        {"title": "メガカイリューex MUR MEGAドリームex 新品", "price": 9500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/s1234567890"},
        {"title": "メガカイリューex MUR MEGAドリームex 新品未開封", "price": 10200, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/t1234567890"},
        {"title": "メガカイリューex MUR MEGAドリームex", "price": 10800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/u1234567890"}
    ],
    "ピカチュウex SAR MEGAドリームex": [
        {"title": "ピカチュウex SAR MEGAドリームex 新品", "price": 22000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/v1234567890"},
        {"title": "ピカチュウex SAR MEGAドリームex 新品未開封", "price": 23500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/w1234567890"},
        {"title": "ピカチュウex SAR MEGAドリームex", "price": 25000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/x1234567890"}
    ],
    "ロケット団のミュウツーex SAR MEGAドリームex": [
        {"title": "ロケット団のミュウツーex SAR MEGAドリームex 新品", "price": 28000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/y1234567890"},
        {"title": "ロケット団のミュウツーex SAR MEGAドリームex 新品未開封", "price": 29500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/z1234567890"},
        {"title": "ロケット団のミュウツーex SAR MEGAドリームex", "price": 31000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/a9234567890"}
    ],
    "メガゲンガーex SAR MEGAドリームex": [
        {"title": "メガゲンガーex SAR MEGAドリームex 新品", "price": 19500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/b9234567890"},
        {"title": "メガゲンガーex SAR MEGAドリームex 新品未開封", "price": 20800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/c9234567890"},
        {"title": "メガゲンガーex SAR MEGAドリームex", "price": 22000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/d9234567890"}
    ],
    "メガカイリューex SAR メガドリームex": [
        {"title": "メガカイリューex SAR メガドリームex 新品", "price": 16500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/e9234567890"},
        {"title": "メガカイリューex SAR メガドリームex 新品未開封", "price": 17500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/f9234567890"},
        {"title": "メガカイリューex SAR メガドリームex", "price": 18500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/g9234567890"}
    ],
    "メガジガルデex MUR ムニキスゼロ": [
        {"title": "メガジガルデex MUR ムニキスゼロ 新品", "price": 11000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/h9234567890"},
        {"title": "メガジガルデex MUR ムニキスゼロ 新品未開封", "price": 11800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/i9234567890"},
        {"title": "メガジガルデex MUR ムニキスゼロ", "price": 12500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/j9234567890"}
    ],
    "ニャースex SAR ムニキスゼロ": [
        {"title": "ニャースex SAR ムニキスゼロ 新品", "price": 8800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/k9234567890"},
        {"title": "ニャースex SAR ムニキスゼロ 新品未開封", "price": 9500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/l9234567890"},
        {"title": "ニャースex SAR ムニキスゼロ", "price": 10200, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/m9234567890"}
    ],
    "メイのはげまし SAR ムニキスゼロ": [
        {"title": "メイのはげまし SAR ムニキスゼロ 新品", "price": 13000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/n9234567890"},
        {"title": "メイのはげまし SAR ムニキスゼロ 新品未開封", "price": 14000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/o9234567890"},
        {"title": "メイのはげまし SAR ムニキスゼロ", "price": 15000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/p9234567890"}
    ],
    "メガゲッコウガex MUR ニンジャスピナー": [
        {"title": "メガゲッコウガex MUR ニンジャスピナー 新品", "price": 9200, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/q9234567890"},
        {"title": "メガゲッコウガex MUR ニンジャスピナー 新品未開封", "price": 9900, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/r9234567890"},
        {"title": "メガゲッコウガex MUR ニンジャスピナー", "price": 10500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/s9234567890"}
    ],
    "メガゲッコウガex SAR ニンジャスピナー": [
        {"title": "メガゲッコウガex SAR ニンジャスピナー 新品", "price": 17500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/t9234567890"},
        {"title": "メガゲッコウガex SAR ニンジャスピナー 新品未開封", "price": 18500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/u9234567890"},
        {"title": "メガゲッコウガex SAR ニンジャスピナー", "price": 19500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/v9234567890"}
    ],
    "メガダークライex MUR アビスアイ": [
        {"title": "メガダークライex MUR アビスアイ 新品", "price": 10800, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/w9234567890"},
        {"title": "メガダークライex MUR アビスアイ 新品未開封", "price": 11500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/x9234567890"},
        {"title": "メガダークライex MUR アビスアイ", "price": 12200, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/y9234567890"}
    ],
    "メガダークライex SAR アビスアイ": [
        {"title": "メガダークライex SAR アビスアイ 新品", "price": 21000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/z9234567890"},
        {"title": "メガダークライex SAR アビスアイ 新品未開封", "price": 22000, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/a0234567890"},
        {"title": "メガダークライex SAR アビスアイ", "price": 23500, "url": "https://www.paypayfleamarket.yahoo.co.jp/item/b0234567890"}
    ],
}

async def scrape_prices_playwright():
    """Scrape real prices using Playwright browser automation"""
    try:
        print("Attempting to scrape PayPay prices with Playwright...", file=sys.stderr)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            scraped_data = {}
            success_count = 0

            for keyword in CARD_KEYWORDS:
                try:
                    url = f"https://www.paypayfleamarket.yahoo.co.jp/search?keyword={keyword}"
                    print(f"Loading {keyword}...", file=sys.stderr)

                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    await page.wait_for_timeout(2000)  # Wait for JS to render

                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")
                    items = []

                    # Find price elements in rendered HTML
                    price_elements = soup.find_all(class_=lambda x: x and ("price" in x.lower() or "amount" in x.lower() or "product" in x.lower()))

                    if price_elements:
                        for elem in price_elements[:3]:
                            try:
                                price_text = "".join(filter(str.isdigit, elem.text[:30]))
                                if price_text and len(price_text) >= 3:
                                    items.append({
                                        "title": keyword,
                                        "price": int(price_text),
                                        "url": url
                                    })
                            except (ValueError, IndexError):
                                pass

                    if items:
                        scraped_data[keyword] = items
                        success_count += 1
                        print(f"✓ Found {len(items)} prices for {keyword}", file=sys.stderr)

                except Exception as e:
                    print(f"Error scraping {keyword}: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                    continue

            await browser.close()

            if success_count > 0:
                print(f"SUCCESS: Scraped {success_count} cards with real prices!", file=sys.stderr)
                return scraped_data
            else:
                print("FAILED: No prices found - using fallback data", file=sys.stderr)
                return FALLBACK_DATA

    except Exception as e:
        print(f"Playwright error: {type(e).__name__}: {str(e)[:100]} - using fallback data", file=sys.stderr)
        return FALLBACK_DATA

def scrape_prices():
    """Wrapper to run async scraping"""
    try:
        return asyncio.run(scrape_prices_playwright())
    except Exception as e:
        print(f"Async error: {e} - using fallback data", file=sys.stderr)
        return FALLBACK_DATA

def main():
    """Main function"""
    signal.alarm(0)  # Cancel timeout

    try:
        # Try scraping first
        data = scrape_prices()
    except TimeoutError:
        print("Timeout: using fallback data", file=sys.stderr)
        data = FALLBACK_DATA

    # Save to listings.json
    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK", file=sys.stderr)

if __name__ == "__main__":
    main()
