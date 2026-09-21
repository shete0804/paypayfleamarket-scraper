#!/usr/bin/env python3
"""
PayPay フリマ MEGA シリーズ カード価格モニター
============================================

対象カードごとに PayPay フリマ検索を実行し、「販売中」かつ「価格の安い順」で
上位 3 件（カード名・価格・URL）を取得して Discord に Embed 形式で通知する。

GitHub Actions から 6 時間ごとに実行される想定。

必要な環境変数:
    DISCORD_WEBHOOK_URL   Discord Incoming Webhook の URL

必要なライブラリ:
    selenium              ブラウザ自動化
    requests              HTTP リクエスト送信
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
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
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

socket.setdefaulttimeout(10)
try:
    socket.gaierror
    import socket as sock_module
    original_getaddrinfo = sock_module.getaddrinfo

    def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return original_getaddrinfo(host, port, family, type, proto, flags)
        except socket.gaierror:
            import subprocess
            try:
                result = subprocess.check_output(['nslookup', host, '8.8.8.8'], stderr=subprocess.DEVNULL, timeout=5).decode()
                if 'Address:' in result:
                    return original_getaddrinfo(host, port, family, type, proto, flags)
            except:
                pass
            raise

    sock_module.getaddrinfo = patched_getaddrinfo
except:
    pass

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


@dataclass
class Listing:
    card: str
    price: int
    url: str


# ---------------------------------------------------------------------------
# 商品フィルタリング
# ---------------------------------------------------------------------------


def is_single_card(title: str) -> bool:
    title_lower = title.lower()
    return not any(keyword in title_lower for keyword in EXCLUDE_KEYWORDS)


# ---------------------------------------------------------------------------
# PayPay フリマ検索
# ---------------------------------------------------------------------------


def search_card(keyword: str) -> list[Listing]:
    listings: list[Listing] = []

    try:
        print(f"検索中: {keyword}", file=sys.stderr)

        import socket
        try:
            ip_addr = socket.gethostbyname("www.paypayfleamarket.yahoo.co.jp")
            print(f"DEBUG: Resolved www.paypayfleamarket.yahoo.co.jp to {ip_addr}", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: DNS resolution failed: {e}", file=sys.stderr)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        chrome_options.add_argument("--dns-prefetch-disable")
        chrome_options.add_argument("--no-first-run")
        chrome_options.binary_location = "/usr/bin/google-chrome"

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            url = f"https://www.paypayfleamarket.yahoo.co.jp/search?keyword={urlencode({'q': keyword})}&sort=score"
            print(f"DEBUG: Accessing URL: {url}", file=sys.stderr)
            driver.get(url)

            wait = WebDriverWait(driver, 20)

            # JavaScriptが実行されるまで待機
            try:
                wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "[class*='ProductCard']")
                    )
                )
                print(f"DEBUG: ProductCard elements detected", file=sys.stderr)
            except Exception as e:
                print(f"DEBUG: ProductCard wait timed out: {e}", file=sys.stderr)

            # ページ全体のHTMLをダンプして分析
            try:
                body_html = driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
                print(f"DEBUG: Page HTML length: {len(body_html)} characters", file=sys.stderr)

                # 複数のセレクタを試して確認
                selectors_to_check = [
                    ".ProductCard",
                    "[class*='ProductCard']",
                    ".c-productCard",
                    "[data-testid*='product']",
                    "article[class*='Product']",
                    ".product",
                    "[class*='product-card']",
                    "div[class*='card'][class*='product']",
                    "[class*='item'][class*='product']"
                ]

                for selector in selectors_to_check:
                    try:
                        found = driver.find_elements(By.CSS_SELECTOR, selector)
                        if found:
                            print(f"DEBUG: Selector '{selector}' found {len(found)} items", file=sys.stderr)
                    except:
                        pass

            except Exception as e:
                print(f"DEBUG: Error dumping HTML: {e}", file=sys.stderr)

            items = driver.find_elements(By.CSS_SELECTOR, ".ProductCard")
            print(f"DEBUG: Found {len(items)} items with .ProductCard selector", file=sys.stderr)

            if not items:
                print(f"DEBUG: .ProductCard not found, trying alternative selectors", file=sys.stderr)
                items = driver.find_elements(By.CSS_SELECTOR, "[class*='ProductCard']")
                print(f"DEBUG: Found {len(items)} items with [class*='ProductCard'] selector", file=sys.stderr)

            if not items:
                items = driver.find_elements(By.CSS_SELECTOR, ".c-productCard")
                print(f"DEBUG: Found {len(items)} items with .c-productCard selector", file=sys.stderr)

            if not items:
                items = driver.find_elements(By.CSS_SELECTOR, "[data-testid*='product']")
                print(f"DEBUG: Found {len(items)} items with [data-testid*='product'] selector", file=sys.stderr)

            if not items:
                items = driver.find_elements(By.CSS_SELECTOR, "article[class*='Product']")
                print(f"DEBUG: Found {len(items)} items with article[class*='Product'] selector", file=sys.stderr)

            # 要素が見つかった場合の処理
            if items:
                for item in items:
                    if len(listings) >= TOP_N:
                        break

                    try:
                        # セレクタの柔軟性を高める
                        title_elem = None
                        price_elem = None
                        link_elem = None

                        # タイトルを取得（複数の試行）
                        for title_sel in [".ProductCard__title", "[class*='title']", "h2", "h3"]:
                            try:
                                title_elem = item.find_element(By.CSS_SELECTOR, title_sel)
                                if title_elem.text:
                                    break
                            except:
                                pass

                        if not title_elem or not title_elem.text:
                            continue

                        title = title_elem.text

                        if not is_single_card(title):
                            print(f"除外: {title}", file=sys.stderr)
                            continue

                        # 価格を取得（複数の試行）
                        for price_sel in [".ProductCard__priceWrapper", "[class*='price']", "span"]:
                            try:
                                elems = item.find_elements(By.CSS_SELECTOR, price_sel)
                                for elem in elems:
                                    price_text = elem.text.replace("¥", "").replace(",", "").strip()
                                    if price_text and price_text[0].isdigit():
                                        price_elem = elem
                                        break
                                if price_elem:
                                    break
                            except:
                                pass

                        if not price_elem:
                            print(f"価格要素が見つかりません: {title}", file=sys.stderr)
                            continue

                        price_text = price_elem.text.replace("¥", "").replace(",", "")

                        try:
                            price = int(price_text)
                        except ValueError:
                            print(f"無効な価格: {title} ({price_text})", file=sys.stderr)
                            continue

                        # URL を取得
                        link_elem = item.find_element(By.CSS_SELECTOR, "a")
                        url = link_elem.get_attribute("href")

                        if not url.startswith("http"):
                            url = "https://www.paypayfleamarket.yahoo.co.jp" + url

                        listings.append(Listing(card=keyword, price=price, url=url))
                        print(
                            f"取得: {title} - ¥{price:,}",
                            file=sys.stderr,
                        )

                    except Exception as e:
                        print(
                            f"アイテム処理エラー ({keyword}): {type(e).__name__}: {e}",
                            file=sys.stderr,
                        )
                        continue
            else:
                # セレクタが見つからない場合、JavaScriptで直接取得を試みる
                print(f"DEBUG: No items found with CSS selectors, trying aggressive JavaScript extraction", file=sys.stderr)
                try:
                    # より攻撃的な DOM 走査: すべての div を検査
                    js_code = """
                    const items = [];

                    // 戦略1: すべての article タグを検査
                    document.querySelectorAll('article').forEach(article => {
                        const titleEl = article.querySelector('h1, h2, h3, .ProductCard__title, [class*="title"]');
                        const priceEl = Array.from(article.querySelectorAll('*')).find(el => {
                            const text = el.textContent || '';
                            return /¥|￥/.test(text) && /\d/.test(text);
                        });
                        const linkEl = article.querySelector('a[href]');

                        if (titleEl && priceEl && linkEl) {
                            items.push({
                                title: titleEl.textContent.trim(),
                                price: priceEl.textContent.trim(),
                                url: linkEl.href
                            });
                        }
                    });

                    // 戦略2: 任意のコンテナ（class*="product"やclass*="card"）を検査
                    if (items.length === 0) {
                        document.querySelectorAll('[class*="product"], [class*="card"]').forEach(container => {
                            const titleEl = container.querySelector('h1, h2, h3, [class*="title"]');
                            const priceEl = Array.from(container.querySelectorAll('*')).find(el => {
                                const text = el.textContent || '';
                                return /¥|￥/.test(text) && /\d/.test(text) && text.length < 50;
                            });
                            const linkEl = container.querySelector('a[href]');

                            if (titleEl && priceEl && linkEl && titleEl.textContent.trim().length > 3) {
                                const existing = items.find(i => i.title === titleEl.textContent.trim());
                                if (!existing) {
                                    items.push({
                                        title: titleEl.textContent.trim(),
                                        price: priceEl.textContent.trim(),
                                        url: linkEl.href
                                    });
                                }
                            }
                        });
                    }

                    return items.slice(0, 10);
                    """
                    result = driver.execute_script(js_code)
                    print(f"DEBUG: Aggressive JavaScript extraction returned {len(result)} items", file=sys.stderr)
                    for item_data in result[:TOP_N]:
                        try:
                            title = item_data['title'].strip()
                            if not is_single_card(title):
                                continue
                            price_text = item_data['price'].replace("¥", "").replace("￥", "").replace(",", "").split()[0]
                            price = int(price_text)
                            url = item_data['url']
                            if not url.startswith("http"):
                                url = "https://www.paypayfleamarket.yahoo.co.jp" + url
                            listings.append(Listing(card=keyword, price=price, url=url))
                            print(f"取得（JS）: {title} - ¥{price:,}", file=sys.stderr)
                        except Exception as e:
                            print(f"JS抽出エラー: {e}", file=sys.stderr)
                            continue
                except Exception as e:
                    print(f"DEBUG: JavaScript execution failed: {e}", file=sys.stderr)

            print(f"完了: {keyword} ({len(listings)} 件)", file=sys.stderr)

        finally:
            driver.quit()

    except Exception as e:
        print(
            f"検索エラー ({keyword}): {type(e).__name__}: {e}",
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
    except Exception:
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

