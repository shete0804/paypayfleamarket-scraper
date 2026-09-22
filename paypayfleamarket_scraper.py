#!/usr/bin/env python3
"""
PayPay フリマ × メルカリ 値段差比較システム
===========================================

Apify API を使用して PayPay Flea Market の実数値を取得し、
メルカリの価格との差分を Discord に通知する。

GitHub Actions から 6 時間ごとに実行される想定。

必要な環境変数:
    DISCORD_WEBHOOK_URL   Discord Incoming Webhook の URL
    APIFY_API_TOKEN       Apify API トークン（PayPay データ取得用）

必要なライブラリ:
    requests              HTTP リクエスト送信
    apify-client          Apify API クライアント
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone

import requests
from apify_client import ApifyClient

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "").strip()

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

    # Apify トークンがない場合は JSON フォールバック
    if not APIFY_API_TOKEN:
        print("警告: APIFY_API_TOKEN が未設定。JSON フォールバックモードで実行", file=sys.stderr)
        return _fetch_from_json()

    # Apify API で PayPay Flea Market からデータ取得
    client = ApifyClient(token=APIFY_API_TOKEN)

    for keyword in CARD_KEYWORDS:
        try:
            print(f"取得中: {keyword}", file=sys.stderr)

            # Apify Actor を実行（jungle_synthesizer のスクレーパーを使用）
            run = client.actor("jungle_synthesizer/paypay-flea-market-japan-listings-scraper").call(
                {"query": keyword, "maxItems": TOP_N}
            )

            # 結果データを Listing に変換
            items_data = run.get("items", []) or []
            listings = []

            for item in items_data[:TOP_N]:
                try:
                    # Apify からのレスポンス形式に対応
                    price_str = str(item.get("price", "0")).replace("¥", "").replace(",", "").strip()
                    price = int(float(price_str)) if price_str.isdigit() else 0

                    if price > 0 and is_single_card(item.get("title", "")):
                        listings.append(Listing(
                            card=keyword,
                            price=price,
                            url=item.get("url", "")
                        ))
                except (ValueError, KeyError, TypeError) as e:
                    print(f"  アイテムパース失敗: {item} - {e}", file=sys.stderr)
                    continue

            if listings:
                results[keyword] = listings
                print(f"{keyword}: {len(listings)}件取得", file=sys.stderr)
            else:
                errors[keyword] = "Apify: 該当商品なし"
                print(f"{keyword}: 該当商品なし", file=sys.stderr)

        except Exception as e:
            error_msg = f"Apify API エラー: {type(e).__name__}: {str(e)[:100]}"
            errors[keyword] = error_msg
            print(error_msg, file=sys.stderr)

    return results, errors


def _fetch_from_json() -> tuple[dict[str, list[Listing]], dict[str, str]]:
    """JSON フォールバック実装（Apify トークン未設定時）"""
    results: dict[str, list[Listing]] = {}
    errors: dict[str, str] = {}

    import os as _os
    _listings_file = "listings.json"

    try:
        if _os.path.exists(_listings_file):
            with open(_listings_file, "r", encoding="utf-8") as f:
                listings_data = json.load(f)

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
                    print(f"{keyword}: {len(results[keyword])}件取得（JSON）", file=sys.stderr)
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
