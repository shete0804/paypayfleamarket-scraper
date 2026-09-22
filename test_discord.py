#!/usr/bin/env python3
"""Test Discord webhook connectivity"""

import os
import requests
import json

webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

if not webhook_url:
    print("ERROR: DISCORD_WEBHOOK_URL environment variable not set")
    exit(1)

print(f"Testing Discord webhook: {webhook_url[:50]}...")

test_embed = {
    "title": "🧪 テスト: PayPay スクレイパー",
    "description": "Discord webhook connection test",
    "color": 3447003,
    "fields": [
        {
            "name": "Status",
            "value": "✓ Webhook は正常に動作しています",
            "inline": False
        }
    ]
}

payload = {"embeds": [test_embed]}

try:
    response = requests.post(webhook_url, json=payload, timeout=10)
    if response.status_code == 204:
        print("✓ SUCCESS: Discord webhook works!")
    else:
        print(f"✗ FAILED: Status {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"✗ ERROR: {e}")
