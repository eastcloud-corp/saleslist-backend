# API一覧（拡張性考慮版）

## 拡張性について
- **マルチテナント対応**: 全APIにテナントIDを含める設計（現在は単一テナント）
- **外部API連携**: Facebook Graph API、LinkedIn API、メール送信API等の統合を想定
- **バージョニング**: `/api/v1/`形式でAPIバージョン管理
- **権限管理**: 将来的にロールベースアクセス制御（RBAC）を実装予定
- **webhook対応**: 外部システムとの連携用webhook機能を将来追加予定

## 基本設定
- **Base URL**: `https://api.budget-sales.com/api/v1/`
- **認証**: Bearer Token (Supabase JWT)
- **Content-Type**: `application/json`
- **将来対応予定**: 
  - テナントID: `X-Tenant-ID` ヘッダー
  - API Key認証: 外部システム連携用

---

## 1. 認証関連API

### 1.1 ログイン
```
POST /auth/login
```
**リクエスト**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**レスポンス**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "山田太郎"
  }
}
```

### 1.2 ログアウト
```
POST /auth/logout
```

### 1.3 トークン更新
```
POST /auth/refresh
```

---

## 2. 企業関連API

### 2.1 企業一覧取得
```
GET /companies/
```
**クエリパラメータ**
- `page`: ページ番号（デフォルト: 1）
- `page_size`: 1ページあたりの件数（デフォルト: 50）
- `search`: 企業名検索
- `industry`: 業界フィルタ
- `employee_min`: 従業員数最小値
- `employee_max`: 従業員数最大値
- `revenue_min`: 売上高最小値
- `revenue_max`: 売上高最大値
- `prefecture`: 都道府県
- `established_year_min`: 設立年最小値
- `established_year_max`: 設立年最大値
- `has_facebook`: Facebook URL有無（true/false）
- `exclude_ng`: NG企業除外（true/false）
- `project_id`: 案件IDによるNG企業除外
- `random_seed`: ランダム表示用シード値

**レスポンス**
```json
{
  "count": 25000,
  "next": "https://api.budget-sales.com/api/v1/companies/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "株式会社サンプル",
      "industry": "IT・ソフトウェア",
      "employee_count": 150,
      "revenue": 500000000,
      "prefecture": "東京都",
      "city": "渋谷区",
      "established_year": 2010,
      "website_url": "https://example.com",
      "contact_email": "info@example.com",
      "phone": "03-1234-5678",
      "notes": "備考",
      "is_global_ng": false,
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-15T15:30:00Z",
      "executives": [
        {
          "id": 1,
          "name": "山田太郎",
          "position": "代表取締役",
          "facebook_url": "https://facebook.com/yamada",
          "other_sns_url": "",
          "direct_email": "yamada@example.com"
        }
      ]
    }
  ]
}
```

### 2.2 企業詳細取得
```
GET /companies/{id}/
```

### 2.3 企業作成
```
POST /companies/
```
**リクエスト**
```json
{
  "name": "株式会社新規企業",
  "industry": "製造業",
  "employee_count": 100,
  "revenue": 300000000,
  "prefecture": "大阪府",
  "city": "大阪市",
  "established_year": 2015,
  "website_url": "https://newcompany.com",
  "contact_email": "info@newcompany.com",
  "phone": "06-1234-5678",
  "notes": "新規登録企業"
}
```

### 2.4 企業更新
```
PUT /companies/{id}/
PATCH /companies/{id}/
```

### 2.5 企業削除
```
DELETE /companies/{id}/
```

### 2.6 企業NG設定切り替え
```
POST /companies/{id}/toggle_ng/
```
**リクエスト**
```json
{
  "reason": "競合他社のため"
}
```

### 2.7 CSVインポート
```
POST /companies/import_csv/
```
**リクエスト（multipart/form-data）**
- `file`: CSVファイル

**レスポンス**
```json
{
  "success": true,
  "imported_count": 150,
  "error_count": 5,
  "errors": [
    {
      "row": 10,
      "message": "企業名が重複しています"
    }
  ]
}
```

### 2.8 CSVエクスポート
```
GET /companies/export_csv/
```
**クエリパラメータ**: 企業一覧取得と同様のフィルタ
**レスポンス**: CSVファイル

---

## 3. 役員関連API

### 3.1 役員一覧取得
```
GET /companies/{company_id}/executives/
```

### 3.2 役員作成
```
POST /companies/{company_id}/executives/
```
**リクエスト**
```json
{
  "name": "佐藤花子",
  "position": "取締役",
  "facebook_url": "https://facebook.com/sato",
  "other_sns_url": "https://linkedin.com/in/sato",
  "direct_email": "sato@example.com",
  "notes": "営業担当"
}
```

### 3.3 役員更新
```
PUT /executives/{id}/
PATCH /executives/{id}/
```

### 3.4 役員削除
```
DELETE /executives/{id}/
```

---

## 4. 案件関連API

### 4.1 案件一覧取得
```
GET /projects/
```
**クエリパラメータ**
- `search`: 案件名・依頼企業名検索
- `status`: ステータスフィルタ
- `created_from`: 作成日開始
- `created_to`: 作成日終了

**レスポンス**
```json
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "name": "人材会社向けDM案件",
      "client_company": "株式会社クライアント",
      "description": "人材業界向けの営業DM送信",
      "status": "進行中",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-15T15:30:00Z",
      "company_count": 150
    }
  ]
}
```

### 4.2 案件詳細取得
```
GET /projects/{id}/
```

### 4.3 案件作成
```
POST /projects/
```

### 4.4 案件更新
```
PUT /projects/{id}/
PATCH /projects/{id}/
```

### 4.5 案件削除
```
DELETE /projects/{id}/
```

### 4.6 案件に企業追加
```
POST /projects/{id}/add_companies/
```
**リクエスト**
```json
{
  "company_ids": [1, 2, 3, 4, 5]
}
```

### 4.7 案件企業一覧取得
```
GET /projects/{id}/companies/
```
**レスポンス**
```json
{
  "count": 150,
  "results": [
    {
      "id": 1,
      "company": {
        "id": 1,
        "name": "株式会社サンプル",
        "industry": "IT・ソフトウェア"
      },
      "status": "未接触",
      "contact_date": null,
      "notes": "",
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-10T10:00:00Z"
    }
  ]
}
```

### 4.8 案件企業ステータス更新
```
PATCH /projects/{project_id}/companies/{company_id}/
```
**リクエスト**
```json
{
  "status": "DM送信済み",
  "contact_date": "2025-01-15",
  "notes": "Facebook DMを送信済み"
}
```

### 4.9 案件企業一括ステータス更新
```
POST /projects/{id}/bulk_update_status/
```
**リクエスト**
```json
{
  "company_ids": [1, 2, 3],
  "status": "DM送信済み",
  "contact_date": "2025-01-15"
}
```

### 4.10 案件企業削除
```
DELETE /projects/{project_id}/companies/{company_id}/
```

### 4.11 案件NG企業設定
```
POST /projects/{project_id}/ng_companies/
```
**リクエスト**
```json
{
  "company_id": 1,
  "reason": "クライアントからNG指定"
}
```

### 4.12 案件CSVエクスポート
```
GET /projects/{id}/export_csv/
```

---

## 5. 保存済みフィルタ関連API

### 5.1 保存済みフィルタ一覧取得
```
GET /saved_filters/
```
**レスポンス**
```json
{
  "results": [
    {
      "id": 1,
      "name": "人材会社_2025Q1",
      "filter_conditions": {
        "industry": "人材・派遣",
        "employee_min": 50,
        "has_facebook": true
      },
      "created_at": "2025-01-01T10:00:00Z"
    }
  ]
}
```

### 5.2 フィルタ保存
```
POST /saved_filters/
```
**リクエスト**
```json
{
  "name": "IT企業_大手",
  "filter_conditions": {
    "industry": "IT・ソフトウェア",
    "employee_min": 300,
    "revenue_min": 1000000000
  }
}
```

### 5.3 フィルタ削除
```
DELETE /saved_filters/{id}/
```

---

## 6. マスタデータ関連API

### 6.1 業界一覧取得
```
GET /master/industries/
```
**レスポンス**
```json
[
  "IT・ソフトウェア",
  "製造業",
  "人材・派遣",
  "金融・保険",
  "不動産",
  "その他"
]
```

### 6.2 都道府県一覧取得
```
GET /master/prefectures/
```

### 6.3 ステータス一覧取得
```
GET /master/statuses/
```
**レスポンス**
```json
[
  "未接触",
  "DM送信予定",
  "DM送信済み",
  "返信あり",
  "アポ獲得",
  "成約",
  "NG"
]
```

---

## エラーレスポンス形式

### 4xx クライアントエラー
```json
{
  "error": "validation_error",
  "message": "入力データにエラーがあります",
  "details": {
    "name": ["この項目は必須です"],
    "email": ["正しいメールアドレスを入力してください"]
  }
}
```

### 5xx サーバーエラー
```json
{
  "error": "internal_server_error",
  "message": "サーバー内部エラーが発生しました"
}
```

---

## 共通ヘッダー

### リクエストヘッダー
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

### レスポンスヘッダー
```
Content-Type: application/json
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
```

# API一覧（拡張性考慮版）

## 拡張性について
- **マルチテナント対応**: 全APIにテナントIDを含める設計（現在は単一テナント）
- **外部API連携**: Facebook Graph API、LinkedIn API、メール送信API等の統合を想定
- **バージョニング**: `/api/v1/`形式でAPIバージョン管理
- **権限管理**: 将来的にロールベースアクセス制御（RBAC）を実装予定
- **webhook対応**: 外部システムとの連携用webhook機能を将来追加予定

## 基本設定
- **Base URL**: `https://api.budget-sales.com/api/v1/`
- **認証**: Bearer Token (Supabase JWT)
- **Content-Type**: `application/json`
- **将来対応予定**: 
  - テナントID: `X-Tenant-ID` ヘッダー
  - API Key認証: 外部システム連携用

