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
| | `/clients/{id}/ng-companies/add` | POST | 企業検索からNG追加 |
| | `/clients/{id}/ng-companies/import` | POST | CSVインポート |
| | `/clients/{id}/ng-companies/{ng_id}` | DELETE | NG削除 |

#### NGリスト機能強化（実装済み）
- **企業検索機能**: 企業管理データから企業名検索してNG追加
- **CSVインポート**: 従来通りのCSV一括インポート機能
- **UI改善**: 企業検索セクションとCSVインポートボタン（右上配置）の併存
| 案件一覧 | `/projects?client_id={id}` | GET | 関連案件取得 |
| | `/projects` | POST | 新規案件作成 |

### 案件作成・更新
```typescript
// POST /projects (作成)
Body: {
  name: string           // 必須
  client_id: number      // 必須
  client_company?: string
  description?: string
  status?: 'active' | '進行中' | '完了' | '中止'
  assigned_user?: string
}

// PUT /projects/{id} (更新)
Body: {
  name: string           // 必須
  client_id: number      // 必須
  client_company?: string
  description?: string
  status?: 'active' | '進行中' | '完了' | '中止'
  assigned_user?: string
}

// PATCH /projects/{id} (部分更新)
Body: {
  name?: string
  client_id?: number
  client_company?: string
  description?: string
  status?: 'active' | 'completed' | '進行中' | '完了' | '中止'
  assigned_user?: string
}
```

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

