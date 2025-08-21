# クライアント・NGリスト管理統合仕様書

## 概要
クライアント企業の営業代行依頼を管理し、NGリストによる企業フィルタリングを実現する統合機能仕様。
クライアントを起点とした業務フローに基づき、効率的な営業活動を支援する。

## 業務フロー

### クライアント中心のフロー
```
1. クライアントから営業代行依頼
   ↓
2. クライアント情報とNGリストを登録
   ↓
3. クライアント詳細画面から営業対象企業を選択
   （NG企業は自動的に選択不可）
   ↓
4. 案件詳細画面で営業進捗を管理
```

## データモデル

### 1. クライアントテーブル (clients)
```sql
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    company_type VARCHAR(50),
    industry VARCHAR(100),
    contact_person VARCHAR(100),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    address TEXT,
    website VARCHAR(255),
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2. クライアントNGリストテーブル (client_ng_companies)
```sql
CREATE TABLE client_ng_companies (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    company_id INTEGER REFERENCES companies(id),
    matched BOOLEAN DEFAULT FALSE,
    reason TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_client_ng_client_id (client_id),
    INDEX idx_client_ng_company_name (company_name),
    UNIQUE(client_id, company_name)
);
```

### 3. NGインポート履歴テーブル (ng_import_logs)
```sql
CREATE TABLE ng_import_logs (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    project_id INTEGER REFERENCES projects(id),
    file_name VARCHAR(255),
    imported_count INTEGER,
    matched_count INTEGER,
    unmatched_count INTEGER,
    imported_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## 画面仕様

### 1. クライアント一覧画面（/clients）- スタート画面
- **機能**: クライアント企業の一覧表示と管理
- **主要項目**:
  - クライアント名、担当者、進行中案件数、登録企業数
  - 新規クライアント追加ボタン
  - 詳細画面への遷移

### 2. クライアント詳細画面（/clients/{id}）
- **タブ構成**:
  - 基本情報タブ: クライアント情報の表示・編集
  - NGリストタブ: NGリスト管理機能
  - 案件一覧タブ: 関連案件の表示
- **主要機能**:
  - 「営業対象企業を選択」ボタン
  - NGリストCSVインポート
  - 案件作成

### 3. 企業選択画面（/clients/{id}/select-companies）
- **機能**: クライアント用の企業選択
- **特徴**:
  - 企業マスタから選択
  - NG企業は自動的にグレーアウト表示
  - NGバッジとツールチップで理由表示
  - 複数選択して案件に追加

### 4. NGリスト管理タブ詳細

#### インポート機能
```typescript
// CSVインポート処理
async function importNGList(clientId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch(`/api/clients/${clientId}/ng-companies/import`, {
    method: 'POST',
    body: formData
  })
  
  return response.json()
}
```

#### NGリスト表示
- マッチ済み/未マッチの可視化
- 一括削除・個別削除機能
- 検索・フィルタリング機能

## API仕様

### クライアント管理API

```typescript
// クライアント一覧取得
GET /clients
Query params:
  - search?: string
  - is_active?: boolean
  - page?: number
  - limit?: number

// クライアント詳細取得
GET /clients/{id}

// クライアント作成
POST /clients
Body: {
  name: string
  company_type?: string
  industry?: string
  contact_person?: string
  contact_email?: string
  contact_phone?: string
  address?: string
  website?: string
  notes?: string
}

// クライアント更新
PUT /clients/{id}

// クライアント削除
DELETE /clients/{id}
```

### NGリスト管理API

```typescript
// クライアントNGリスト取得
GET /clients/{id}/ng-companies
Response: {
  count: number
  matched_count: number
  unmatched_count: number
  results: ClientNGCompany[]
}

// NGリストCSVインポート
POST /clients/{id}/ng-companies/import
Body: FormData (CSV file)
Response: {
  imported_count: number
  matched_count: number
  unmatched_count: number
  errors: string[]
}

// NG企業削除
DELETE /clients/{id}/ng-companies/{ng_id}

// NGテンプレートダウンロード
GET /ng-companies/template
Response: CSV file
```

### 企業選択API（クライアント用）

```typescript
// クライアント用企業一覧（NG判定付き）
GET /clients/{client_id}/available-companies
Query params:
  - search?: string
  - industry?: string
  - prefecture?: string
  - employee_min?: number
  - employee_max?: number
  - exclude_ng?: boolean
  - page?: number
  - limit?: number

Response: {
  count: number
  results: Array<{
    ...Company,
    ng_status: {
      is_ng: boolean
      type: 'global' | 'client' | 'project' | null
      reason: string | null
    }
  }>
}

// 選択企業を案件に追加
POST /projects/{project_id}/add-companies
Body: {
  company_ids: number[]
}
```

## NG判定ロジック

```javascript
function isNGCompany(company, context) {
  // 1. グローバルNG
  if (company.is_global_ng) {
    return { 
      is_ng: true, 
      type: 'global', 
      reason: company.ng_reason 
    }
  }
  
  // 2. クライアントNG
  if (context.client_id) {
    const clientNG = checkClientNG(company.id, company.name, context.client_id)
    if (clientNG) {
      return { 
        is_ng: true, 
        type: 'client', 
        reason: clientNG.reason 
      }
    }
  }
  
  // 3. 案件固有NG
  if (context.project_id) {
    const projectNG = checkProjectNG(company.id, context.project_id)
    if (projectNG) {
      return { 
        is_ng: true, 
        type: 'project', 
        reason: projectNG.reason 
      }
    }
  }
  
  return { is_ng: false }
}
```

## CSVフォーマット

### NGリストCSVテンプレート
```csv
企業名,理由
株式会社ABC,競合他社
○○コーポレーション,既存取引先
△△商事,クライアント指定NG
```

### インポート処理の要件
1. **企業名マッチング**
   - 完全一致を優先
   - 部分一致で候補表示
   - 法人格の表記揺れ対応（株式会社/（株）など）

2. **重複チェック**
   - 同一クライアント内での重複を防止
   - 既存NGとの重複は更新

3. **バリデーション**
   - 企業名必須
   - 文字数制限（255文字）
   - 不正な文字のサニタイズ

## UI/UXコンポーネント

### NGリスト管理コンポーネント
```tsx
export function NGListTab({ clientId }: { clientId: number }) {
  const [ngList, setNgList] = useState<ClientNGCompany[]>([])
  const [isImporting, setIsImporting] = useState(false)
  
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    
    setIsImporting(true)
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      const response = await fetch(`/api/clients/${clientId}/ng-companies/import`, {
        method: 'POST',
        body: formData,
      })
      
      const result = await response.json()
      
      toast({
        title: 'インポート完了',
        description: `${result.imported_count}件のNGリストを登録しました`,
      })
      
      fetchNGList()
    } catch (error) {
      toast({
        title: 'エラー',
        description: 'インポートに失敗しました',
        variant: 'destructive',
      })
    } finally {
      setIsImporting(false)
    }
  }
  
  return (
    <div className="space-y-4">
      {/* インポートセクション */}
      <Card>
        <CardHeader>
          <CardTitle>NGリストインポート</CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            type="file"
            accept=".csv"
            onChange={handleFileUpload}
            disabled={isImporting}
          />
        </CardContent>
      </Card>
      
      {/* NGリスト一覧 */}
      <NGListTable ngList={ngList} onDelete={handleDelete} />
    </div>
  )
}
```

### 企業選択時のNG表示
```tsx
function CompanyRow({ company, clientId }: Props) {
  const ngStatus = company.ng_status
  
  return (
    <TableRow className={ngStatus?.is_ng ? 'bg-red-50' : ''}>
      <TableCell>
        <Checkbox 
          disabled={ngStatus?.is_ng}
          // ... checkbox props
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {company.name}
          {ngStatus?.is_ng && (
            <Tooltip>
              <TooltipTrigger>
                <Badge variant="destructive">NG</Badge>
              </TooltipTrigger>
              <TooltipContent>
                {ngStatus.reason}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </TableCell>
    </TableRow>
  )
}
```

## 実装優先度

### Phase 1（必須）
- クライアント一覧・詳細画面
- NGリストCSVインポート機能
- 企業選択時のNG除外表示

### Phase 2（推奨）
- NGリスト手動編集機能
- インポート履歴表示
- 高度なマッチングロジック

### Phase 3（将来）
- AIによる企業名マッチング
- NGリスト共有機能
- 定期的な自動マッチング

## セキュリティ・パフォーマンス

- CSVファイルサイズ制限（10MB）
- CSVインジェクション対策
- アップロードファイルのウイルススキャン
- NGリストへのアクセス権限管理
- 大量データ（1000件以上）のページネーション処理