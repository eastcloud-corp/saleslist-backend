# Vercel v0向け実装指示書

## システム概要
営業リスト管理システムのフロントエンドを実装してください。
クライアント企業からの営業代行依頼を管理し、NGリストによる企業フィルタリングを含む営業活動支援システムです。

## 重要な設計方針
- **クライアント中心のビジネスフロー**
- **スタート画面は /clients（クライアント一覧）**
- **企業リストはマスタデータとして扱う**
- **NGリスト管理機能を含む**

## 技術要件
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Hook Form + Zod
- 日本語UI

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

## 必要なファイル一覧
以下のファイルを参照して実装してください：

1. `/saleslist-backend/docs/correct_business_flow.md` - ビジネスフロー
2. `/saleslist-backend/docs/DB_design.md` - データベース設計
3. `/saleslist-backend/docs/client_ng_management_spec.md` - クライアント・NG管理仕様
4. `/saleslist-backend/docs/screen_api_specification.md` - 画面・API仕様
5. `/saleslist-backend/docs/implementation_guide.md` - 実装ガイド

## 実装優先度

### Phase 1（最優先）
1. **クライアント一覧画面（/clients）**
   - クライアント企業の一覧表示
   - 新規クライアント追加
   - 詳細画面への遷移

2. **クライアント詳細画面（/clients/{id}）**
   - 基本情報タブ
   - NGリストタブ（CSVインポート機能）
   - 案件一覧タブ

3. **NGリスト管理機能**
   - CSVインポート
   - マッチ状態の可視化
   - 個別削除機能

4. **企業選択画面（/clients/{id}/select-companies）**
   - NG企業のグレーアウト表示
   - NG理由のツールチップ
   - 複数選択機能

### Phase 2（推奨）
5. **案件詳細画面（/projects/{id}）**
   - 営業進捗管理
   - ステータス更新
   - 活動履歴

6. **企業マスタ管理（/companies）**
   - 管理画面扱い
   - 一括インポート/エクスポート

## API接続設定

### 環境変数（.env.local）
```
NEXT_PUBLIC_API_URL=https://saleslist-mock-api.onrender.com
NEXT_PUBLIC_APP_NAME=営業リスト管理システム
NEXT_PUBLIC_APP_VERSION=1.0.0
```

### 認証情報（テスト用）
```
Email: user@example.com
Password: password123
```

## 主要APIエンドポイント

### クライアント管理
- `GET /clients` - クライアント一覧
- `GET /clients/{id}` - クライアント詳細
- `POST /clients` - クライアント作成
- `PUT /clients/{id}` - クライアント更新

### NGリスト管理
- `GET /clients/{id}/ng-companies` - NGリスト取得
- `POST /clients/{id}/ng-companies/import` - CSVインポート
- `DELETE /clients/{id}/ng-companies/{ng_id}` - NG削除

### 企業選択（クライアント用）
- `GET /clients/{id}/available-companies` - NG判定付き企業一覧
- `POST /projects/{id}/add-companies` - 選択企業を案件に追加

### 案件管理
- `GET /projects` - 案件一覧
- `GET /projects/{id}` - 案件詳細
- `GET /projects/{id}/companies` - 案件企業一覧
- `PATCH /projects/{id}/companies/{company_id}` - ステータス更新

## コンポーネント実装例

### NGリストタブ（implementation_guide.md参照）
```typescript
export function NGListTab({ clientId }: { clientId: number }) {
  // CSVインポート機能
  // NGリスト表示
  // マッチ状態の可視化
  // 個別削除機能
}
```

### 企業選択時のNG表示
```typescript
function CompanyRow({ company, clientId }: Props) {
  const ngStatus = company.ng_status
  
  return (
    <TableRow className={ngStatus?.is_ng ? 'bg-red-50' : ''}>
      <TableCell>
        <Checkbox disabled={ngStatus?.is_ng} />
      </TableCell>
      <TableCell>
        {company.name}
        {ngStatus?.is_ng && <Badge variant="destructive">NG</Badge>}
      </TableCell>
    </TableRow>
  )
}
```

## UI/UX要件

### NGリスト管理
- CSVテンプレートダウンロード機能
- ドラッグ&ドロップ対応
- インポート進捗表示
- エラーメッセージの詳細表示

### 企業選択
- NG企業は赤色背景でハイライト
- NGバッジとツールチップで理由表示
- フィルタリング機能（業界、地域、規模）
- ページネーション（20件/ページ）

### 営業進捗管理
- ステータス選択（ドロップダウン）
- 活動履歴のタイムライン表示
- 統計情報のダッシュボード

## エラーハンドリング
- 401エラー時: 自動トークンリフレッシュ
- ネットワークエラー: リトライボタン表示
- バリデーションエラー: フィールドごとのエラー表示
- CSVインポートエラー: 詳細なエラーレポート

## パフォーマンス最適化
- リスト表示: ページネーション
- API呼び出し: デバウンス処理
- 画像: next/image最適化
- コンポーネント: 動的インポート

## テストシナリオ
1. クライアント作成→NGリストインポート→企業選択→案件作成
2. NG企業のフィルタリング確認
3. 営業ステータス更新フロー
4. CSVインポート（正常/異常）

## 注意事項
- すべてのUIは日本語で実装
- レスポンシブデザイン対応
- ローディング状態の表示必須
- エラー時は具体的なメッセージ表示
- CSVは UTF-8、10MB以下

## 実装の進め方
1. まずimplementation_guide.mdのコンポーネント例を参照
2. screen_api_specification.mdで画面とAPIの対応を確認
3. client_ng_management_spec.mdでNGリスト機能の詳細を理解
4. correct_business_flow.mdで全体のフローを把握

実装時は特にクライアント中心のフローを意識し、企業リストはあくまでマスタデータとして扱うことを忘れないでください。