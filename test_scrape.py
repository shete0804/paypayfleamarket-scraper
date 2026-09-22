#!/usr/bin/env python3
"""デバッグ: PayPay から実際に何が取得できるか確認"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

keyword = "メガルカリオex MUR メガブレイブ"
url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

print(f"URL: {url}")
print(f"Headers: {headers}\n")

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
    print(f"Content length: {len(response.content)} bytes\n")

    soup = BeautifulSoup(response.content, "html.parser")

    # <a href="/item/..."> を探す
    items = soup.find_all("a", href=re.compile(r"/item/"))
    print(f"Found {len(items)} items with href='/item/'\n")

    # 最初の 5 つのアイテムを表示
    for i, item in enumerate(items[:5]):
        text = item.get_text(strip=True)
        href = item.get("href", "")
        print(f"Item {i+1}:")
        print(f"  Text: {text[:80]}")
        print(f"  Href: {href}")

        # 価格マッチ試行
        price_match = re.search(r"¥([\d,]+)", text)
        if price_match:
            print(f"  Price: ¥{price_match.group(1)}")
        else:
            print(f"  Price: NOT FOUND")
        print()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
