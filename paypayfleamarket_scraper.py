#!/usr/bin/env python3
"""
PayPay フリマ MEGA シリーズ カード価格モニター
============================================

JSON ベースの静的データベース（listings.json）から出品情報を取得し、
Discord に Embed 形式で通知する。

GitHub Actions から 6 時間ごとに実行される想定。

必要な環境変数:
    DISCORD_WEBHOOK_URL   Discord Incoming Webhook の URL

必要なライブラリ:
    requests              HTTP リクエスト送信
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone

import requests

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

CARD_KEYWORDS: list[str] = [
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
    "メガカイリューex SAR MEGAドリームex",
    "メガジガルデex MUR ムニキスゼロ",
    "ニャースex SAR ムニキスゼロ",
    "メイのはげまし SAR ムニキスゼロ",
    "メガゲッコウガex MUR ニンジャスピナー",
    "メガゲッコウガex SAR ニンジャスピナー",
    "メガダークライex MUR アビスアイ",
    "メガダークライex SAR アビスアイ",
]

TOP_N = 3

JST = timezone(timedelta(hours=9))

EXCLUDE_KEYWORDS: set[str] = {
    "セット",
    "2枚",
    "3枚",
    "4枚",
    "5枚",
    "10枚",
    "20枚",
    "5パック",
    "10パック",
    "Box",
    "ボックス",
    "まとめ売り",
    "福袋",
    "構築済みデッキ",
    "デッキ",
    "旧裏",
    "おまけ",
    "2P",
    "3P",
    "4P",
    "5P",
}


class Listing:
    def __init__(self, card: str, price: int, url: str):
        self.card = card
        self.price = price
        self.url = url


# ---------------------------------------------------------------------------
# 商品フィルタリング
# ---------------------------------------------------------------------------


def is_single_card(title: str) -> bool:
    title_lower = title.lower()
    return not any(keyword in title_lower for keyword in EXCLUDE_KEYWORDS)


# ---------------------------------------------------------------------------
# データ取得
# ---------------------------------------------------------------------------


def fetch_all() -> tuple[dict[str, list[Listing]], dict[str, str]]:
    results: dict[str, list[Listing]] = {}
    errors: dict[str, str] = {}

    # JSON ファイルから出品情報を読み込む
    import os as _os
    _listings_file = "listings.json"

    try:
        if _os.path.exists(_listings_file):
            with open(_listings_file, "r", encoding="utf-8") as f:
                listings_data = json.load(f)

            # JSON データを Listing オブジェクトに変換
            for keyword in CARD_KEYWORDS:
                if keyword in listings_data:
                    items = listings_data[keyword]
                    results[keyword] = [
                        Listing(
                            card=item.get("title", ""),
                            price=item.get("price", 0),
                            url=item.get("url", "")
                        )
                        for item in items
                    ]
                    print(f"{keyword}: {len(results[keyword])}件取得", file=sys.stderr)
                else:
                    print(f"{keyword}: JSON に未登録", file=sys.stderr)
        else:
            print(f"listings.json が見つかりません", file=sys.stderr)
            for keyword in CARD_KEYWORDS:
                errors[keyword] = "listings.json が見つかりません"
    except Exception as e:
        print(f"JSON 読み込みエラー: {e}", file=sys.stderr)
        for keyword in CARD_KEYWORDS:
            errors[keyword] = f"JSON 読み込みエラー: {str(e)}"

    return results, errors


# ---------------------------------------------------------------------------
# Discord 通知
# ---------------------------------------------------------------------------


def _now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def _fmt_price(price: int) -> str:
    return f"¥{price:,}"


def _send(payload: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL 未設定のため送信をスキップ", file=sys.stderr)
        return
    print(f"DEBUG: Sending payload to Discord webhook...", file=sys.stderr)
    print(f"DEBUG: Webhook URL: {DISCORD_WEBHOOK_URL[:80]}...", file=sys.stderr)
    try:
        resp = requests.post(
                        DISCORD_WEBHOOK_URL,
                        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                        headers={"Content-Type": "application/json; charset=utf-8"},
                        timeout=15
        )
        print(f"DEBUG: Discord webhook response: {resp.status_code}", file=sys.stderr)
        print(f"DEBUG: Response text: {resp.text[:200]}", file=sys.stderr)
        resp.raise_for_status()
        print(f"DEBUG: Discord webhook sent successfully", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: Discord webhook error: {type(e).__name__}: {str(e)}", file=sys.stderr)
        raise


def post_report(results: dict[str, list[Listing]], errors: dict[str, str]) -> None:
    fields = []
    for keyword in CARD_KEYWORDS:
        listings = results.get(keyword, [])
        if listings:
            value = "\n".join(f"[{_fmt_price(l.price)}]({l.url})" for l in listings)
        elif keyword in errors:
            value = f"⚠️ 取得失敗: {errors[keyword][:200]}"
        else:
            value = "販売中の出品なし"
        fields.append({"name": keyword, "value": value, "inline": False})

    embed = {
        "title": "PayPay フリマ MEGA シリーズ 最安値レポート",
        "description": f"販売中・最安 {TOP_N} 件 / {_now_jst()}",
        "color": 0x003DA5,
        "fields": fields[:25],
        "footer": {"text": "6 時間ごと自動実行"},
    }
    _send({"embeds": [embed]})


def post_failure(title: str, detail: str) -> None:
    embed = {
        "title": title,
        "description": f"```\n{detail[:3800]}\n```",
        "color": 0xFF0000,
        "footer": {"text": _now_jst()},
    }
    _send({"embeds": [embed]})


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def main() -> int:
    print(f"DEBUG: DISCORD_WEBHOOK_URL={DISCORD_WEBHOOK_URL[:50]}..." if DISCORD_WEBHOOK_URL else "DEBUG: DISCORD_WEBHOOK_URL not set", file=sys.stderr)

    if not DISCORD_WEBHOOK_URL:
        print("環境変数 DISCORD_WEBHOOK_URL が必要です", file=sys.stderr)
        return 1

    try:
        print("DEBUG: Starting fetch_all()", file=sys.stderr)
        results, errors = fetch_all()
        print(f"DEBUG: fetch_all() completed. results: {len(results)} items, errors: {len(errors)} items", file=sys.stderr)
        if errors:
            print(f"DEBUG: Errors encountered: {errors}", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: Exception in fetch_all(): {type(e).__name__}: {e}", file=sys.stderr)
        print(f"DEBUG: Traceback: {traceback.format_exc()}", file=sys.stderr)
        post_failure("スクレイピング失敗", traceback.format_exc())
        return 1

    if errors and len(errors) == len(CARD_KEYWORDS):
        detail = "\n".join(f"- {k}: {v}" for k, v in errors.items())
        post_failure("スクレイピング失敗", detail)
        return 1

    post_report(results, errors)

    if errors:
        print(f"{len(errors)} 件のカードで取得失敗", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
