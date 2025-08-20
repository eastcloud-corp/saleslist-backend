# 画面とAPI対応表

営業リスト管理システムの各画面で使用するAPIエンドポイントの詳細対応表です。

## 基本情報

- **モックAPI URL**: https://saleslist-mock-api.onrender.com
- **認証方式**: Bearer Token (JWT)
- **データ形式**: JSON

---

## 1. ログイン画面 (`/login`)

### 画面概要
- ユーザー認証を行う画面
- メールアドレス・パスワード入力フォーム

### 使用API

| 操作 | HTTP メソッド | エンドポイント | 説明 | リクエスト例 |
|------|---------------|---------------|------|-------------|
| ログイン | POST | `/auth/login` | ユーザー認証 | `{"email": "user@example.com", "password": "password123"}` |

### APIレスポンス例
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

---

## 2. 企業リスト画面 (`/companies`)

### 画面概要
- 企業データの一覧表示・検索・案件への追加を行うメイン画面
- 検索・フィルタ機能、CSV操作、案件追加機能

### 使用API

| 操作 | HTTP メソッド | エンドポイント | 説明 | 主なパラメータ |
|------|---------------|---------------|------|-------------|
| 企業一覧取得 | GET | `/companies/` | 企業リスト表示 | `page`, `page_size`, `search`, `industry` |
| 企業検索・フィルタ | GET | `/companies/` | 検索条件での絞り込み | `search`, `industry`, `employee_min/max`, `prefecture` |
| ランダム表示 | GET | `/companies/` | 初回ランダム表示 | `random_seed` |
| NG企業除外 | GET | `/companies/` | NG企業を除外した表示 | `exclude_ng=true`, `project_id` |
| 企業NG設定 | POST | `/companies/{id}/toggle_ng/` | 企業のNG設定切り替え | `{"reason": "競合他社のため"}` |
| CSV エクスポート | GET | `/companies/export_csv/` | 検索結果のCSV出力 | 検索条件同様 |
| CSV インポート | POST | `/companies/import_csv/` | 企業データ一括インポート | `multipart/form-data` |
| 案件追加 | POST | `/projects/{id}/add_companies/` | 選択企業を案件に追加 | `{"company_ids": [1,2,3]}` |
| 案件一覧取得 | GET | `/projects/` | 案件選択モーダル用 | - |
| 業界一覧取得 | GET | `/master/industries/` | 業界フィルタ用 | - |
| 都道府県一覧 | GET | `/master/prefectures/` | 都道府県フィルタ用 | - |

### フィルタパラメータ詳細
```javascript
const filterParams = {
  search: "企業名での部分一致検索",
  industry: "IT・ソフトウェア", // 業界フィルタ
  employee_min: 50,           // 従業員数最小値
  employee_max: 500,          // 従業員数最大値
  revenue_min: 100000000,     // 売上高最小値（円）
  revenue_max: 1000000000,    // 売上高最大値（円）
  prefecture: "東京都",        // 都道府県
  established_year_min: 2000, // 設立年最小値
  established_year_max: 2023, // 設立年最大値
  has_facebook: true,         // Facebook URL有無
  exclude_ng: true,           // NG企業除外
  project_id: 1,              // 特定案件のNG企業除外
  page: 1,                    // ページ番号
  page_size: 50               // 1ページあたりの件数
};
```

---

## 3. 企業詳細画面 (`/companies/{id}`)

### 画面概要
- 企業情報の詳細表示・編集
- 代表者・役員情報の管理
- グローバルNG設定

### 使用API

| 操作 | HTTP メソッド | エンドポイント | 説明 | リクエスト例 |
|------|---------------|---------------|------|-------------|
| 企業詳細取得 | GET | `/companies/{id}/` | 企業情報詳細表示 | - |
| 企業情報更新 | PUT | `/companies/{id}/` | 企業情報全体更新 | 企業データオブジェクト |
| 企業部分更新 | PATCH | `/companies/{id}/` | 企業情報部分更新 | 変更フィールドのみ |
| 企業削除 | DELETE | `/companies/{id}/` | 企業削除 | - |
| 役員一覧取得 | GET | `/companies/{id}/executives/` | 役員情報一覧 | - |
| 役員追加 | POST | `/companies/{id}/executives/` | 新規役員追加 | 役員データオブジェクト |
| 役員更新 | PUT | `/executives/{id}/` | 役員情報更新 | 役員データオブジェクト |
| 役員削除 | DELETE | `/executives/{id}/` | 役員削除 | - |
| NG設定切り替え | POST | `/companies/{id}/toggle_ng/` | グローバルNG設定 | `{"reason": "理由"}` |

