#!/usr/bin/env python3
"""Debug: Save raw HTML response from PayPay"""

import requests
from urllib.parse import quote

keyword = "メガルカリオex MUR メガブレイブ"
url = f"https://paypayfleamarket.yahoo.co.jp/search/{quote(keyword)}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

print(f"Fetching: {url}")

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.content)} bytes")

    # Save raw HTML
    with open("debug_response.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved to debug_response.html")

    # Look for JSON-LD
    if '<script type="application/ld+json">' in response.text:
        print("✓ Found: <script type=\"application/ld+json\">")
    elif "<script type='application/ld+json'>" in response.text:
        print("✓ Found: <script type='application/ld+json'>")
    else:
        print("✗ JSON-LD script tag not found")
        print(f"First 1000 chars:\n{response.text[:1000]}")

    # Count script tags
    import re
    scripts = re.findall(r'<script[^>]*>', response.text)
    print(f"Found {len(scripts)} <script> tags")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
