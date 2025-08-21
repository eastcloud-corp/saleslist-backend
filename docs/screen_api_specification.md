# 画面・API統合仕様書

## 概要
クライアント中心のビジネスフローに基づく画面とAPIエンドポイントの統合仕様。
スタート画面をクライアント一覧とし、企業リストはマスタデータとして扱う。

## 画面フロー

```
/clients（クライアント一覧）※スタート画面
    ↓
/clients/{id}（クライアント詳細）
    ├── 基本情報タブ
    ├── NGリストタブ
    ├── 案件一覧タブ
    └── 「営業対象企業を選択」ボタン
            ↓
/clients/{id}/select-companies（企業選択画面）
    - NG企業は選択不可（グレーアウト）
            ↓
/projects/{id}（案件詳細・営業進捗管理）
```

## 1. クライアント一覧画面（/clients）

### 画面仕様
- **役割**: スタート画面、クライアント管理の中心
- **表示項目**: クライアント名、担当者、進行中案件数、登録企業数、アクション

### 使用API

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/clients` | GET | クライアント一覧取得 |
| `/clients` | POST | 新規クライアント作成 |

### リクエスト/レスポンス
```typescript
// GET /clients
Query params: {
  search?: string
  is_active?: boolean
  page?: number
  limit?: number
}

Response: {
  count: number
  results: Client[]
}
```

## 2. クライアント詳細画面（/clients/{id}）

### 画面仕様
- **タブ構成**: 基本情報、NGリスト、案件一覧
- **主要機能**: 営業対象企業選択、NGリストインポート、案件作成

### 使用API

| タブ | エンドポイント | メソッド | 用途 |
|-----|-------------|---------|-----|
| 基本情報 | `/clients/{id}` | GET | クライアント詳細取得 |
| | `/clients/{id}` | PUT | クライアント情報更新 |
| NGリスト | `/clients/{id}/ng-companies` | GET | NGリスト取得 |
| | `/clients/{id}/ng-companies/import` | POST | CSVインポート |
| | `/clients/{id}/ng-companies/{ng_id}` | DELETE | NG削除 |
| 案件一覧 | `/projects?client_id={id}` | GET | 関連案件取得 |
| | `/projects` | POST | 新規案件作成 |

### NGリストタブ詳細
```typescript
// GET /clients/{id}/ng-companies
Response: {
  count: number
  matched_count: number
  unmatched_count: number
  results: Array<{
    id: number
    client_id: number
    company_name: string
    company_id?: number
    matched: boolean
    reason?: string
    is_active: boolean
    created_at: string
    updated_at: string
  }>
}

// POST /clients/{id}/ng-companies
Body: {
  company_name: string
  reason?: string
}

// POST /clients/{id}/ng-companies/import
Body: FormData (CSV file) or JSON { csv_data: string }
Response: {
  imported_count: number
  matched_count: number
  unmatched_count: number
  errors?: string[]
}

// GET /ng-companies/template
Response: string (CSV template)

// POST /ng-companies/match
Body: {
  client_id?: number
  project_id?: number
}
Response: {
  matched_count: number
  updated_companies: Company[]
}
```

## 3. 企業選択画面（/clients/{id}/select-companies）

### 画面仕様
- **機能**: クライアント用の営業対象企業選択
- **特徴**: NG企業の自動グレーアウト、複数選択可能

### 使用API

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/clients/{id}/available-companies` | GET | NG判定付き企業一覧 |
| `/projects/{project_id}/add-companies` | POST | 選択企業を案件に追加 |

### リクエスト/レスポンス
```typescript
// GET /clients/{id}/available-companies
Query params: {
  search?: string
  industry?: string
  prefecture?: string
  employee_min?: number
  employee_max?: number
  exclude_ng?: boolean
  page?: number
  limit?: number
}

Response: {
  count: number
  results: Array<{
    id: number
    name: string
    industry: string
    prefecture: string
    employee_count: string
    // NG判定情報
    ng_status: {
      is_ng: boolean
      type: 'global' | 'client' | 'project' | null
      reason: string | null
    }
  }>
}

// POST /projects/{project_id}/add-companies
Body: {
  company_ids: number[]
}
Response: {
  added_count: number
  companies: ProjectCompany[]
}
```

