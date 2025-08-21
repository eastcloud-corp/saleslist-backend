# 実装ガイド - 営業リスト管理システム

## 概要
クライアント中心のビジネスフローに基づく営業リスト管理システムの実装ガイド。
Vercel v0やその他のフロントエンド開発者向けの詳細な実装指示書。

## 技術スタック

### フロントエンド
- **フレームワーク**: Next.js 14 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS
- **UIコンポーネント**: shadcn/ui
- **フォーム管理**: React Hook Form + Zod
- **状態管理**: React Context API / Zustand（必要に応じて）

### バックエンド（モック）
- **モックサーバー**: Prism (Stoplight)
- **API仕様**: OpenAPI 3.0.3
- **エンドポイント**: https://saleslist-mock-api.onrender.com

### 認証・データベース（将来実装）
- **認証**: Supabase Auth
- **データベース**: Supabase (PostgreSQL)

## プロジェクト構造

```
saleslist-front/
├── app/
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── clients/
│   │   │   ├── page.tsx                 # クライアント一覧（スタート画面）
│   │   │   ├── [id]/
│   │   │   │   ├── page.tsx            # クライアント詳細
│   │   │   │   └── select-companies/
│   │   │   │       └── page.tsx        # 企業選択画面
│   │   │   └── new/
│   │   │       └── page.tsx            # 新規クライアント作成
│   │   ├── projects/
│   │   │   ├── page.tsx                # 案件一覧
│   │   │   └── [id]/
│   │   │       └── page.tsx            # 案件詳細・営業進捗
│   │   └── companies/
│   │       ├── page.tsx                # 企業マスタ（管理画面）
│   │       └── [id]/
│   │           └── page.tsx            # 企業詳細
│   └── layout.tsx
├── components/
│   ├── clients/
│   │   ├── client-list.tsx
│   │   ├── client-form.tsx
│   │   ├── ng-list-tab.tsx             # NGリスト管理タブ
│   │   └── ng-import-dialog.tsx        # NGインポートダイアログ
│   ├── companies/
│   │   ├── company-list.tsx
│   │   ├── company-row.tsx             # NG表示対応
│   │   └── company-selector.tsx        # 企業選択コンポーネント
│   ├── projects/
│   │   ├── project-list.tsx
│   │   ├── project-companies.tsx       # 営業進捗管理
│   │   └── status-selector.tsx
│   └── ui/                             # shadcn/ui components
├── lib/
│   ├── api-client.ts                   # API クライアント
│   ├── types.ts                        # 型定義
│   ├── utils.ts
│   └── constants.ts
└── hooks/
    ├── use-auth.tsx
    ├── use-clients.tsx
    ├── use-ng-list.tsx                 # NGリスト管理フック
    └── use-companies.tsx

```

## 実装する必要があるファイル

### 1. 基本設定ファイル

#### `/lib/types.ts` - 型定義
```typescript
export interface Client {
  id: number
  name: string
  company_type?: string
  industry?: string
  contact_person?: string
  contact_email?: string
  contact_phone?: string
  address?: string
  website?: string
  notes?: string
  is_active: boolean
  created_at: string
  updated_at: string
  // 集計フィールド
  active_projects_count?: number
  total_companies_count?: number
}

export interface Company {
  id: number
  name: string
  name_kana?: string
  postal_code?: string
  prefecture: string
  city?: string
  address?: string
  industry: string
  employee_count: string
  capital?: string
  establishment_year?: number
  website?: string
  phone?: string
  email?: string
  is_listed: boolean
  listing_name?: string
  department?: string
  position?: string
  is_global_ng: boolean
  ng_reason?: string
  created_at: string
  updated_at: string
  // NG判定情報
  ng_status?: {
    is_ng: boolean
    type: 'global' | 'client' | 'project' | null
    reason: string | null
  }
}

export interface ClientNGCompany {
  id: number
  client_id: number
  company_name: string
  company_id?: number
  matched: boolean
  reason?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Project {
  id: number
  client_id: number
  client?: Client
  name: string
  description?: string
  status: 'planning' | 'active' | 'completed' | 'on_hold'
  start_date?: string
  end_date?: string
  target_count?: number
  staff_id?: number
  created_at: string
  updated_at: string
}

export interface ProjectCompany {
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
  created_at: string
  updated_at: string
}
```

