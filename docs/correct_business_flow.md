# 正しい業務フローと画面設計

## 業務フロー

### 1️⃣ クライアントから営業代行依頼
```
クライアント企業
    ↓ 
「この企業リストに営業してください」
「ただし、このNG企業リストは除外してください」
    ↓
バジェットアドテクノロジー
```

### 2️⃣ システムへの登録
```
1. クライアント情報登録
2. NGリスト登録（CSV一括）
3. 案件作成
```

### 3️⃣ 営業対象企業の選択
```
クライアント詳細画面
    ↓
「営業対象企業を選択」ボタン
    ↓
企業選択画面（NG企業は選択不可）
    ↓
選択した企業を案件に追加
```

### 4️⃣ 営業進捗管理
```
案件詳細画面
    ↓
営業ステータス管理
（未接触 → DM送信済み → 返信あり → アポ獲得 → 成約）
```

## 画面構成（修正版）

### メイン画面フロー
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
    - 企業マスタから選択
    - NG企業は選択不可（グレーアウト）
    - 選択した企業を案件に追加
            ↓
/projects/{id}（案件詳細・営業進捗管理）
    - 選択した企業の一覧
    - 各企業の営業ステータス管理
```

### 管理画面（マスタメンテナンス）
```
/companies（企業マスタ管理）
    - 全企業データの管理
    - CSVインポート/エクスポート
    - グローバルNG設定

/settings（システム設定）
    - ユーザー管理
    - マスタデータ管理