## 4. 企業選択画面（/projects/{id}/add-companies）

### 画面仕様
- **役割**: 案件に企業を追加する選択画面
- **特徴**: NG企業と追加済み企業の自動判定・表示

### 使用API

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/projects/{id}/available-companies` | GET | 追加可能企業一覧取得 |
| `/projects/{id}/add-companies` | POST | 選択企業を案件に追加 |

### リクエスト/レスポンス
```typescript
// GET /projects/{id}/available-companies
Query params: {
  search?: string
  industry?: string
  page?: number
  limit?: number
}

Response: {
  count: number
  results: Array<{
    id: number
    name: string
    industry: string
    prefecture: string
    employee_count: string
    ng_status: {
      is_ng: boolean
      type: 'global' | 'client' | 'project' | null
      reason: string | null
    }
    in_project: boolean  // 追加済みフラグ
  }>
}

// POST /projects/{id}/add-companies
Body: {
  company_ids: number[]
}
Response: {
  added_count: number
  companies: ProjectCompany[]
}
```

## 5. 案件詳細画面（/projects/{id}）

### 画面仕様
- **タブ構成**: 営業進捗、統計、活動履歴
- **主要機能**: ステータス更新、活動記録、企業追加

### 使用API

| タブ | エンドポイント | メソッド | 用途 |
|-----|-------------|---------|-----|
| 基本情報 | `/projects/{id}` | GET | 案件詳細取得 |
| | `/projects/{id}` | PUT | 案件情報更新 |
| 営業進捗 | `/projects/{id}/companies` | GET | 案件企業一覧 |
| | `/projects/{id}/companies/{company_id}` | PATCH | ステータス更新 |
| | `/projects/{id}/add-companies` | POST | 企業追加 |
| | `/projects/{id}/companies/{company_id}` | DELETE | 企業削除 |
| 統計 | `/projects/{id}/stats` | GET | 統計情報取得 |
| 活動履歴 | `/projects/{id}/activities` | GET | 活動履歴取得 |
| | `/projects/{id}/activities` | POST | 活動記録追加 |

### 営業進捗管理
```typescript
// GET /projects/{id}/companies
Response: {
  count: number
  results: Array<{
    id: number
    project_id: number
    company_id: number
    company: Company
    status: '未接触' | 'DM送信済み' | '返信あり' | 'アポ獲得' | '成約' | 'NG'
    contact_date?: string
    next_action?: string
    notes?: string
    staff_id?: number
    staff_name?: string
  }>
}

// PATCH /projects/{id}/companies/{company_id}
Body: {
  status?: string
  contact_date?: string
  next_action?: string
  notes?: string
  staff_id?: number
}

// POST /projects/{id}/bulk_update_status
Body: {
  company_ids: number[]
  status: string
  contact_date?: string
}
Response: {
  updated_count: number
  message: string
}

// POST /projects/{project_id}/ng_companies
Body: {
  company_id: number
  reason?: string
}

// GET /projects/{id}/export_csv
Response: string (CSV data)
```

## 6. 企業マスタ管理画面（/companies）※管理画面

### 画面仕様
- **役割**: マスタデータのメンテナンス
- **機能**: 企業情報の一括管理、CSVインポート/エクスポート、NG切替

### 使用API

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/companies` | GET | 企業一覧取得 |
| `/companies` | POST | 新規企業登録 |
| `/companies/{id}` | GET | 企業詳細取得 |
| `/companies/{id}` | PUT | 企業情報更新 |
| `/companies/{id}` | PATCH | 企業情報部分更新 |
| `/companies/{id}` | DELETE | 企業削除 |
| `/companies/{id}/toggle_ng` | POST | グローバルNG切替 |
| `/companies/import_csv` | POST | CSVインポート |
| `/companies/export_csv` | GET | CSVエクスポート |
| `/companies/{company_id}/executives` | GET | 役員一覧取得 |
| `/companies/{company_id}/executives` | POST | 役員登録 |