#### `/lib/api-client.ts` - APIクライアント
```typescript
class ApiClient {
  private baseURL: string
  private token: string | null = null
  private refreshToken: string | null = null
  private isRefreshingToken = false
  private refreshPromise: Promise<void> | null = null

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'https://saleslist-mock-api.onrender.com'
    this.loadTokens()
  }

  private loadTokens() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token')
      this.refreshToken = localStorage.getItem('refresh_token')
    }
  }

  private async refreshAccessToken(): Promise<void> {
    if (this.isRefreshingToken) {
      if (this.refreshPromise) {
        await this.refreshPromise
        return
      }
    }

    this.isRefreshingToken = true
    this.refreshPromise = new Promise(async (resolve, reject) => {
      try {
        const response = await fetch(`${this.baseURL}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.refreshToken}`,
            'Content-Type': 'application/json',
          },
        })

        if (!response.ok) {
          throw new Error('Token refresh failed')
        }

        const data = await response.json()
        this.token = data.access_token
        this.refreshToken = data.refresh_token
        
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        
        resolve()
      } catch (error) {
        reject(error)
      } finally {
        this.isRefreshingToken = false
        this.refreshPromise = null
      }
    })

    await this.refreshPromise
  }

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    let response = await fetch(`${this.baseURL}${path}`, {
      ...options,
      headers,
    })

    // トークンリフレッシュ処理
    if (response.status === 401 && this.refreshToken) {
      await this.refreshAccessToken()
      
      // リトライ
      response = await fetch(`${this.baseURL}${path}`, {
        ...options,
        headers: {
          ...headers,
          'Authorization': `Bearer ${this.token}`,
        },
      })
    }

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'API request failed')
    }

    return response.json()
  }

  // 便利メソッド
  get<T>(path: string, params?: Record<string, any>): Promise<T> {
    const queryString = params ? `?${new URLSearchParams(params).toString()}` : ''
    return this.request<T>(`${path}${queryString}`)
  }

  post<T>(path: string, body?: any): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  put<T>(path: string, body?: any): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
  }

  patch<T>(path: string, body?: any): Promise<T> {
    return this.request<T>(path, {
      method: 'PATCH',
      body: JSON.stringify(body),
    })
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>(path, {
      method: 'DELETE',
    })
  }

  async uploadFile(path: string, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${this.baseURL}${path}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
      },
      body: formData,
    })

    if (!response.ok) {
      throw new Error('File upload failed')
    }

    return response.json()
  }
}

export const apiClient = new ApiClient()
```

### 2. コンポーネント実装

#### `/components/clients/ng-list-tab.tsx` - NGリスト管理タブ
```typescript
import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Upload, Download, Trash2, AlertCircle } from 'lucide-react'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api-client'
import { ClientNGCompany } from '@/lib/types'

export function NGListTab({ clientId }: { clientId: number }) {
  const [ngList, setNgList] = useState<ClientNGCompany[]>([])
  const [isImporting, setIsImporting] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  const fetchNGList = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.get<{
        count: number
        matched_count: number
        unmatched_count: number
        results: ClientNGCompany[]
      }>(`/clients/${clientId}/ng-companies`)
      setNgList(response.results)
    } catch (error) {
      toast({
        title: 'エラー',
        description: 'NGリストの取得に失敗しました',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchNGList()
  }, [clientId])

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsImporting(true)
    
    try {
      const result = await apiClient.uploadFile(
        `/clients/${clientId}/ng-companies/import`,
        file
      )
      
      toast({
        title: 'インポート完了',
        description: `${result.imported_count}件のNGリストを登録しました（マッチ: ${result.matched_count}件）`,
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
      // ファイル入力をリセット
      event.target.value = ''
    }
  }

  const handleDelete = async (ngId: number) => {
    try {
      await apiClient.delete(`/clients/${clientId}/ng-companies/${ngId}`)
      toast({
        title: '削除完了',
        description: 'NG企業を削除しました',
      })
      fetchNGList()
    } catch (error) {
      toast({
        title: 'エラー',
        description: '削除に失敗しました',
        variant: 'destructive',
      })
    }
  }

  const downloadTemplate = () => {
    const csv = '企業名,理由\\n株式会社サンプル,競合他社\\n'
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'ng_list_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return <div>読み込み中...</div>
  }

  return (
    <div className="space-y-4">
      {/* インポートセクション */}
      <Card>
        <CardHeader>
          <CardTitle>NGリストインポート</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <Input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                disabled={isImporting}
              />
            </div>
            <Button
              variant="outline"
              onClick={downloadTemplate}
            >
              <Download className="mr-2 h-4 w-4" />
              テンプレート
            </Button>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            CSV形式で企業名とNG理由を一括登録できます
          </p>
        </CardContent>
      </Card>

      {/* NGリスト一覧 */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>登録済みNGリスト</CardTitle>
            <div className="flex gap-2">
              <Badge variant="default">
                マッチ済: {ngList.filter(ng => ng.matched).length}
              </Badge>
              <Badge variant="secondary">
                未マッチ: {ngList.filter(ng => !ng.matched).length}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>企業名</TableHead>
                <TableHead>マッチ状態</TableHead>
                <TableHead>理由</TableHead>
                <TableHead>登録日</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ngList.map((ng) => (
                <TableRow key={ng.id}>
                  <TableCell className="font-medium">
                    {ng.company_name}
                  </TableCell>
                  <TableCell>
                    {ng.matched ? (
                      <Badge variant="success">マッチ済</Badge>
                    ) : (
                      <Badge variant="outline">未マッチ</Badge>
                    )}
                  </TableCell>
                  <TableCell>{ng.reason || '-'}</TableCell>
                  <TableCell>
                    {new Date(ng.created_at).toLocaleDateString('ja-JP')}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(ng.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 3. フック実装

#### `/hooks/use-ng-list.tsx` - NGリスト管理フック
```typescript
import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import { ClientNGCompany } from '@/lib/types'

