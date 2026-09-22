#!/usr/bin/env python3
import json
from datetime import datetime

# テスト用：簡単な JSON 出力
data = {
    "テスト": [
        {"title": "テスト 1", "price": 1000, "url": "https://example.com/1"},
        {"title": "テスト 2", "price": 2000, "url": "https://example.com/2"},
        {"title": "テスト 3", "price": 3000, "url": "https://example.com/3"},
    ]
}

with open("listings.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Test completed at {datetime.now()}")
print(f"Wrote {len(data)} entries")