### リクエスト/レスポンス
```typescript
// GET /companies
Query params: {
  search?: string
  industry?: string
  prefecture?: string
  city?: string
  employee_min?: number
  employee_max?: number
  is_listed?: boolean
  page?: number
  limit?: number
}

Response: {
  count: number
  results: Company[]
}
```

## 7. フィルタ保存機能

### 画面仕様
- **機能**: 検索条件の保存・再利用
- **用途**: 企業一覧画面、企業選択画面での絞り込み条件保存

### 使用API

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/saved_filters` | GET | 保存済みフィルタ一覧 |
| `/saved_filters` | POST | フィルタ保存 |
| `/saved_filters/{id}` | DELETE | フィルタ削除 |

### リクエスト/レスポンス
```typescript
// POST /saved_filters
Body: {
  name: string
  filters?: object  // フィルタ条件（任意形式）
  filter_conditions?: object  // 旧形式との互換性
}

// GET /saved_filters
Response: {
  results: Array<{
    id: number
    name: string
    filter_conditions: object
    created_at: string
  }>
}
```

## 8. 役員管理機能

### 使用API

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/executives/{id}` | PUT | 役員情報更新 |
| `/executives/{id}` | PATCH | 役員情報部分更新 |
| `/executives/{id}` | DELETE | 役員削除 |

## 9. マスターデータAPI

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/master/industries` | GET | 業種一覧 |
| `/master/prefectures` | GET | 都道府県一覧 |
| `/master/statuses` | GET | ステータス一覧 |

## 10. 管理画面（/admin）※Phase 2

### 画面仕様
- **機能**: システム設定、ユーザー管理、マスタデータ管理

### 使用API

| 機能 | エンドポイント | メソッド | 用途 |
|-----|-------------|---------|-----|
| ユーザー管理 | `/users` | GET | ユーザー一覧 |
| | `/users` | POST | ユーザー作成 |
| | `/users/{id}` | PUT | ユーザー更新 |
| | `/users/{id}` | DELETE | ユーザー削除 |
| システム設定 | `/settings` | GET | 設定取得 |
| | `/settings` | PUT | 設定更新 |

## 認証API

| エンドポイント | メソッド | 用途 |
|-------------|---------|-----|
| `/auth/login` | POST | ログイン |
| `/auth/logout` | POST | ログアウト |
| `/auth/refresh` | POST | トークンリフレッシュ |
| `/auth/me` | GET | 現在のユーザー情報 |

### 認証フロー
```typescript
// POST /auth/login
Body: {
  email: string
  password: string
}
Response: {
  access_token: string
  refresh_token: string
  user: User
}

// POST /auth/refresh
Headers: {
  Authorization: 'Bearer {refresh_token}'
}
Response: {
  access_token: string
  refresh_token: string
}
```

## エラーレスポンス

すべてのAPIは以下の形式でエラーを返す：

```typescript
{
  error: {
    code: string
    message: string
    details?: any
  }
}
```

### HTTPステータスコード

| コード | 意味 | 使用場面 |
|-------|-----|---------|
| 200 | OK | 正常な取得・更新 |
| 201 | Created | リソース作成成功 |
| 204 | No Content | 削除成功 |
| 400 | Bad Request | バリデーションエラー |
| 401 | Unauthorized | 認証エラー |
| 403 | Forbidden | 権限エラー |
| 404 | Not Found | リソース不在 |
| 409 | Conflict | 重複エラー |
| 500 | Internal Server Error | サーバーエラー |

## ページネーション

リスト系APIは共通のページネーション形式を使用：

```typescript
// Request
Query params: {
  page?: number    // デフォルト: 1
  limit?: number   // デフォルト: 20、最大: 100
}

// Response
{
  count: number      // 総件数
  next: string | null    // 次ページURL
  previous: string | null // 前ページURL
  results: T[]       // データ配列
}
```

## リアルタイム更新（将来実装）

WebSocketを使用したリアルタイム更新：

```typescript
// WebSocket接続
ws://api.example.com/ws

// イベント形式
{
  type: 'project.updated' | 'company.status_changed' | 'ng_list.imported'
  data: any
}
```