# Swagger モックサーバー

ソーシャルナビゲーターのAPIモックサーバーです。

## セットアップ

### 1. 依存関係のインストール

```bash
# Prismのグローバルインストール
npm run install:prism

# Swagger CLIのグローバルインストール（検証用）
npm run install:swagger-cli
```

### 2. OpenAPI定義の検証

```bash
npm run validate
```

## モックサーバーの起動

### 静的レスポンスモード（デフォルト）

設定されたサンプルデータを返します。

```bash
npm run mock
```

### 動的レスポンスモード

OpenAPI定義から自動生成されたデータを返します。

```bash
npm run mock:dynamic
```

## アクセス情報

- **モックサーバーURL**: http://localhost:4010
- **Swagger UI**: Prism起動後、ブラウザで http://localhost:4010 にアクセス

## API使用例

### ログイン

```bash
curl -X POST http://localhost:4010/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### 企業一覧取得

```bash
curl -X GET "http://localhost:4010/companies?page=1&page_size=50" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### 企業作成

```bash
curl -X POST http://localhost:4010/companies \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -d '{
    "name": "株式会社テスト",
    "industry": "IT・ソフトウェア",
    "employee_count": 100,
    "prefecture": "東京都"
  }'
```

## ディレクトリ構造

```
swagger/
├── openapi.yaml        # OpenAPI定義ファイル
├── package.json        # npm設定ファイル
├── README.md          # このファイル
└── examples/          # サンプルデータ（今後追加予定）
    ├── companies.json
    ├── projects.json
    └── users.json
```

## 注意事項

- モックサーバーは開発環境でのみ使用してください
- 実際のデータベースとは接続されていません
- 認証トークンは固定値を使用しています
- CORSは有効化されています

## トラブルシューティング

### ポート4010が使用中の場合

```bash
# 別のポートで起動
prism mock -h 0.0.0.0 -p 3000 --cors openapi.yaml
```

### Prismがインストールできない場合

```bash
# npmキャッシュをクリア
npm cache clean --force

# 再インストール
npm install -g @stoplight/prism-cli
```