---

## 7. 将来拡張予定API

### 7.1 マルチテナント対応API（Phase 3）

#### テナント管理
```
GET /admin/tenants/
POST /admin/tenants/
PUT /admin/tenants/{id}/
```

#### テナント切り替え
```
POST /auth/switch_tenant/
```
**リクエスト**
```json
{
  "tenant_id": "tenant_123"
}
```

### 7.2 外部連携API（Phase 2-3）

#### メール送信
```
POST /external/email/send/
```
**リクエスト**
```json
{
  "project_id": 1,
  "company_ids": [1, 2, 3],
  "template_id": 5,
  "scheduled_at": "2025-01-20T10:00:00Z"
}
```

#### Facebook検索
```
POST /external/facebook/search/
```
**リクエスト**
```json
{
  "company_name": "株式会社サンプル",
  "representative_name": "山田太郎"
}
```

#### LinkedIn検索
```
POST /external/linkedin/search/
```

#### 外部CRM同期
```
POST /external/crm/sync/
GET /external/crm/status/{sync_id}/
```

### 7.3 自動化API（Phase 2-4）

#### クローリング設定
```
GET /automation/crawling_configs/
POST /automation/crawling_configs/
```

#### クローリング実行
```
POST /automation/crawling/execute/
GET /automation/crawling/status/{job_id}/
```