export function useNGList(clientId: number) {
  const [ngList, setNgList] = useState<ClientNGCompany[]>([])
  const [stats, setStats] = useState({
    count: 0,
    matched_count: 0,
    unmatched_count: 0
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchNGList = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await apiClient.get<{
        count: number
        matched_count: number
        unmatched_count: number
        results: ClientNGCompany[]
      }>(`/clients/${clientId}/ng-companies`)
      
      setNgList(response.results)
      setStats({
        count: response.count,
        matched_count: response.matched_count,
        unmatched_count: response.unmatched_count
      })
    } catch (err) {
      setError('NGリストの取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  const importCSV = async (file: File) => {
    const response = await apiClient.uploadFile(
      `/clients/${clientId}/ng-companies/import`,
      file
    )
    
    await fetchNGList()
    return response
  }

  const deleteNG = async (ngId: number) => {
    await apiClient.delete(`/clients/${clientId}/ng-companies/${ngId}`)
    await fetchNGList()
  }

  useEffect(() => {
    fetchNGList()
  }, [clientId])

  return {
    ngList,
    stats,
    isLoading,
    error,
    importCSV,
    deleteNG,
    refetch: fetchNGList
  }
}
```

## Vercel v0への提供ファイル

### 必須ファイル（順番に提供）
1. `/saleslist-backend/docs/correct_business_flow.md` - 正しいビジネスフロー
2. `/saleslist-backend/docs/DB_design.md` - データベース設計
3. `/saleslist-backend/docs/client_ng_management_spec.md` - クライアント・NG管理統合仕様
4. `/saleslist-backend/docs/screen_api_specification.md` - 画面・API統合仕様
5. `/saleslist-backend/deployment/swagger/openapi.yaml` - API仕様（必要部分のみ）
6. 本ファイル（implementation_guide.md）

### v0への指示テンプレート
```
営業リスト管理システムのフロントエンドを実装してください。

## 重要な設計方針
- クライアント中心のビジネスフロー
- スタート画面は /clients（クライアント一覧）
- 企業リストはマスタデータとして扱う
- NGリスト管理機能を含む

## 技術要件
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Hook Form + Zod

## 実装優先度
Phase 1:
1. クライアント一覧・詳細画面
2. NGリストCSVインポート機能
3. 企業選択画面（NG企業グレーアウト）

Phase 2:
4. 案件詳細・営業進捗管理
5. 企業マスタ管理（管理画面）

## API接続
- モックAPI: https://saleslist-mock-api.onrender.com
- JWT認証（Bearer Token）
- 自動トークンリフレッシュ実装済み

## テスト認証情報
Email: user@example.com
Password: password123

添付ファイルの仕様書に基づいて実装してください。
特にimplementation_guide.mdのコンポーネント例を参考にしてください。
```

## 環境変数設定

### `.env.local`
```
NEXT_PUBLIC_API_URL=https://saleslist-mock-api.onrender.com
NEXT_PUBLIC_APP_NAME=営業リスト管理システム
NEXT_PUBLIC_APP_VERSION=1.0.0
```

### `.env.development`
```
NEXT_PUBLIC_API_URL=http://localhost:4010
```

## テストシナリオ

### 1. クライアント管理
- [ ] クライアント一覧表示
- [ ] 新規クライアント作成
- [ ] クライアント詳細表示
- [ ] クライアント情報更新

### 2. NGリスト管理
- [ ] NGリストCSVインポート
- [ ] NGリスト表示（マッチ状態可視化）
- [ ] NG企業削除
- [ ] テンプレートダウンロード

### 3. 企業選択
- [ ] NG企業のグレーアウト表示
- [ ] NG理由のツールチップ表示
- [ ] 複数企業選択
- [ ] 案件への企業追加

### 4. 営業進捗管理
- [ ] ステータス更新
- [ ] 活動記録追加
- [ ] 統計表示

## トラブルシューティング

### CORS エラー
- モックAPIサーバーはCORS対応済み
- ローカル開発時は`http://localhost:3003`からのアクセスを許可

### 認証エラー
- トークンの有効期限切れ → 自動リフレッシュ
- リフレッシュトークンも期限切れ → 再ログイン画面へ

### CSVインポートエラー
- 文字コード: UTF-8推奨
- ファイルサイズ: 10MB以下
- フォーマット: ヘッダー行必須

## パフォーマンス最適化

- リスト表示: ページネーション実装（20件/ページ）
- 画像: next/imageによる最適化
- API呼び出し: useSWRによるキャッシュ管理（オプション）
- バンドルサイズ: 動的インポートの活用