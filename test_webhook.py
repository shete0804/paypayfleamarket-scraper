#!/usr/bin/env python3
import os
import requests
import json

webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

if not webhook_url:
    print("❌ DISCORD_WEBHOOK_URL not set")
    exit(1)

print(f"🔍 Testing webhook: {webhook_url[:80]}...")

payload = {
    "embeds": [{
        "title": "PayPay フリマ テスト",
        "description": "Webhook テスト実行",
        "color": 0x00FF00
    }]
}

try:
    resp = requests.post(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=15
    )
    print(f"✅ Response status: {resp.status_code}")
    if resp.status_code == 204:
        print("✅ Webhook OK (HTTP 204)")
    else:
        print(f"⚠️ Response body: {resp.text[:200]}")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