#### 自動メッセージ送信
```
POST /automation/message_campaigns/
GET /automation/message_campaigns/{id}/status/
```

### 7.4 分析・レポートAPI（Phase 4）

#### ダッシュボードデータ
```
GET /analytics/dashboard/
```
**レスポンス**
```json
{
  "summary": {
    "total_companies": 25000,
    "active_projects": 15,
    "dm_sent_this_month": 1500,
    "response_rate": 0.12
  },
  "charts": {
    "response_rate_by_industry": [...],
    "monthly_activity": [...]
  }
}
```

#### パフォーマンス分析
```
GET /analytics/performance/
```

#### 成功確率予測
```
POST /ai/predict_success_rate/
```

### 7.5 Webhook API（Phase 3）

#### Webhook設定
```
GET /webhooks/
POST /webhooks/
```
**リクエスト**
```json
{
  "url": "https://client-system.com/webhook",
  "events": ["lead_created", "status_updated"],
  "secret": "webhook_secret_key"
}
```

#### Webhook配信ログ
```
GET /webhooks/{id}/deliveries/
```

---

## 拡張時のデータベース設計

### マルチテナント対応テーブル例
```sql
-- テナントマスタ
tenants (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  domain VARCHAR(255),
  plan_type VARCHAR(50),
  max_users INTEGER,
  max_companies INTEGER,
  features JSONB,
  created_at TIMESTAMP,
  is_active BOOLEAN
);

-- 修正後企業テーブル
companies (
  id SERIAL PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id),
  name VARCHAR(255),
  -- 既存カラム...
  created_at TIMESTAMP
);

-- 外部連携ログ
external_api_logs (
  id SERIAL PRIMARY KEY,
  tenant_id UUID,
  api_type VARCHAR(50), -- 'facebook', 'linkedin', 'email'
  request_data JSONB,
  response_data JSONB,
  status VARCHAR(50),
  created_at TIMESTAMP
);

-- メール送信履歴
email_campaigns (
  id SERIAL PRIMARY KEY,
  tenant_id UUID,
  project_id INTEGER,
  template_id INTEGER,
  sent_count INTEGER,
  delivered_count INTEGER,
  opened_count INTEGER,
  clicked_count INTEGER,
  created_at TIMESTAMP
);

-- Webhook設定
webhooks (
  id SERIAL PRIMARY KEY,
  tenant_id UUID,
  url VARCHAR(500),
  events TEXT[],
  secret VARCHAR(255),
  is_active BOOLEAN,
  created_at TIMESTAMP
);
```

