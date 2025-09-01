# Django API テストスイート

ソーシャルナビゲーター バックエンドAPIのテストスイートです。

## 📁 ディレクトリ構成

```
tests/
├── unit/                    # 単体テスト
│   ├── test_models.py      # モデルテスト
│   ├── test_serializers.py # シリアライザーテスト
│   └── test_views.py       # ビューテスト
├── integration/            # API統合テスト
│   ├── test_auth_api.py    # 認証API
│   ├── test_clients_api.py # クライアントAPI
│   ├── test_companies_api.py # 企業API
│   ├── test_projects_api.py # 案件API
│   ├── test_masters_api.py # マスターAPI
│   └── test_dashboard_api.py # ダッシュボードAPI
├── fixtures/               # テストデータ
│   ├── test_users.json
│   ├── test_clients.json
│   └── test_companies.json
├── shell_scripts/          # シェルスクリプトテスト
│   ├── test_auth.sh
│   ├── test_companies.sh
│   └── run_all_api_tests.sh
└── README.md              # このファイル
```

## 🚀 実行方法

### Django標準テスト
```bash
# 全テスト実行
python3 manage.py test tests

# 個別テスト実行
python3 manage.py test tests.unit.test_models
python3 manage.py test tests.integration.test_auth_api
```

### シェルスクリプトテスト
```bash
# API動作確認（curl使用）
cd tests/shell_scripts
./run_all_api_tests.sh
```

## 📋 テスト対象

### v0レポート解決確認
- ✅ `POST /companies/` - 企業作成API
- ✅ `DELETE /projects/{id}/` - プロジェクト削除API
- ✅ `GET /auth/me` - ユーザー情報取得API
- ✅ `GET /dashboard/stats` - ダッシュボード統計API
- ✅ `GET /master/industries` - 業界マスターAPI
- ✅ `GET /master/statuses` - ステータスマスターAPI

### API機能テスト
- JWT認証フロー
- CRUD操作（作成・読取・更新・削除）
- 検索・フィルタ機能
- ページネーション
- エラーハンドリング
- 権限制御

## 🔧 テスト環境

- **Django**: localhost:8080
- **データベース**: SQLite（テスト用）
- **認証**: JWT Bearer Token