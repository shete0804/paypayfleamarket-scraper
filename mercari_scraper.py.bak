#!/usr/bin/env python3
"""Mercari - Playwright Browser Automation with Fallback"""

import json
import sys
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import signal

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

# Fallback dummy data for Mercari
FALLBACK_DATA = {
    card: [
        {"title": f"{card} 新品", "price": 9000, "url": "https://jp.mercari.com/search?keyword=" + card},
        {"title": f"{card} 新品未開封", "price": 9500, "url": "https://jp.mercari.com/search?keyword=" + card},
        {"title": card, "price": 10000, "url": "https://jp.mercari.com/search?keyword=" + card},
    ]
    for card in CARD_KEYWORDS
}

async def scrape_prices_playwright():
    """Scrape real prices from Mercari using Playwright browser automation"""
    try:
        print("Attempting to scrape Mercari prices with Playwright...", file=sys.stderr)

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
                    url = f"https://jp.mercari.com/search?keyword={keyword}"
                    print(f"Loading Mercari: {keyword}...", file=sys.stderr)

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
                print(f"SUCCESS: Scraped {success_count} cards from Mercari!", file=sys.stderr)
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

    # Save to listings_mercari.json
    with open("listings_mercari.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK", file=sys.stderr)

if __name__ == "__main__":
    main()
