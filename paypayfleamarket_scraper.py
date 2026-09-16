#!/usr/bin/env python3
"""
PayPay 繝輔Μ繝・MEGA 繧ｷ繝ｪ繝ｼ繧ｺ 繧ｫ繝ｼ繝我ｾ｡譬ｼ繝｢繝九ち繝ｼ
============================================

蟇ｾ雎｡繧ｫ繝ｼ繝峨＃縺ｨ縺ｫ PayPay 繝輔Μ繝樊､懃ｴ｢繧貞ｮ溯｡後＠縲√瑚ｲｩ螢ｲ荳ｭ縲阪°縺､縲御ｾ｡譬ｼ縺ｮ螳峨＞鬆・阪〒
荳贋ｽ・3 莉ｶ・医き繝ｼ繝牙錐繝ｻ萓｡譬ｼ繝ｻURL・峨ｒ蜿門ｾ励＠縺ｦ Discord 縺ｫ Embed 蠖｢蠑上〒騾夂衍縺吶ｋ縲・
GitHub Actions 縺九ｉ 6 譎る俣縺斐→縺ｫ螳溯｡後＆繧後ｋ諠ｳ螳壹・
蠢・ｦ√↑迺ｰ蠅・､画焚:
    DISCORD_WEBHOOK_URL   Discord Incoming Webhook 縺ｮ URL

蠢・ｦ√↑繝ｩ繧､繝悶Λ繝ｪ:
    selenium              繝悶Λ繧ｦ繧ｶ閾ｪ蜍募喧
    requests              HTTP 繝ｪ繧ｯ繧ｨ繧ｹ繝磯∽ｿ｡
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ---------------------------------------------------------------------------
# 險ｭ螳・# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

CARD_KEYWORDS: list[str] = [
    "繝｡繧ｬ繝ｫ繧ｫ繝ｪ繧ｪex MUR 繝｡繧ｬ繝悶Ξ繧､繝・,
    "繝ｪ繝ｼ繝ｪ繧ｨ縺ｮ豎ｺ蠢・SAR 繝｡繧ｬ繝悶Ξ繧､繝・,
    "繝｡繧ｬ繧ｵ繝ｼ繝翫う繝・x MUR 繝｡繧ｬ繧ｷ繝ｳ繝輔か繝九い",
    "繝｡繧ｬ繧ｵ繝ｼ繝翫う繝・x SAR 繝｡繧ｬ繧ｷ繝ｳ繝輔か繝九い",
    "繝｡繧ｬ繝ｪ繧ｶ繝ｼ繝峨ΦXex MUR 繧､繝ｳ繝輔ぉ繝ｫ繝珊",
    "繝｡繧ｬ繝ｪ繧ｶ繝ｼ繝峨ΦXex SAR 繧､繝ｳ繝輔ぉ繝ｫ繝珊",
    "繝｡繧ｬ繧ｫ繧､繝ｪ繝･繝ｼex MUR MEGA繝峨Μ繝ｼ繝ex",
    "繝斐き繝√Η繧ｦex SAR MEGA繝峨Μ繝ｼ繝ex",
    "繝ｭ繧ｱ繝・ヨ蝗｣縺ｮ繝溘Η繧ｦ繝・・ex SAR MEGA繝峨Μ繝ｼ繝ex",
    "繝｡繧ｬ繧ｲ繝ｳ繧ｬ繝ｼex SAR MEGA繝峨Μ繝ｼ繝ex",
    "繝｡繧ｬ繧ｫ繧､繝ｪ繝･繝ｼex SAR MEGA繝峨Μ繝ｼ繝ex",
    "繝｡繧ｬ繧ｸ繧ｬ繝ｫ繝㌃x MUR 繝繝九く繧ｹ繧ｼ繝ｭ",
    "繝九Ε繝ｼ繧ｹex SAR 繝繝九く繧ｹ繧ｼ繝ｭ",
    "繝｡繧､縺ｮ縺ｯ縺偵∪縺・SAR 繝繝九く繧ｹ繧ｼ繝ｭ",
    "繝｡繧ｬ繧ｲ繝・さ繧ｦ繧ｬex MUR 繝九Φ繧ｸ繝｣繧ｹ繝斐リ繝ｼ",
    "繝｡繧ｬ繧ｲ繝・さ繧ｦ繧ｬex SAR 繝九Φ繧ｸ繝｣繧ｹ繝斐リ繝ｼ",
    "繝｡繧ｬ繝繝ｼ繧ｯ繝ｩ繧､ex MUR 繧｢繝薙せ繧｢繧､",
    "繝｡繧ｬ繝繝ｼ繧ｯ繝ｩ繧､ex SAR 繧｢繝薙せ繧｢繧､",
]

TOP_N = 3

JST = timezone(timedelta(hours=9))

EXCLUDE_KEYWORDS: set[str] = {
    "繧ｻ繝・ヨ",
    "2譫・,
    "3譫・,
    "4譫・,
    "5譫・,
    "10譫・,
    "20譫・,
    "5繝代ャ繧ｯ",
    "10繝代ャ繧ｯ",
    "Box",
    "繝懊ャ繧ｯ繧ｹ",
    "縺ｾ縺ｨ繧∝｣ｲ繧・,
    "遖剰｢・,
    "讒狗ｯ画ｸ医∩繝・ャ繧ｭ",
    "繝・ャ繧ｭ",
    "譌ｧ陬・,
    "縺翫∪縺・,
    "2P",
    "3P",
    "4P",
    "5P",
}


@dataclass
class Listing:
    card: str
    price: int
    url: str


# ---------------------------------------------------------------------------
# 蝠・刀繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ
# ---------------------------------------------------------------------------


def is_single_card(title: str) -> bool:
    title_lower = title.lower()
    return not any(keyword in title_lower for keyword in EXCLUDE_KEYWORDS)


# ---------------------------------------------------------------------------
# PayPay 繝輔Μ繝樊､懃ｴ｢
# ---------------------------------------------------------------------------


def search_card(keyword: str) -> list[Listing]:
    listings: list[Listing] = []

    try:
        print(f"讀懃ｴ｢荳ｭ: {keyword}", file=sys.stderr)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/snap/bin/chromium"

        driver = webdriver.Chrome(options=chrome_options)

        try:
            url = f"https://www.paypayfleamarket.yahoo.co.jp/search?keyword={urlencode({'q': keyword})}&sort=score"
            driver.get(url)

            wait = WebDriverWait(driver, 10)
            wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".ProductCard__title")
                )
            )

            items = driver.find_elements(By.CSS_SELECTOR, ".ProductCard")

            for item in items:
                if len(listings) >= TOP_N:
                    break

                try:
                    title_elem = item.find_element(By.CSS_SELECTOR, ".ProductCard__title")
                    title = title_elem.text

                    if not is_single_card(title):
                        print(f"髯､螟・ {title}", file=sys.stderr)
                        continue

                    price_elem = item.find_element(
                        By.CSS_SELECTOR, ".ProductCard__priceWrapper"
                    )
                    price_text = price_elem.text.replace("ﾂ･", "").replace(",", "")

                    try:
                        price = int(price_text)
                    except ValueError:
                        print(f"辟｡蜉ｹ縺ｪ萓｡譬ｼ: {title} ({price_text})", file=sys.stderr)
                        continue

                    link_elem = item.find_element(By.CSS_SELECTOR, "a")
                    url = link_elem.get_attribute("href")

                    if not url.startswith("http"):
                        url = "https://www.paypayfleamarket.yahoo.co.jp" + url

                    listings.append(Listing(card=keyword, price=price, url=url))
                    print(
                        f"蜿門ｾ・ {title} - ﾂ･{price:,}",
                        file=sys.stderr,
                    )

                except Exception as e:
                    print(
                        f"繧｢繧､繝・Β蜃ｦ逅・お繝ｩ繝ｼ ({keyword}): {type(e).__name__}: {e}",
                        file=sys.stderr,
                    )
                    continue

            print(f"螳御ｺ・ {keyword} ({len(listings)} 莉ｶ)", file=sys.stderr)

        finally:
            driver.quit()

    except Exception as e:
        print(
            f"讀懃ｴ｢繧ｨ繝ｩ繝ｼ ({keyword}): {type(e).__name__}: {e}",
            file=sys.stderr,
        )

    return listings


def fetch_all() -> tuple[dict[str, list[Listing]], dict[str, str]]:
    results: dict[str, list[Listing]] = {}
    errors: dict[str, str] = {}

    for keyword in CARD_KEYWORDS:
        try:
            result = search_card(keyword)
            results[keyword] = result
        except Exception as e:
            errors[keyword] = str(e)

    return results, errors


# ---------------------------------------------------------------------------
# Discord 騾夂衍
# ---------------------------------------------------------------------------


def _now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")


def _fmt_price(price: int) -> str:
    return f"ﾂ･{price:,}"


def _send(payload: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL 譛ｪ險ｭ螳壹・縺溘ａ騾∽ｿ｡繧偵せ繧ｭ繝・・", file=sys.stderr)
        return
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    resp.raise_for_status()


def post_report(results: dict[str, list[Listing]], errors: dict[str, str]) -> None:
    fields = []
    for keyword in CARD_KEYWORDS:
        listings = results.get(keyword, [])
        if listings:
            value = "\n".join(f"[{_fmt_price(l.price)}]({l.url})" for l in listings)
        elif keyword in errors:
            value = f"笞・・蜿門ｾ怜､ｱ謨・ {errors[keyword][:200]}"
        else:
            value = "雋ｩ螢ｲ荳ｭ縺ｮ蜃ｺ蜩√↑縺・
        fields.append({"name": keyword, "value": value, "inline": False})

    embed = {
        "title": "PayPay 繝輔Μ繝・MEGA 繧ｷ繝ｪ繝ｼ繧ｺ 譛螳牙､繝ｬ繝昴・繝・,
        "description": f"雋ｩ螢ｲ荳ｭ繝ｻ譛螳・{TOP_N} 莉ｶ / {_now_jst()}",
        "color": 0x003DA5,
        "fields": fields[:25],
        "footer": {"text": "6 譎る俣縺斐→閾ｪ蜍募ｮ溯｡・},
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
# 繧ｨ繝ｳ繝医Μ繝昴う繝ｳ繝・# ---------------------------------------------------------------------------


def main() -> int:
    if not DISCORD_WEBHOOK_URL:
        print("迺ｰ蠅・､画焚 DISCORD_WEBHOOK_URL 縺悟ｿ・ｦ√〒縺・, file=sys.stderr)
        return 1

    try:
        results, errors = fetch_all()
    except Exception:
        post_failure("繧ｹ繧ｯ繝ｬ繧､繝斐Φ繧ｰ螟ｱ謨・, traceback.format_exc())
        return 1

    if errors and len(errors) == len(CARD_KEYWORDS):
        detail = "\n".join(f"- {k}: {v}" for k, v in errors.items())
        post_failure("繧ｹ繧ｯ繝ｬ繧､繝斐Φ繧ｰ螟ｱ謨・, detail)
        return 1

    post_report(results, errors)

    if errors:
        print(f"{len(errors)} 莉ｶ縺ｮ繧ｫ繝ｼ繝峨〒蜿門ｾ怜､ｱ謨・, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