### データ構造例
```javascript
const companyData = {
  name: "株式会社新規企業",
  industry: "製造業",
  employee_count: 100,
  revenue: 300000000,
  prefecture: "大阪府",
  city: "大阪市",
  established_year: 2015,
  website_url: "https://newcompany.com",
  contact_email: "info@newcompany.com",
  phone: "06-1234-5678",
  notes: "新規登録企業"
};

const executiveData = {
  name: "佐藤花子",
  position: "取締役",
  facebook_url: "https://facebook.com/sato",
  other_sns_url: "https://linkedin.com/in/sato",
  direct_email: "sato@example.com",
  notes: "営業担当"
};
```

---

## 4. 案件管理画面 (`/projects`)

### 画面概要
- 案件の一覧表示・作成・編集
- 案件検索機能

### 使用API

| 操作 | HTTP メソッド | エンドポイント | 説明 | パラメータ |
|------|---------------|---------------|------|----------|
| 案件一覧取得 | GET | `/projects/` | 案件リスト表示 | `search`, `status`, `created_from/to` |
| 案件作成 | POST | `/projects/` | 新規案件作成 | 案件データオブジェクト |
| 案件更新 | PUT | `/projects/{id}/` | 案件情報更新 | 案件データオブジェクト |
| 案件削除 | DELETE | `/projects/{id}/` | 案件削除 | - |

### 案件データ構造例
```javascript
const projectData = {
  name: "IT企業向けDMキャンペーン2025Q1",
  client_company: "株式会社マーケティングプロ",
  description: "IT・ソフトウェア企業向けの新サービス紹介DM送信",
  status: "進行中", // 進行中/完了/中止
  assigned_user: "田中次郎"
};
```

---

## 5. 案件詳細画面 (`/projects/{id}`)

### 画面概要
- 案件に追加された企業の管理
- ステータス更新・一括操作
- 案件NG企業管理

### 使用API

| 操作 | HTTP メソッド | エンドポイント | 説明 | リクエスト例 |
|------|---------------|---------------|------|-------------|
| 案件詳細取得 | GET | `/projects/{id}/` | 案件基本情報 | - |
| 案件企業一覧 | GET | `/projects/{id}/companies/` | 案件の企業リスト | `page`, `page_size` |
| 企業ステータス更新 | PATCH | `/projects/{project_id}/companies/{company_id}/` | 個別ステータス更新 | ステータスデータ |
| 一括ステータス更新 | POST | `/projects/{id}/bulk_update_status/` | 複数企業一括更新 | 企業ID配列+ステータス |
| 案件企業削除 | DELETE | `/projects/{project_id}/companies/{company_id}/` | 案件から企業除外 | - |
| 案件NG企業設定 | POST | `/projects/{project_id}/ng_companies/` | 案件固有NG設定 | NG企業データ |
| 案件CSV出力 | GET | `/projects/{id}/export_csv/` | 案件データCSV出力 | - |
| ステータス一覧 | GET | `/master/statuses/` | ステータス選択肢取得 | - |

### ステータス更新データ例
```javascript
// 個別更新
const statusUpdate = {
  status: "DM送信済み",
  contact_date: "2025-01-15",
  notes: "Facebook DMを送信済み"
};

// 一括更新
const bulkUpdate = {
  company_ids: [1, 2, 3],
  status: "DM送信済み",
  contact_date: "2025-01-15"
};
```

---

## 6. 保存済みフィルタ機能

### 概要
- 検索条件の保存・呼び出し機能（企業リスト画面で使用）

### 使用API

| 操作 | HTTP メソッド | エンドポイント | 説明 |
|------|---------------|---------------|------|
| フィルタ一覧取得 | GET | `/saved_filters/` | 保存済みフィルタ一覧 |
| フィルタ保存 | POST | `/saved_filters/` | 現在の検索条件を保存 |
| フィルタ削除 | DELETE | `/saved_filters/{id}/` | 保存済みフィルタ削除 |

### 保存フィルタデータ例
```javascript
const savedFilter = {
  name: "IT企業_大手",
  filter_conditions: {
    industry: "IT・ソフトウェア",
    employee_min: 300,
    revenue_min: 1000000000
  }
};
```

---

## エラーハンドリング

### 共通エラーレスポンス

#### 4xx クライアントエラー
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

#### 401 認証エラー
```json
{
  "error": "unauthorized",
  "message": "認証が必要です"
}
```

#### 404 リソース未発見
```json
{
  "error": "not_found",
  "message": "指定されたリソースが見つかりません"
}
```

---

## 認証・セキュリティ

### リクエストヘッダー
```javascript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
};
```

### トークン更新
```javascript
// アクセストークン期限切れ時の処理
POST /auth/refresh
{
  "refresh_token": "refresh_token_here"
}
```

---

## ページネーション

### 共通パラメータ
- `page`: ページ番号（デフォルト: 1）
- `page_size`: 1ページあたりの件数（デフォルト: 50、選択肢: 50/100/200）

### レスポンス形式
```json
{
  "count": 25000,
  "next": "https://api.budget-sales.com/api/v1/companies/?page=2",
  "previous": null,
  "results": [...] // データ配列
}
```