```

## 画面詳細

### 1. クライアント一覧（/clients）- スタート画面
```tsx
function ClientListPage() {
  return (
    <div>
      <PageHeader>
        <h1>クライアント一覧</h1>
        <Button>+ 新規クライアント</Button>
      </PageHeader>
      
      <Table>
        <TableRow>
          <TableCell>クライアント名</TableCell>
          <TableCell>担当者</TableCell>
          <TableCell>進行中案件</TableCell>
          <TableCell>登録企業数</TableCell>
          <TableCell>アクション</TableCell>
        </TableRow>
        {clients.map(client => (
          <TableRow>
            <TableCell>{client.name}</TableCell>
            <TableCell>{client.contact_person}</TableCell>
            <TableCell>{client.active_projects}</TableCell>
            <TableCell>{client.total_companies}</TableCell>
            <TableCell>
              <Button onClick={() => navigate(`/clients/${client.id}`)}>
                詳細
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </Table>
    </div>
  )
}
```

### 2. クライアント詳細（/clients/{id}）
```tsx
function ClientDetailPage() {
  return (
    <div>
      <PageHeader>
        <h1>{client.name}</h1>
        <Button onClick={() => navigate(`/clients/${id}/select-companies`)}>
          営業対象企業を選択
        </Button>
      </PageHeader>
      
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">概要</TabsTrigger>
          <TabsTrigger value="ng-list">NGリスト</TabsTrigger>
          <TabsTrigger value="projects">案件一覧</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview">
          {/* クライアント基本情報 */}
        </TabsContent>
        
        <TabsContent value="ng-list">
          <NGListManager clientId={id} />
          {/* CSVインポート、NGリスト管理 */}
        </TabsContent>
        
        <TabsContent value="projects">
          <ProjectList clientId={id} />
          {/* このクライアントの案件一覧 */}
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

### 3. 企業選択画面（/clients/{id}/select-companies）
```tsx
function CompanySelectionPage({ clientId }) {
  const [selectedCompanies, setSelectedCompanies] = useState([])
  const ngList = useNGList(clientId) // このクライアントのNGリスト
  
  return (
    <div>
      <PageHeader>
        <h1>営業対象企業を選択</h1>
        <div className="flex gap-2">
          <Badge>選択中: {selectedCompanies.length}社</Badge>
          <Button 
            onClick={handleAddToProject}
            disabled={selectedCompanies.length === 0}
          >
            案件に追加
          </Button>
        </div>
      </PageHeader>
      
      <Filters>
        {/* 業界、地域、規模などでフィルタ */}
      </Filters>
      
      <Table>
        {companies.map(company => {
          const isNG = checkIfNG(company, ngList)
          return (
            <TableRow key={company.id} className={isNG ? 'opacity-50' : ''}>
              <TableCell>
                <Checkbox 
                  disabled={isNG}
                  checked={selectedCompanies.includes(company.id)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedCompanies([...selectedCompanies, company.id])
                    } else {
                      setSelectedCompanies(selectedCompanies.filter(id => id !== company.id))
                    }
                  }}
                />
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  {company.name}
                  {isNG && (
                    <Tooltip>
                      <TooltipTrigger>
                        <Badge variant="destructive">NG</Badge>
                      </TooltipTrigger>
                      <TooltipContent>
                        {isNG.reason}
                      </TooltipContent>
                    </Tooltip>
                  )}
                </div>
              </TableCell>
              <TableCell>{company.industry}</TableCell>
              <TableCell>{company.employee_count}</TableCell>
              <TableCell>{company.prefecture}</TableCell>
            </TableRow>
          )
        })}
      </Table>
    </div>
  )
}
```

### 4. 案件詳細・営業進捗管理（/projects/{id}）
```tsx
function ProjectDetailPage({ projectId }) {
  return (
    <div>
      <PageHeader>
        <h1>{project.name}</h1>
        <Badge>{project.status}</Badge>
      </PageHeader>
      
      <Tabs defaultValue="companies">
        <TabsList>
          <TabsTrigger value="companies">営業進捗</TabsTrigger>
          <TabsTrigger value="stats">統計</TabsTrigger>
          <TabsTrigger value="history">活動履歴</TabsTrigger>
        </TabsList>
        
        <TabsContent value="companies">
          <div className="mb-4">
            <Button onClick={() => navigate(`/clients/${project.client_id}/select-companies`)}>
              + 企業を追加
            </Button>
          </div>
          
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>企業名</TableHead>
                <TableHead>ステータス</TableHead>
                <TableHead>最終接触日</TableHead>
                <TableHead>担当者</TableHead>
                <TableHead>アクション</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projectCompanies.map(pc => (
                <TableRow key={pc.id}>
                  <TableCell>{pc.company.name}</TableCell>
                  <TableCell>
                    <Select
                      value={pc.status}
                      onValueChange={(value) => updateStatus(pc.id, value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="未接触">未接触</SelectItem>
                        <SelectItem value="DM送信済み">DM送信済み</SelectItem>
                        <SelectItem value="返信あり">返信あり</SelectItem>
                        <SelectItem value="アポ獲得">アポ獲得</SelectItem>
                        <SelectItem value="成約">成約</SelectItem>
                        <SelectItem value="NG">NG</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>{pc.contact_date}</TableCell>
                  <TableCell>{pc.staff_name}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="outline">
                      詳細
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

## APIエンドポイント（修正）

### 企業選択用API
```typescript
// クライアント用の企業一覧（NG判定付き）
GET /clients/{client_id}/available-companies
Query params:
  - search?: string
  - industry?: string
  - prefecture?: string
  - employee_min?: number
  - employee_max?: number
  - exclude_ng?: boolean (default: false)
  - show_ng?: boolean (default: true)

Response:
{
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

// 選択した企業を案件に追加
POST /projects/{project_id}/add-companies
Body:
{
  company_ids: number[]
}
```

## データフロー

```
1. クライアント登録
   POST /clients

2. NGリスト登録
   POST /clients/{id}/ng-companies/import

3. 案件作成
   POST /projects
   { client_id, name, description }

4. 企業選択・追加
   GET /clients/{id}/available-companies
   POST /projects/{id}/add-companies

5. 営業進捗更新
   PATCH /projects/{id}/companies/{company_id}
   { status, contact_date, notes }
```

## 重要な変更点

1. **メイン画面をクライアント一覧に変更**
   - 企業リストは管理画面扱い

2. **企業選択はクライアントコンテキスト内で実行**
   - `/clients/{id}/select-companies`

3. **NG判定はクライアント単位で適用**
   - 企業マスタ画面ではNG表示しない
   - クライアントの企業選択時のみNG判定

4. **営業進捗は案件詳細で管理**
   - ステータス更新
   - 活動履歴記録