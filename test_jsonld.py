#!/usr/bin/env python3
"""Test JSON-LD extraction from PayPay Flea Market"""

import requests
import re
import json
from urllib.parse import quote
from bs4 import BeautifulSoup

keyword = "メガルカリオex MUR メガブレイブ"
url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.content)}")

    html_text = response.content.decode('utf-8', errors='ignore')

    # Find JSON-LD schema
    json_ld_match = re.search(r'<script type="application/ld\+json">([^<]+)</script>', html_text)
    if json_ld_match:
        print("\n✓ JSON-LD schema found")
        json_str = json_ld_match.group(1)
        print(f"JSON-LD size: {len(json_str)} bytes")

        schemas = json.loads(json_str)
        if not isinstance(schemas, list):
            schemas = [schemas]

        print(f"Schemas found: {len(schemas)}")

        # Extract URLs from ItemList
        item_urls = []
        for schema in schemas:
            if schema.get("@type") == "ItemList" and "itemListElement" in schema:
                print(f"  Found ItemList with {len(schema['itemListElement'])} items")
                for item in schema["itemListElement"]:
                    if "url" in item:
                        item_urls.append(item["url"])

        print(f"\nExtracted {len(item_urls)} URLs from JSON-LD:")
        for i, url in enumerate(item_urls[:3], 1):
            print(f"  {i}. {url}")

        # Test fetching the first item
        if item_urls:
            print(f"\n--- Testing first item page ---")
            first_url = item_urls[0]
            try:
                item_response = requests.get(first_url, headers=headers, timeout=10)
                print(f"Status: {item_response.status_code}")

                item_soup = BeautifulSoup(item_response.content, "html.parser")

                # Get title
                title_tag = item_soup.find("h1")
                title = title_tag.get_text(strip=True) if title_tag else "Unknown"
                print(f"Title: {title[:60]}")

                # Get price
                price_match = re.search(r"¥([\d,]+)", item_soup.get_text())
                if price_match:
                    price = int(price_match.group(1).replace(",", ""))
                    print(f"Price: ¥{price}")
                else:
                    print("Price: NOT FOUND")

            except Exception as e:
                print(f"Error fetching item: {e}")
    else:
        print("\n✗ JSON-LD schema NOT found")
        print(f"HTML preview: {html_text[:500]}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