---

## 1. 認証関連API

### 1.1 ログイン
```
POST /auth/login
```
**リクエスト**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**レスポンス**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "山田太郎"
  }
}
```

### 1.2 ログアウト
```
POST /auth/logout
```

### 1.3 トークン更新
```
POST /auth/refresh
```

---

## 2. 企業関連API

### 2.1 企業一覧取得
```
GET /companies/
```
**クエリパラメータ**
- `page`: ページ番号（デフォルト: 1）
- `page_size`: 1ページあたりの件数（デフォルト: 50）
- `search`: 企業名検索
- `industry`: 業界フィルタ
- `employee_min`: 従業員数最小値
- `employee_max`: 従業員数最大値
- `revenue_min`: 売上高最小値
- `revenue_max`: 売上高最大値
- `prefecture`: 都道府県
- `established_year_min`: 設立年最小値
- `established_year_max`: 設立年最大値
- `has_facebook`: Facebook URL有無（true/false）
- `exclude_ng`: NG企業除外（true/false）
- `project_id`: 案件IDによるNG企業除外
- `random_seed`: ランダム表示用シード値

**レスポンス**
```json
{
  "count": 25000,
  "next": "https://api.budget-sales.com/api/v1/companies/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "株式会社サンプル",
      "industry": "IT・ソフトウェア",
      "employee_count": 150,
      "revenue": 500000000,
      "prefecture": "東京都",
      "city": "渋谷区",
      "established_year": 2010,
      "website_url": "https://example.com",
      "contact_email": "info@example.com",
      "phone": "03-1234-5678",
      "notes": "備考",
      "is_global_ng": false,
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-15T15:30:00Z",
      "executives": [
        {
          "id": 1,
          "name": "山田太郎",
          "position": "代表取締役",
          "facebook_url": "https://facebook.com/yamada",
          "other_sns_url": "",
          "direct_email": "yamada@example.com"
        }
      ]
    }
  ]
}
```

### 2.2 企業詳細取得
```
GET /companies/{id}/
```

### 2.3 企業作成
```
POST /companies/
```
**リクエスト**
```json
{
  "name": "株式会社新規企業",
  "industry": "製造業",
  "employee_count": 100,
  "revenue": 300000000,
  "prefecture": "大阪府",
  "city": "大阪市",
  "established_year": 2015,
  "website_url": "https://newcompany.com",
  "contact_email": "info@newcompany.com",
  "phone": "06-1234-5678",
  "notes": "新規登録企業"
}
```

### 2.4 企業更新
```
PUT /companies/{id}/
PATCH /companies/{id}/
```

### 2.5 企業削除
```
DELETE /companies/{id}/
```

### 2.6 企業NG設定切り替え
```
POST /companies/{id}/toggle_ng/
```
**リクエスト**
```json
{
  "reason": "競合他社のため"
}
```

### 2.7 CSVインポート
```
POST /companies/import_csv/
```
**リクエスト（multipart/form-data）**
- `file`: CSVファイル

**レスポンス**
```json
{
  "success": true,
  "imported_count": 150,
  "error_count": 5,
  "errors": [
    {
      "row": 10,
      "message": "企業名が重複しています"
    }
  ]
}
```

### 2.8 CSVエクスポート
```
GET /companies/export_csv/
```
**クエリパラメータ**: 企業一覧取得と同様のフィルタ
**レスポンス**: CSVファイル

---

## 3. 役員関連API

### 3.1 役員一覧取得
```
GET /companies/{company_id}/executives/
```

### 3.2 役員作成
```
POST /companies/{company_id}/executives/
```
**リクエスト**
```json
{
  "name": "佐藤花子",
  "position": "取締役",
  "facebook_url": "https://facebook.com/sato",
  "other_sns_url": "https://linkedin.com/in/sato",
  "direct_email": "sato@example.com",
  "notes": "営業担当"
}
```

### 3.3 役員更新
```
PUT /executives/{id}/
PATCH /executives/{id}/
```

### 3.4 役員削除
```
DELETE /executives/{id}/
```

---

## 4. 案件関連API

### 4.1 案件一覧取得
```
GET /projects/
```
**クエリパラメータ**
- `search`: 案件名・依頼企業名検索
- `status`: ステータスフィルタ
- `created_from`: 作成日開始
- `created_to`: 作成日終了

**レスポンス**
```json
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "name": "人材会社向けDM案件",
      "client_company": "株式会社クライアント",
      "description": "人材業界向けの営業DM送信",
      "status": "進行中",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-15T15:30:00Z",
      "company_count": 150
    }
  ]
}
```

### 4.2 案件詳細取得
```
GET /projects/{id}/
```

### 4.3 案件作成
```
POST /projects/
```

### 4.4 案件更新
```
PUT /projects/{id}/
PATCH /projects/{id}/
```

### 4.5 案件削除
```
DELETE /projects/{id}/
```

### 4.6 案件に企業追加
```
POST /projects/{id}/add_companies/
```
**リクエスト**
```json
{
  "company_ids": [1, 2, 3, 4, 5]
}
```

### 4.7 案件企業一覧取得
```
GET /projects/{id}/companies/
```
**レスポンス**
```json
{
  "count": 150,
  "results": [
    {
      "id": 1,
      "company": {
        "id": 1,
        "name": "株式会社サンプル",
        "industry": "IT・ソフトウェア"
      },
      "status": "未接触",
      "contact_date": null,
      "notes": "",
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-10T10:00:00Z"
    }
  ]
}
```

### 4.8 案件企業ステータス更新
```
PATCH /projects/{project_id}/companies/{company_id}/
```
**リクエスト**
```json
{
  "status": "DM送信済み",
  "contact_date": "2025-01-15",
  "notes": "Facebook DMを送信済み"
}
```

### 4.9 案件企業一括ステータス更新
```
POST /projects/{id}/bulk_update_status/
```
**リクエスト**
```json
{
  "company_ids": [1, 2, 3],
  "status": "DM送信済み",
  "contact_date": "2025-01-15"
}
```

### 4.10 案件企業削除
```
DELETE /projects/{project_id}/companies/{company_id}/
```

### 4.11 案件NG企業設定
```
POST /projects/{project_id}/ng_companies/
```
**リクエスト**
```json
{
  "company_id": 1,
  "reason": "クライアントからNG指定"
}
```

### 4.12 案件CSVエクスポート
```
GET /projects/{id}/export_csv/
```

---

## 5. 保存済みフィルタ関連API

### 5.1 保存済みフィルタ一覧取得
```
GET /saved_filters/
```
**レスポンス**
```json
{
  "results": [
    {
      "id": 1,
      "name": "人材会社_2025Q1",
      "filter_conditions": {
        "industry": "人材・派遣",
        "employee_min": 50,
        "has_facebook": true
      },
      "created_at": "2025-01-01T10:00:00Z"
    }
  ]
}
```

### 5.2 フィルタ保存
```
POST /saved_filters/
```
**リクエスト**
```json
{
  "name": "IT企業_大手",
  "filter_conditions": {
    "industry": "IT・ソフトウェア",
    "employee_min": 300,
    "revenue_min": 1000000000
  }
}
```

### 5.3 フィルタ削除
```
DELETE /saved_filters/{id}/
```

---

## 6. マスタデータ関連API

### 6.1 業界一覧取得
```
GET /master/industries/
```
**レスポンス**
```json
[
  "IT・ソフトウェア",
  "製造業",
  "人材・派遣",
  "金融・保険",
  "不動産",
  "その他"
]
```

### 6.2 都道府県一覧取得
```
GET /master/prefectures/
```

### 6.3 ステータス一覧取得
```
GET /master/statuses/
```
**レスポンス**
```json
[
  "未接触",
  "DM送信予定",
  "DM送信済み",
  "返信あり",
  "アポ獲得",
  "成約",
  "NG"
]
```

---

## エラーレスポンス形式

### 4xx クライアントエラー
```json
{
  "error": "validation_error",
  "message": "入力データにエラーがあります",
  "details": {
    "name": ["この項目は必須です"],
    "email": ["正しいメールアドレスを入力してください"]
  }
}
```

### 5xx サーバーエラー
```json
{
  "error": "internal_server_error",
  "message": "サーバー内部エラーが発生しました"
}
```

---

## 共通ヘッダー

### リクエストヘッダー
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

### レスポンスヘッダー
```
Content-Type: application/json
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
```