# OpenAPI ファイル構成

## 📁 現在使用中のファイル

### メインファイル
- **`openapi.yaml`** (202K) - 🚀 **Renderデプロイ用（本番）**
  - Dockerfileで使用される統合版
  - すべてのAPI定義とスキーマを含む完全版

### 開発用分割ファイル
- **`openapi-main.yaml`** (188K) - API paths定義
  - エンドポイント定義のみ
  - 開発時の編集用
  
- **`openapi-schemas.yaml`** (15K) - スキーマ定義
  - データモデル定義
  - components/schemas部分

- **`openapi-merged.yaml`** (202K) - 統合テスト用
  - merge-openapi.shで生成される
  - openapi-main.yaml + openapi-schemas.yaml

### 設定ファイル
- **`render.yaml`** - Renderデプロイ設定
- **`Dockerfile`** - コンテナ設定（openapi.yamlを使用）

### スクリプト
- **`merge-openapi.sh`** - ファイル統合スクリプト
  ```bash
  ./merge-openapi.sh  # openapi-merged.yamlを生成
  ```

## 📁 ディレクトリ構成

```
deployment/swagger/
├── openapi.yaml              ← 本番用（Render）
├── openapi-main.yaml         ← 開発用（API定義）
├── openapi-schemas.yaml      ← 開発用（スキーマ）
├── openapi-merged.yaml       ← テスト用（統合版）
├── merge-openapi.sh          ← 統合スクリプト
├── Dockerfile                ← openapi.yamlを使用
├── render.yaml              
├── old/                      ← アーカイブ
│   ├── main.yaml
│   ├── openapi-test.yaml
│   ├── openapi-with-clients.yaml
│   └── openapi-with-data.yaml
├── openapi/                  ← 詳細分割版（実験的）
│   ├── openapi.yaml
│   ├── paths/
│   ├── schemas/
│   └── scripts/
└── examples/                 ← サンプルデータ

```

## 🔄 ワークフロー

### 開発時
1. `openapi-main.yaml` または `openapi-schemas.yaml` を編集
2. `./merge-openapi.sh` で統合版生成
3. `openapi-merged.yaml` でローカルテスト

### デプロイ時
```bash
# 統合版を本番用にコピー
cp openapi-merged.yaml openapi.yaml

# Git commit & push
git add openapi.yaml
git commit -m "Update API definitions"
git push

# Renderが自動デプロイ
```

## ⚠️ 注意事項
- **openapi.yaml** は本番用なので直接編集しない
- 開発は分割ファイルで行う
- デプロイ前に必ず統合版を生成する