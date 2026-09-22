# PayPay Flea Market × Mercari 値段差比較 スクレイパー

## システム概要

18種類のポケモンカード（MEGA シリーズ）の価格を PayPay フリマから取得し、Discord に定期レポートを送信するシステム。

## 機能

- ✅ **自動スクレイピング**: GitHub Actions で6時間ごと自動実行
- ✅ **Discord 通知**: 最安値3件を含む価格レポートを Discord に送信  
- ✅ **18カード対応**: MEGA ブレイブ、MEGAドリームex、他の全セット

## ファイル構成

```
├── update_listings.py          # PayPay から最新価格を取得
├── paypayfleamarket_scraper.py # Discord に価格を送信
├── listings.json               # 価格データ（JSON形式）
├── .github/workflows/
│   └── scraper.yml            # GitHub Actions ワークフロー
└── requirements.txt           # Python 依存パッケージ
```

## 動作フロー

1. **update_listings.py** が PayPay Flea Market を検索
2. 各カードの最安値 3 件を抽出 → `listings.json` に保存
3. **paypayfleamarket_scraper.py** が `listings.json` を読込
4. Discord Webhook 経由で通知を送信

## 環境構築

### GitHub Secrets の設定（必須）

1. `DISCORD_WEBHOOK_URL`: Discord サーバーの Webhook URL
2. `GITHUB_TOKEN`: 自動で生成（既に設定済み）

### ローカルテスト

```bash
pip install requests beautifulsoup4
python update_listings.py  # 価格取得テスト
python paypayfleamarket_scraper.py  # Discord 送信テスト
```

## トラブルシューティング

### 価格が ¥0 の場合

PayPay Flea Market は JavaScript で動的にコンテンツを読み込みます。  
現在の実装は HTTP リクエストの静的 HTML に対応しているため、以下の改善が必要：

**解決策:**
- Selenium または Playwright でブラウザ自動化に対応
- または PayPay の API エンドポイントを直接利用

## GitHub Actions スケジュール

```yaml
schedule:
  - cron: '0 */6 * * *'  # 毎日 0時, 6時, 12時, 18時 JST に実行
```

## 今後の改善

1. **Playwright 統合**: JavaScript 動的コンテンツ対応
2. **Mercari 連携**: 値段差比較機能
3. **エラー通知**: Discord でエラーアラート
4. **パフォーマンス最適化**: 並列処理導入
