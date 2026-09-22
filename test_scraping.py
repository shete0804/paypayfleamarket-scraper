#!/usr/bin/env python3
"""Test scraping PayPay Flea Market"""

import requests
from bs4 import BeautifulSoup
import sys

url = 'https://www.paypayfleamarket.yahoo.co.jp/search?keyword=メガルカリオex'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

try:
    print("Attempting to scrape PayPay Flea Market...", file=sys.stderr)
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}", file=sys.stderr)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Try multiple selectors
        selectors = [
            ('class', lambda x: x and 'price' in x.lower()),
            ('data-price', True),
            ('class', lambda x: x and 'amount' in x.lower()),
        ]

        found = False
        for attr, value in selectors:
            if attr == 'class':
                elements = soup.find_all(class_=value)
            else:
                elements = soup.find_all(attrs={attr: value})

            if elements:
                print(f"Found {len(elements)} elements with {attr}", file=sys.stderr)
                for elem in elements[:3]:
                    print(f"  - {elem.text[:100]}", file=sys.stderr)
                found = True
                break

        if not found:
            print("No price elements found - content likely rendered by JavaScript", file=sys.stderr)
            # Print first 1000 chars to inspect
            print(response.text[:500], file=sys.stderr)
    else:
        print(f"Failed to fetch: {response.status_code}", file=sys.stderr)

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
