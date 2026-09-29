#!/usr/bin/env python3
"""Discord 通知処理."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests

import price_watch.event

if TYPE_CHECKING:
    import PIL.Image

    from price_watch.models import CheckedItem, TargetDiff


DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def _send_discord(embed: dict) -> bool:
    """Discord Webhook で通知を送信."""
    if not DISCORD_WEBHOOK_URL:
        logging.debug("DISCORD_WEBHOOK_URL not set, skipping Discord notification")
        return False

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.warning(f"Failed to send Discord notification: {e}")
        return False


def info(
    slack_config,
    item: CheckedItem,
    is_record: bool = False,
) -> str | None:
    """価格変更の情報を通知（Discord）."""
    discord_embed = {
        "title": f"{'🔥' if is_record else '💰'} {item.name}",
        "description": f"**¥{item.old_price or 0:,} → ¥{item.price or 0:,}** {item.price_unit}",
        "fields": [
            {"name": "ストア", "value": item.store or "不明", "inline": True},
            {"name": "在庫", "value": "在庫あり" if item.stock_as_int() != 0 else "品切れ", "inline": True},
        ],
        "color": 0xFF5733 if is_record else 0x3498DB,
    }
    if item.url:
        discord_embed["fields"].append({"name": "URL", "value": f"[詳細]({item.url})", "inline": False})
    if item.thumb_url:
        discord_embed["thumbnail"] = {"url": item.thumb_url}

    _send_discord(discord_embed)
    return None


def error(
    slack_config,
    item: CheckedItem,
    error_msg: str,
) -> str | None:
    """エラーを通知（Discord）."""
    discord_embed = {
        "title": f"⚠️ エラー: {item.name}",
        "description": error_msg,
        "fields": [
            {"name": "ストア", "value": item.store or "不明", "inline": True},
        ],
        "color": 0xFF0000,
    }
    if item.url:
        discord_embed["fields"].append({"name": "URL", "value": f"[リンク]({item.url})", "inline": False})

    _send_discord(discord_embed)
    return None


def error_with_page(
    slack_config,
    item: CheckedItem,
    exception: Exception,
    screenshot: PIL.Image.Image | None = None,
    page_source: str | None = None,
) -> str | None:
    """スクリーンショット付きエラー通知（Discord）."""
    discord_embed = {
        "title": f"❌ スクレイプエラー: {item.name}",
        "description": str(exception),
        "fields": [
            {"name": "ストア", "value": item.store or "不明", "inline": True},
        ],
        "color": 0xFF0000,
    }
    if item.url:
        discord_embed["fields"].append({"name": "URL", "value": f"[リンク]({item.url})", "inline": False})

    _send_discord(discord_embed)
    return None


def event(
    slack_config,
    event_result: price_watch.event.EventResult,
    item: CheckedItem,
    external_url: str | None = None,
) -> str | None:
    """イベント通知（Discord）."""
    icon_map = {
        price_watch.event.EventType.BACK_IN_STOCK: "📦",
        price_watch.event.EventType.CRAWL_FAILURE: "⚠️",
        price_watch.event.EventType.DATA_RETRIEVAL_FAILURE: "❌",
        price_watch.event.EventType.LOWEST_PRICE: "🔥",
        price_watch.event.EventType.PRICE_DROP: "📉",
    }
    icon = icon_map.get(event_result.event_type, "📌")

    message_text = _build_event_message(event_result, item)

    discord_embed = {
        "title": f"{icon} {price_watch.event.format_event_title(event_result.event_type.value)}: {item.name}",
        "description": message_text,
        "fields": [
            {"name": "ストア", "value": item.store or "不明", "inline": True},
            {"name": "現在価格", "value": f"¥{event_result.price:,}" if event_result.price else "不明", "inline": True},
        ],
        "color": 0xFF0000 if event_result.event_type == price_watch.event.EventType.DATA_RETRIEVAL_FAILURE else 0xFF5733,
    }
    if item.url:
        discord_embed["fields"].append({"name": "URL", "value": f"[詳細]({item.url})", "inline": False})
    if item.thumb_url:
        discord_embed["thumbnail"] = {"url": item.thumb_url}

    _send_discord(discord_embed)
    return None


def _build_event_message(
    event_result: price_watch.event.EventResult,
    item: CheckedItem,
) -> str:
    """イベント通知メッセージを構築."""
    parts: list[str] = []

    price_unit = item.price_unit

    match event_result.event_type:
        case price_watch.event.EventType.BACK_IN_STOCK:
            parts.append("**在庫が復活しました**")
            if event_result.price is not None:
                parts.append(f"価格: ¥{event_result.price:,}{price_unit}")

        case price_watch.event.EventType.CRAWL_FAILURE:
            parts.append("**24時間以上クロールに失敗しています**")
            parts.append("サイトの構造が変わった可能性があります")

        case price_watch.event.EventType.DATA_RETRIEVAL_FAILURE:
            parts.append("**6時間以上情報を取得できていません**")
            parts.append("価格・在庫情報の取得に失敗しています")

        case price_watch.event.EventType.LOWEST_PRICE:
            if event_result.old_price is not None and event_result.price is not None:
                drop = event_result.old_price - event_result.price
                old = f"¥{event_result.old_price:,}{price_unit}"
                new = f"¥{event_result.price:,}{price_unit}"
                parts.append("**過去最安値を更新！**")
                parts.append(f"{old} → **{new}** (-¥{drop:,}{price_unit})")
            else:
                parts.append("**過去最安値を更新しました**")

        case price_watch.event.EventType.PRICE_DROP:
            if (
                event_result.old_price is not None
                and event_result.price is not None
                and event_result.threshold_days is not None
            ):
                drop = event_result.old_price - event_result.price
                old = f"¥{event_result.old_price:,}{price_unit}"
                new = f"¥{event_result.price:,}{price_unit}"
                parts.append(f"**{event_result.threshold_days}日間の最安値から値下げ**")
                parts.append(f"{old} → **{new}** (-¥{drop:,}{price_unit})")
            else:
                parts.append("**価格が下がりました**")

    return "\n".join(parts)


def target_changed(
    slack_config,
    diff,
) -> str | None:
    """target.yaml の変更を通知（Discord）."""
    if not diff.has_changes():
        return None

    message_parts: list[str] = []

    if diff.added:
        message_parts.append(f"**➕ 追加 ({len(diff.added)}件)**")
        for item in diff.added:
            message_parts.append(f"  • {item.name} ({item.store})")
        message_parts.append("")

    if diff.removed:
        message_parts.append(f"**➖ 削除 ({len(diff.removed)}件)**")
        for item in diff.removed:
            message_parts.append(f"  • {item.name} ({item.store})")
        message_parts.append("")

    if diff.changed:
        message_parts.append(f"**✏️ 変更 ({len(diff.changed)}件)**")
        for item, changes in diff.changed:
            message_parts.append(f"  • {item.name} ({item.store})")
            for change in changes:
                message_parts.append(f'    - {change.field}: "{change.old_value}" → "{change.new_value}"')
        message_parts.append("")

    message_text = "\n".join(message_parts).strip()

    discord_embed = {
        "title": "📝 target.yaml が更新されました",
        "description": message_text,
        "color": 0x2ECC71,
    }

    _send_discord(discord_embed)
    return None


def auth_failure(
    slack_config,
    client_ip: str,
    failure_count: int,
) -> str | None:
    """認証失敗を通知（Discord）."""
    discord_embed = {
        "title": "🚨 認証失敗アラート",
        "description": f"**1時間に{failure_count}回の認証失敗を検出しました**\nIP: `{client_ip}`\nブルートフォース攻撃の可能性があります。",
        "color": 0xFF0000,
    }

    _send_discord(discord_embed)
    return None