// POST /clients/{id}/ng-companies/add (企業検索からNG追加)
Body: {
  company_id: number      // 必須 - 企業管理データのID
  company_name: string    // 必須 - 企業名
  reason: string          // 必須 - NG理由
}
Response: {
  id: number
  company_id?: number
  company_name: string
  reason: string
  matched: boolean        // 企業管理データとマッチしたかどうか
  created_at: string
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

### 案件詳細情報
```typescript
// GET /projects/{id}
Response: {
  id: number
  client_id: number  // クライアントID
  name: string
  client_company: string
  description: string
  status: '進行中' | '完了' | '中止'
  start_date: string  // 開始日
  end_date: string    // 終了日
  created_at: string
  updated_at: string
  company_count: number      // 登録企業数
  contacted_count: number    // 接触済み企業数
  success_count: number      // 成約数
  assigned_user: string
  companies: Array<{      // 案件に紐づく企業リスト
    id: number
    company: {
      id: number
      name: string
      industry: string
    }
    status: string
    contact_date: string | null
    notes: string
    created_at: string
    updated_at: string
  }>
}
```

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
  is_active?: boolean        // 論理削除・有効化
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

## 7. 営業先企業詳細画面（/projects/{project_id}/companies/{company_id}）

### 画面仕様
- **役割**: 案件における企業の営業進捗詳細管理
- **コンテキスト**: 特定の案件での企業との営業活動記録
- **表示項目**: 企業基本情報、営業履歴、ステータス変更、次回アクション

### 使用API

| 機能 | エンドポイント | メソッド | 用途 |
|-----|-------------|---------|-----|
| 基本情報 | `/companies/{company_id}` | GET | 企業基本情報取得 |
| 営業情報 | `/projects/{project_id}/companies/{company_id}` | GET | 案件での営業情報取得 |
| ステータス更新 | `/projects/{project_id}/companies/{company_id}` | PATCH | 営業ステータス更新 |
| 営業履歴 | `/projects/{project_id}/companies/{company_id}/history` | GET | 営業履歴一覧取得 |
| 履歴追加 | `/projects/{project_id}/companies/{company_id}/history` | POST | 営業履歴記録追加 |
| 履歴編集 | `/projects/{project_id}/companies/{company_id}/history/{history_id}` | PUT | 営業履歴更新 |
| 履歴削除 | `/projects/{project_id}/companies/{company_id}/history/{history_id}` | DELETE | 営業履歴削除 |

### リクエスト/レスポンス
```typescript
// GET /projects/{project_id}/companies/{company_id}
Response: {
  id: number
  project_id: number
  company_id: number
  company: Company              // 企業基本情報
  status: string               // 現在の営業ステータス
  contact_date?: string        // 最終接触日
  next_action?: string         // 次回アクション
  notes?: string              // 案件メモ
  staff_id?: number           // 担当者ID
  staff_name?: string         // 担当者名
  added_at: string            // 案件追加日
  updated_at: string          // 最終更新日
}

// GET /projects/{project_id}/companies/{company_id}/history
Response: {
  count: number
  results: Array<{
    id: number
    status: string            // 営業ステータス
    status_date: string       // ステータス日付
    staff_name?: string       // 担当者
    notes?: string           // 履歴メモ
    created_at: string       // 記録日時
  }>
}

// POST /projects/{project_id}/companies/{company_id}/history
Body: {
  status: string             // 必須 - 新ステータス
  status_date: string        // 必須 - ステータス日付
  staff_name?: string        // 担当者名
  notes?: string            // 履歴メモ
}

// PUT /projects/{project_id}/companies/{company_id}/history/{history_id}
Body: {
  status?: string           // ステータス更新
  status_date?: string      // 日付更新
  staff_name?: string       // 担当者更新
  notes?: string           // メモ更新
}

// DELETE /projects/{project_id}/companies/{company_id}/history/{history_id}
Response: 204 No Content
}
```

## 8. フィルタ保存機能

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

## 10. 設定画面（/settings）

### 画面仕様
- **役割**: ユーザー管理、システム設定
- **表示項目**: ユーザー一覧、権限管理、システム設定タブ
- **主要機能**: ユーザー作成、権限変更、設定変更

### 使用API

| タブ | エンドポイント | メソッド | 用途 |
|-----|-------------|---------|-----|
| ユーザー管理 | `/auth/users/` | GET | ユーザー一覧取得 |
| | `/auth/users/create/` | POST | 新規ユーザー作成 |
| | `/auth/users/{id}/` | PATCH | ユーザー情報更新・無効化 |
| 全タブ | `/auth/me` | GET | 現在ユーザー情報 |

### リクエスト/レスポンス
```typescript
// GET /auth/users/
Response: {
  count: number
  results: User[]
}

// POST /auth/users/create/
Body: {
  name: string           // 必須
  email: string          // 必須
  role: "admin" | "user" // 必須
  password: string       // 必須
}

Response: {
  id: number
  name: string
  email: string
  role: "admin" | "user"
  is_active: boolean
  created_at: string
  updated_at: string
}

// PATCH /auth/users/{id}/ (ユーザー情報更新・無効化)
Body: {
  name?: string              // 名前更新
  email?: string             // メールアドレス更新
  role?: "admin" | "user" | "viewer"  // 権限変更
  is_active?: boolean        // アクティブ状態変更（無効化）
}

Response: {
  id: number
  name: string
  email: string
  role: "admin" | "user" | "viewer"
  is_active: boolean
  created_at: string
  updated_at: string
}

#### 実装済み機能強化まとめ

##### NGリスト管理強化
- **企業検索機能**: 企業管理データから企業名検索してNG追加
- **CSVインポート**: 従来通りのCSV一括インポート機能  
- **UI改善**: 企業検索セクションとCSVインポートボタン（右上配置）の併存

##### ユーザー管理機能強化
- **ユーザー状態切り替え**: Switchコンポーネントでワンクリック有効化・無効化
- **画面自動更新**: ユーザー作成・更新後の自動リフレッシュ機能
- **双方向切り替え**: 無効化したユーザーの再有効化機能

##### UI/UX改善
- **案件カードレイアウト統一**: 高さ320px固定、ボタン位置統一
- **ProjectCompanies統合**: 重複コンポーネント削除、インラインステータス編集
- **NG企業表示改善**: API連携でリアルタイムNG情報表示・グレーアウト

##### 営業先企業詳細機能
- **案件コンテキスト**: プロジェクトID + 企業IDでの個別管理
- **営業履歴管理**: ステータス変更履歴の記録・表示・追加機能
- **URL構造**: `/projects/{project_id}/companies/{company_id}` で案件ごと管理
```