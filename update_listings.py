#!/usr/bin/env python3
"""PayPay Flea Market scraper (undetected-chromedriver - bot検出回避)"""

import json
import re
import sys
import time
from urllib.parse import quote

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CARD_KEYWORDS = [
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
    "メガカイリューex SAR メガドリームex",
    "メガジガルデex MUR ムニキスゼロ",
    "ニャースex SAR ムニキスゼロ",
    "メイのはげまし SAR ムニキスゼロ",
    "メガゲッコウガex MUR ニンジャスピナー",
    "メガゲッコウガex SAR ニンジャスピナー",
    "メガダークライex MUR アビスアイ",
    "メガダークライex SAR アビスアイ",
]

EXCLUDE_KEYWORDS = [
    "セット", "2枚", "3枚", "4枚", "5枚", "10枚", "20枚",
    "5パック", "10パック", "Box", "ボックス", "まとめ売り",
    "福袋", "構築済みデッキ", "デッキ", "旧裏", "おまけ",
]

TOP_N = 3


def log_print(msg):
    """ログ出力"""
    print(msg, file=sys.stderr)


def scrape_keyword(driver, keyword: str) -> list:
    """キーワード検索のスクレイピング"""
    try:
        search_url = f"https://www.paypayfleamarket.yahoo.co.jp/search?query={quote(keyword)}"
        log_print(f"[LOAD] {search_url}")
        driver.get(search_url)

        # ページ読み込み待機
        log_print(f"[WAIT] ページ読み込み中...")
        time.sleep(3)

        # 出品情報の取得
        results = []

        try:
            # 商品リスト要素を探す（複数のセレクタを試す）
            items = None
            for selector in [
                "div[data-testid='product-card']",
                "div[class*='ProductCard']",
                "li[class*='product']",
                "article",
            ]:
                try:
                    items = driver.find_elements(By.CSS_SELECTOR, selector)
                    if items and len(items) > 0:
                        log_print(f"[FOUND] セレクタ '{selector}' で {len(items)} 件見つかりました")
                        break
                except:
                    continue

            if not items:
                log_print(f"[FAIL] 商品要素が見つかりません")
                return []

            # 価格情報を抽出
            for item in items[:20]:
                try:
                    # タイトル取得
                    title_elem = None
                    for title_selector in ["h2", "h3", "[class*='title']", "a"]:
                        try:
                            title_elem = item.find_element(By.CSS_SELECTOR, title_selector)
                            if title_elem and title_elem.text:
                                break
                        except:
                            continue

                    if not title_elem or not title_elem.text:
                        continue
                    title = title_elem.text[:50]

                    # 価格取得
                    price = None
                    price_text = item.text
                    price_match = re.search(r'¥([\d,]+)', price_text)
                    if price_match:
                        price = int(price_match.group(1).replace(",", ""))

                    if not price:
                        continue

                    # URL取得
                    url = ""
                    try:
                        link = item.find_element(By.TAG_NAME, "a")
                        url = link.get_attribute("href")
                    except:
                        pass

                    if not url.startswith("http"):
                        url = f"https://www.paypayfleamarket.yahoo.co.jp{url}"

                    # フィルタリング
                    if any(kw in title for kw in EXCLUDE_KEYWORDS):
                        continue

                    results.append({
                        "title": title,
                        "price": price,
                        "url": url,
                    })

                    if len(results) >= TOP_N:
                        break

                except Exception as e:
                    continue

        except Exception as e:
            log_print(f"[PARSE_ERROR] {type(e).__name__}: {str(e)[:100]}")

        log_print(f"[SUCCESS] {len(results)} 件取得")
        return results

    except Exception as e:
        log_print(f"[ERROR] {type(e).__name__}: {str(e)[:100]}")
        return []


def main():
    """メイン処理"""
    log_print("[START] PayPay Flea Market スクレイピング開始")
    log_print(f"[INFO] {len(CARD_KEYWORDS)} 個のキーワードを処理")

    driver = None
    data = {}
    success_count = 0

    try:
        # undetected-chromedriver でブラウザ起動
        log_print("[INIT] undetected-chromedriver を起動...")
        driver = uc.Chrome(
            headless=True,
            use_subprocess=False,
            browser_executable_path="/usr/bin/chromium-browser"
        )

        for i, keyword in enumerate(CARD_KEYWORDS, 1):
            log_print(f"\n[{i}/{len(CARD_KEYWORDS)}] {keyword}")
            results = scrape_keyword(driver, keyword)

            if results:
                data[keyword] = results
                success_count += 1

    except Exception as e:
        log_print(f"[CRITICAL] {type(e).__name__}: {str(e)[:100]}")

    finally:
        if driver:
            try:
                driver.quit()
                log_print("[CLEANUP] ブラウザを閉じました")
            except:
                pass

    # 結果を保存
    log_print(f"\n[END] 合計 {success_count}/{len(CARD_KEYWORDS)} 件成功")

    if success_count > 0:
        with open("listings.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_print("[SAVE] listings.json を更新しました")
    else:
        log_print("[KEEP] スクレイピング失敗のため、既存の listings.json を保持")


if __name__ == "__main__":
    main()
