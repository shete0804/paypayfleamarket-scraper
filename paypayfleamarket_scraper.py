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
from datetime import datetime, timedelta, timezone

import requests

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()

# 修正: 登録済みカード 2 つのみに限定（2026-09-22）
CARD_KEYWORDS: list[str] = [
    "メガルカリオex MUR メガブレイブ",
    "リーリエの決心 SAR メガブレイブ",
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
# PayPay フリマ検索
# ---------------------------------------------------------------------------


def search_card(keyword: str) -> list[Listing]:
    listings: list[Listing] = []

    try:
        print(f"検索中: {keyword}", file=sys.stderr)

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
        # ブロック対策：User-Agent を設定
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        # 追加の互換性オプション
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.binary_location = "/usr/bin/google-chrome"

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(15)

        try:
            # トップページに移動（リトライ付き）
            print(f"PayPay フリマのトップページにアクセス中", file=sys.stderr)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    driver.get("https://www.paypayfleamarket.yahoo.co.jp/")
                    print(f"ページロード待機中...", file=sys.stderr)
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.NAME, "word"))
                    )
                    # ページが完全に読み込まれたか確認
                    doc_ready = driver.execute_script("return document.readyState")
                    print(f"Document Ready State: {doc_ready}", file=sys.stderr)

                    # ページ内容をチェック
                    page_title = driver.title
                    body_text_length = len(driver.execute_script("return document.body.innerText"))
                    print(f"ページタイトル: {page_title}, Body テキスト長: {body_text_length}", file=sys.stderr)

                    print(f"トップページアクセス成功（試行 {attempt + 1}/{max_retries}）", file=sys.stderr)
                    break
                except Exception as retry_error:
                    print(f"トップページアクセス失敗（試行 {attempt + 1}/{max_retries}）: {retry_error}", file=sys.stderr)
                    print(f"ページソース長: {len(driver.page_source)}", file=sys.stderr)
                    if attempt == max_retries - 1:
                        raise
                    import time
                    time.sleep(2)

            # 検索欄に「keyword + 新品」と入力
            try:
                search_box = driver.find_element(By.NAME, "word")
                print(f"検索欄が見つかりました", file=sys.stderr)
            except:
                print(f"検索欄が見つかりません。ページソース先頭5000文字を出力:", file=sys.stderr)
                print(f"{driver.page_source[:5000]}", file=sys.stderr)
                raise

            search_box.clear()
            search_box.send_keys(f"{keyword} 新品")
            print(f"検索欄に入力: {keyword} 新品", file=sys.stderr)

            # 検索ボタンをクリック（複数のセレクタで試行）
            search_btn_selectors = [
                ".sc-14dcb79f-4 > img",
                "button[type='submit']",
                "[class*='search'][class*='button']",
                "button",
                "[role='button']",
                "input[type='submit']"
            ]
            search_btn = None
            for selector in search_btn_selectors:
                try:
                    candidates = driver.find_elements(By.CSS_SELECTOR, selector)
                    if candidates:
                        search_btn = candidates[0]
                        print(f"検索ボタン検出: {selector}", file=sys.stderr)
                        break
                except:
                    pass

            if not search_btn:
                print(f"検索ボタンが見つかりません。Enterキーで検索実行", file=sys.stderr)
                search_box.send_keys(Keys.RETURN)
            else:
                try:
                    search_btn.click()
                except:
                    print(f"ボタンクリック失敗。JavaScript実行で代替", file=sys.stderr)
                    driver.execute_script("arguments[0].click();", search_btn)
            print(f"検索実行", file=sys.stderr)
            WebDriverWait(driver, 15).until(
                EC.url_contains("search")
            )

            # 検索結果ページの確認
            current_url = driver.current_url
            print(f"検索後のURL: {current_url}", file=sys.stderr)

            # ページが完全に読み込まれるまで待機
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            print(f"ページ完全読み込み完了", file=sys.stderr)

            # 「販売中のみ」フィルターをクリック（最初の検索結果から）
            try:
                # 販売中チェックボックスを見つけてクリック
                live_only_checkbox = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox'][class*='live'], input[type='checkbox'][class*='status']"))
                )
                if not live_only_checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", live_only_checkbox)
                    print(f"「販売中のみ」フィルターを有効化", file=sys.stderr)
                    WebDriverWait(driver, 10).until(
                        EC.staleness_of(live_only_checkbox)
                    )
            except Exception as e:
                print(f"フィルター処理をスキップ: {e}", file=sys.stderr)

            # ページをスクロールして遅延ロード要素を読み込む
            print(f"ページをスクロール中...", file=sys.stderr)
            driver.execute_script("window.scrollBy(0, window.innerHeight);")
            import time
            time.sleep(2)

            # 複数の商品を試す（最初の 5 つまで）
            # セレクタ候補（複数レベルでフォールバック）
            selectors = [
                "a[href*='/item/']",  # 直接的なitem URL
                "[class*='ProductCard'] a",
                "[class*='product'] a",
                "[class*='listing'] a",
                "li a[href*='item']",
                "div[class*='card'] a",
                "a.ProductCard__link",
                "a[href*='paypayfleamarket']",
                "a"  # 最後の手段：すべてのリンク
            ]

            product_links = []
            for selector in selectors:
                try:
                    candidates = driver.find_elements(By.CSS_SELECTOR, selector)
                    # リンク検証：href が item ページを指しているか確認
                    valid_links = [link for link in candidates if link.get_attribute('href') and '/item/' in link.get_attribute('href')]
                    if valid_links:
                        product_links = valid_links
                        print(f"セレクタ成功: {selector} - {len(product_links)}個の有効な商品リンク", file=sys.stderr)
                        break
                    else:
                        print(f"セレクタ試行: {selector} - 候補{len(candidates)}個だが有効なitem URLなし", file=sys.stderr)
                        # 見つかった要素の詳細情報を出力
                        for i, cand in enumerate(candidates[:3]):
                            print(f"  [候補{i+1}] tag={cand.tag_name}, class={cand.get_attribute('class')}, href={cand.get_attribute('href')[:60] if cand.get_attribute('href') else 'N/A'}", file=sys.stderr)
                except Exception as selector_error:
                    print(f"セレクタエラー: {selector} - {selector_error}", file=sys.stderr)

            if not product_links:
                print(f"商品リンクが見つかりません（すべてのセレクタで失敗）", file=sys.stderr)
                # ページ内のすべてのリンクを列挙してデバッグ
                all_links = driver.find_elements(By.TAG_NAME, "a")
                print(f"ページ内の全リンク数: {len(all_links)}", file=sys.stderr)
                print(f"最初の20個のリンク: ", file=sys.stderr)
                for i, link in enumerate(all_links[:20]):
                    print(f"  [{i+1}] tag={link.tag_name}, class={link.get_attribute('class')}, href={link.get_attribute('href')[:60] if link.get_attribute('href') else 'N/A'}, text={link.text[:30] if link.text else 'N/A'}", file=sys.stderr)
                # ページの HTML 構造を出力（最初の 5000 文字）
                print(f"=== ページソース先頭5000文字 ===", file=sys.stderr)
                print(driver.page_source[:5000], file=sys.stderr)
                print(f"=== ページソース終了 ===", file=sys.stderr)
                return listings

            print(f"見つかった商品数: {len(product_links)}", file=sys.stderr)
            # 見つかったリンクの詳細情報を出力
            for i, link in enumerate(product_links[:5]):
                href = link.get_attribute('href')
                text = link.text
                print(f"  [商品{i+1}] href={href}, text={text[:50] if text else 'N/A'}", file=sys.stderr)

            for product_index in range(min(5, len(product_links))):
                try:
                    print(f"--- 商品 {product_index + 1} を試行 ---", file=sys.stderr)

                    # 商品リンク再取得（DOM 更新対応）
                    product_links_selectors = [
                        "a[href*='/item/']",
                        "[class*='ProductCard'] a",
                        "[class*='product'] a",
                        "li a[href*='item']",
                        "a.ProductCard__link"
                    ]
                    product_links_retry = []
                    for selector in product_links_selectors:
                        try:
                            product_links_retry = driver.find_elements(By.CSS_SELECTOR, selector)
                            if product_links_retry:
                                break
                        except:
                            pass
                    product_links = product_links_retry if product_links_retry else product_links
                    if product_index >= len(product_links):
                        print(f"商品 {product_index + 1} はリスト外", file=sys.stderr)
                        break

                    product_link = product_links[product_index]
                    driver.execute_script("arguments[0].click();", product_link)
                    print(f"商品 {product_index + 1} をクリック", file=sys.stderr)

                    # 詳細ページへのナビゲーション待機
                    WebDriverWait(driver, 10).until(
                        EC.url_contains("item/")
                    )

                    # 詳細ページから商品データを抽出
                    current_url = driver.current_url
                    print(f"詳細ページURL: {current_url}", file=sys.stderr)

                    # DOM 全体をスキャンしてテキストを取得
                    page_text = driver.execute_script("return document.body.innerText || ''")
                    print(f"ページテキスト取得: {len(page_text)} 文字", file=sys.stderr)
                    print(f"ページテキスト先頭 500 文字: {page_text[:500]}", file=sys.stderr)

                    # 正規表現で商品名と価格を抽出
                    # 商品名：keyword を含む 5 文字以上のテキスト
                    import re

                    title = None
                    price = None

                    # 商品名抽出：keyword を含み、複数単語セット除外語を含まない行を探す
                    lines = page_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if keyword in line and len(line) > 5:
                            if not any(exclude in line for exclude in EXCLUDE_KEYWORDS):
                                title = line
                                print(f"商品名候補: {line}", file=sys.stderr)
                                break

                    # 代替：最初の有意なタイトル形式を探す
                    if not title:
                        for line in lines:
                            line = line.strip()
                            if 5 < len(line) < 200 and not any(exclude in line for exclude in EXCLUDE_KEYWORDS):
                                if not any(c.isdigit() for c in line[:5]):  # 最初の 5 文字に数字がない
                                    title = line
                                    break

                    if not title:
                        print(f"商品名が取得できません: keyword='{keyword}'", file=sys.stderr)
                        print(f"商品 {product_index + 1} を Skip → 次へ", file=sys.stderr)
                        continue  # 次の商品へ

                    print(f"商品名: {title}", file=sys.stderr)

                    if not is_single_card(title):
                        print(f"除外（複数枚セット等）: {title}", file=sys.stderr)
                        print(f"商品 {product_index + 1} を Skip → 次へ", file=sys.stderr)
                        continue  # 次の商品へ

                    # 価格抽出：¥XXXXX 形式または数字 5 桁以上
                    price_match = re.search(r'¥[\s]?(\d+(?:,\d+)*)', page_text)
                    if not price_match:
                        # 代替：単純な数字を探す（4 桁以上）
                        price_match = re.search(r'\b(\d{4,})\b', page_text)

                    if price_match:
                        price_str = price_match.group(1).replace(',', '')
                        try:
                            price = int(price_str)
                        except:
                            pass

                    if not price:
                        print(f"価格が取得できません: {title}", file=sys.stderr)
                        print(f"商品 {product_index + 1} を Skip → 次へ", file=sys.stderr)
                        continue  # 次の商品へ

                    print(f"価格: ¥{price:,}", file=sys.stderr)

                    listings.append(Listing(card=keyword, price=price, url=current_url))
                    print(f"取得完了: {title} - ¥{price:,}", file=sys.stderr)

                    # TOP_N 件に達したら終了
                    if len(listings) >= TOP_N:
                        print(f"TOP_N ({TOP_N} 件) に達したため終了", file=sys.stderr)
                        break

                except Exception as e:
                    print(f"商品 {product_index + 1} 抽出エラー: {type(e).__name__}: {e}", file=sys.stderr)
                    continue  # 次の商品へ

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

