#!/usr/bin/env python3
"""
PayPay フリマ スクレイパー（JSON ベース）
==========================================

listings.json から PayPay Flea Market の出品情報を取得し、
Discord に通知する。

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

LISTINGS_FILE = "listings.json"

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


# ---------------------------------------------------------------------------
# データ取得（JSON ベース）
# ---------------------------------------------------------------------------


def load_listings() -> tuple[dict[str, list[dict]], str | None]:
    """listings.json から出品情報を読み込む。失敗時はエラーメッセージを返す"""
    import os.path

    try:
        # Working directory を表示
        cwd = os.getcwd()
        print(f"CWD: {cwd}", file=sys.stderr)

        # 複数のパスを試す
        possible_paths = [
            LISTINGS_FILE,
            f"./{LISTINGS_FILE}",
            f"/github/workspace/{LISTINGS_FILE}",
            os.path.join(cwd, LISTINGS_FILE),
        ]

        for path in possible_paths:
            try:
                abs_path = os.path.abspath(path)
                print(f"Try: {abs_path}", file=sys.stderr)
                with open(abs_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"✓ Loaded: {abs_path}", file=sys.stderr)
                    return data, None
            except FileNotFoundError:
                print(f"  NotFound", file=sys.stderr)
                continue
            except json.JSONDecodeError as e:
                return {}, f"JSON error in {abs_path}: {e}"

        # すべてのパスが失敗
        return {}, f"NOT FOUND: {LISTINGS_FILE}"

    except Exception as e:
        return {}, f"Error: {e}"


def fetch_all() -> tuple[dict[str, list[dict]], dict[str, str], str | None]:
    """listings.json から全カードの出品情報を取得"""
    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    listings, load_error = load_listings()

    if load_error:
        return results, errors, load_error

    for keyword in CARD_KEYWORDS:
        if keyword in listings:
            results[keyword] = listings[keyword][:TOP_N]
            print(f"取得中: {keyword} - {len(results[keyword])}件", file=sys.stderr)
        else:
            error_msg = "listings.json に登録なし"
            errors[keyword] = error_msg
            print(f"取得中: {keyword} - {error_msg}", file=sys.stderr)

    return results, errors, None


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
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    resp.raise_for_status()


def post_report(results: dict[str, list[dict]], errors: dict[str, str]) -> None:
    fields = []
    for keyword in CARD_KEYWORDS:
        listings = results.get(keyword, [])
        if listings:
            value = "\n".join(f"[{_fmt_price(l['price'])}]({l['url']})" for l in listings)
        elif keyword in errors:
            value = f"⚠️ {errors[keyword]}"
        else:
            value = "登録なし"
        fields.append({"name": keyword, "value": value, "inline": False})

    embed = {
        "title": "PayPay フリマ MEGA シリーズ 価格情報",
        "description": f"最安 {TOP_N} 件 / {_now_jst()}",
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
    try:
        results, errors, load_error = fetch_all()
    except Exception:
        detail = traceback.format_exc()
        print(f"スクレイピング失敗: {detail}", file=sys.stderr)
        print(detail)  # Also to stdout
        if DISCORD_WEBHOOK_URL:
            post_failure("スクレイピング失敗", detail)
        return 1

    # ファイル読み込みエラー
    if load_error:
        print(f"致命的エラー: {load_error}", file=sys.stderr)
        print(f"ERROR: {load_error}")  # Also to stdout
        if DISCORD_WEBHOOK_URL:
            post_failure("listings.json 読み込みエラー", load_error)
        return 1

    # すべてのカードで取得失敗（実データがない）
    if errors and len(errors) == len(CARD_KEYWORDS):
        detail = "\n".join(f"- {k}: {v}" for k, v in errors.items())
        print(f"すべてのカードで取得失敗: {detail}", file=sys.stderr)
        if DISCORD_WEBHOOK_URL:
            post_failure("スクレイピング失敗", detail)
        return 1

    # 成功：データを報告（Discord または コンソール）
    if DISCORD_WEBHOOK_URL:
        post_report(results, errors)
    else:
        # Webhook なしの場合は、結果をコンソール出力
        print("=== PayPay フリマ価格情報（Discord Webhook なし） ===", file=sys.stderr)
        for keyword in CARD_KEYWORDS:
            listings = results.get(keyword, [])
            if listings:
                prices = ", ".join(f"¥{l['price']:,}" for l in listings)
                print(f"{keyword}: {prices}", file=sys.stderr)
            else:
                print(f"{keyword}: 登録なし", file=sys.stderr)

    if errors:
        print(f"{len(errors)} 件のカードで取得失敗", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
