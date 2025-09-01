# ソーシャルナビゲーター バックエンド

Django REST Framework によるBtoB営業支援プラットフォームのAPIサーバー

## 📋 ディレクトリ構成

```
saleslist-backend/
├── accounts/              # ユーザー認証・管理
├── clients/               # クライアント管理
├── companies/             # 企業マスター管理
├── projects/              # 案件・営業ステータス管理
├── masters/               # マスターデータ管理
├── dashboard/             # ダッシュボード統計
├── filters/               # 保存フィルター機能
├── executives/            # 役員管理
├── ng_companies/          # NG企業管理
├── database/              # PostgreSQL Dockerコンテナ
├── redis/                 # Redis Dockerコンテナ（将来使用）
├── docker/                # Docker Compose設定
├── tests/                 # APIテストスイート
├── docs/                  # 設計書・API仕様書
├── manage.py              # Django管理コマンド
├── requirements.txt       # Python依存関係
└── seed_data.py          # 初期データ投入スクリプト
```

## 🚀 起動手順

### **1. データベース起動**
```bash
# PostgreSQL (Docker)
cd docker
docker-compose -f docker-compose.dev.yml up -d database

# または既存コンテナ起動
docker start social-navigator-database-dev
```

### **2. Django Backend起動**
```bash
# 依存関係インストール（初回のみ）
pip3 install -r requirements.txt

# マイグレーション実行（初回のみ）
python3 manage.py migrate

# 初期データ投入（初回のみ）
python3 seed_data.py

# 開発サーバー起動
python3 manage.py runserver 8080
```

### **3. 動作確認**
```bash
# API応答確認
curl http://localhost:8080/api/v1/auth/login

# ダッシュボード確認
curl http://localhost:8080/admin/
```

## 🎯 主要API仕様

### **認証API**
- `POST /api/v1/auth/login` - ログイン
- `GET /api/v1/auth/me` - ユーザー情報取得
- `GET /api/v1/auth/users/` - ユーザー一覧（設定画面用）
- `POST /api/v1/auth/users/create/` - ユーザー作成

### **データ管理API**
- `GET/POST/PUT/DELETE /api/v1/clients/` - クライアント管理
- `GET/POST/PUT/DELETE /api/v1/companies/` - 企業管理（15項目）
- `GET/POST/PUT/DELETE /api/v1/projects/` - プロジェクト管理

### **営業管理API**
- `GET /api/v1/projects/{id}/companies/` - 案件企業一覧
- `PUT /api/v1/projects/{id}/companies/{company_id}/` - 営業ステータス更新
- `POST /api/v1/projects/{id}/add-companies/` - 企業追加

### **マスターデータAPI**
- `GET /api/v1/master/industries/` - 業界マスター
- `GET /api/v1/master/prefectures/` - 都道府県マスター（47件）
- `GET /api/v1/master/sales-statuses/` - 営業ステータスマスター（13種類）

### **ダッシュボードAPI**
- `GET /api/v1/dashboard/stats` - 統計データ
- `GET /api/v1/dashboard/recent-projects` - 最近のプロジェクト
- `GET /api/v1/dashboard/recent-companies` - 最近の企業

## 🔧 技術スタック

- **Django**: 5.2.5
- **Django REST Framework**: 3.16.1
- **PostgreSQL**: 15 (Docker)
- **JWT認証**: djangorestframework-simplejwt
- **CORS**: django-cors-headers
- **フィルタリング**: django-filter

## 📊 データベース

### **主要テーブル**
- **clients**: クライアント情報
- **companies**: 企業マスター（15項目拡張済み）
- **projects**: 案件管理
- **project_companies**: 案件企業関係・営業ステータス管理
- **sales_history**: 営業履歴（ステータス変更履歴）
- **industries**: 業界マスター（11種類）
- **statuses**: ステータスマスター（営業13種類含む）
- **prefectures**: 都道府県マスター（47都道府県）

### **初期データ**
- **テストユーザー**: `user@example.com` / `password123`
- **クライアント**: 2社
- **企業**: 9社（多様な業界・所在地）
- **プロジェクト**: 1案件

## 🧪 テスト実行

```bash
# 全APIテスト
cd tests
python3 check_all_apis.py

# ユーザー管理APIテスト
python3 test_user_management.py

# Django管理画面
http://localhost:8080/admin/
```

## 🌐 本番デプロイ

さくらapp run用のDocker設定が `docker/` ディレクトリに準備済み：
- `docker-compose.yml` - 本番用
- `docker-compose.dev.yml` - 開発用

## 📞 サポート

- **API仕様書**: `docs/screen_api_specification.md`
- **DB設計書**: `docs/DB_design.md`
- **OpenAPI仕様**: `deployment/swagger/openapi.yaml`