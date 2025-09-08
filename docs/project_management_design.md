# 案件管理システム 設計書

## 重要: この設計書は既存の「案件管理」機能の拡張設計です
- 既存の `/projects` ページを拡張します
- 新しい「プロジェクト管理」ページは作成しません

## 0. フロントエンド UI 仕様

### 0.1 既存案件管理画面の拡張
既存の `/projects` ページに以下の機能を追加：

#### 一覧画面表示項目
**固定列（左側）：**
- 案件名（2行表示対応）
- クライアント名（2行表示対応）

**横スクロール列（重要度順）：**
- 進行状況（プルダウン選択）
- アポ数（数値入力）
- 承認数（数値入力）
- 返信数（数値入力）
- 友達数（数値入力）
- Dログイン可（チェックボックス）
- 運用者招待（チェックボックス）
- 状況（テキストエリア）
- 定例会実施日（カレンダー入力）
- リスト輸入先（プルダウン選択）
- 記載日（カレンダー入力）
- 進行タスク・ネクストタスク・期限（テキストエリア）
- デイリータスク（テキストエリア）
- 返信チェック（テキストエリア）
- 備考（テキストエリア）
- クレームor要望（テキストエリア）
- ディレクター（テキスト）
- 運用者（テキスト）
- 営業マン（テキスト）
- 運用開始日（カレンダー）
- 終了予定日（カレンダー）
- サービス（プルダウン選択）
- 媒体（プルダウン選択）
- 定例会ステータス（プルダウン選択）
- リスト有無（プルダウン選択）

#### 詳細画面専用項目
- クライアントNG、運用障壁（詳細画面のみ）
- 課題点、改善点（詳細画面のみ）

#### 契約情報（既存フィールド使用）
- 契約開始日 → `operation_start_date`（運用開始日）として管理
- 契約終了日 → `expected_end_date`（終了予定日）として管理
- 契約期間 → `contract_period`（既存フィールド）
- 記載日 → `entry_date_sales`（既存フィールド）

### 0.2 インライン編集機能
- 各行に編集ボタンを追加配置
- 編集モード時は該当行のみインライン編集可能
- 編集可能項目：チェックボックス2項目、進行状況、数値4項目、状況
- 保存/キャンセルボタン表示
- 他ユーザーが編集中の場合は「<ユーザー名>が使用中です」と表示
- 1つの案件に対して同時編集は1人のみ可能

### 0.3 排他制御仕様
- 編集モード開始時にロック取得
- 編集完了/キャンセル時にロック解除  
- ロックタイムアウト: 30分
- 保存後は画面リフレッシュして最新データ表示

## 1. 新規マスターテーブル

### 1.1 進行状況マスター (ProjectProgressStatus)
```sql
CREATE TABLE project_progress_status (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**初期データ:**
- 未着手
- ヒアリングシート記入中
- キックオフMTG
- DM作成・確認/アカウント構築
- リスト作成中
- 運用者アサイン中
- 運用中
- 停止
- 解釈
- 一時停止
- 契約満了
- 開始時期未定・変更
- 解体
- 営業追いかけ

### 1.2 媒体マスター (MediaType)
```sql
CREATE TABLE media_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 1.3 定例会ステータスマスター (RegularMeetingStatus)
```sql
CREATE TABLE regular_meeting_status (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**初期データ:**
- 未
- 済
- 不要
- 20日未満
- 未開始
- 最終定例会予定

### 1.4 リスト有無マスター (ListAvailability)
```sql
CREATE TABLE list_availability (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**初期データ:**
- 無
- 有（我々提供）
- 有（クライアント提供）

### 1.5 リスト輸入先マスター (ListImportSource)
```sql
CREATE TABLE list_import_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**初期データ:**
- インフォボックス
- セールスナビゲーター
- バジェットリスト
- 返信ありから
- その他
- 無

### 1.6 サービスマスター (ServiceType)
```sql
CREATE TABLE service_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**初期データ:**
- アウトソーシング
- SNS運用代行
- 広告代理店
- SEO
- HP制作
- Web制作
- Webマーケ
- 人材派遣
- 人材紹介
- 採用支援
- SES
- BPO
- 店舗
- 営業代行
- テレアポ
- アポ獲得
- M&A仲介
- 経営
- 助成金
- リスキリング
- 人材教育
- 社内教育
- 賃貸
- 売買
- アプリ開発
- Web開発
- SaaS
- Sier
- 経営者コミュニティ
- オンラインサロン
- 交流会
- 芸能
- 引っ越し
- 建設
- 動画制作
- エンタメ
- 資産運用
- EC
- LINE構築
- AI
- トレカ販売
- フランチャイズ
- アート
- HP掲載

### 1.7 編集ロックテーブル (ProjectEditLock)
```sql
CREATE TABLE project_edit_locks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    locked_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id)
);
```

**説明:**
- project_id: ロック対象の案件ID（ユニーク制約で同時編集防止）
- user_id: 編集中のユーザーID
- expires_at: ロック期限（30分後に自動解除）

## 2. 既存Project モデルの拡張設計

### 2.1 モデル統一方針
- **既存のProjectモデルを拡張します**
- 旧フィールド（description, manager, assigned_user等）は削除予定
- 設計書の新フィールドを正式採用

### 2.2 拡張フィールド定義
```python
class Project(models.Model):
    # 基本情報
    client = models.ForeignKey('clients.Client', on_delete=models.RESTRICT, related_name='projects')
    name = models.CharField(max_length=255, verbose_name="案件名")
    location_prefecture = models.CharField(max_length=10, blank=True, verbose_name="所在地(都道府県)")
    industry = models.CharField(max_length=100, blank=True, verbose_name="業種")
    service_type = models.ForeignKey('ServiceType', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="サービス")
    
    # リンク情報
    operation_sheet_link = models.URLField(blank=True, verbose_name="運用シートリンク")
    report_link = models.URLField(blank=True, verbose_name="レポートリンク")
    account_link = models.URLField(blank=True, verbose_name="アカウントリンク")
    
    # 媒体・制限情報
    media_type = models.ForeignKey('MediaType', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="媒体")
    restrictions = models.TextField(blank=True, verbose_name="制限")
    contact_info = models.TextField(blank=True, verbose_name="連絡先")
    
    # 数値データ
    appointment_count = models.IntegerField(default=0, verbose_name="アポ数")
    approval_count = models.IntegerField(default=0, verbose_name="承認数")
    reply_count = models.IntegerField(default=0, verbose_name="返信数")
    friends_count = models.IntegerField(default=0, verbose_name="友達数")
    
    # 状況・進行管理
    situation = models.TextField(blank=True, verbose_name="状況")
    progress_status = models.ForeignKey('ProjectProgressStatus', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="進行状況")
    
    # チェック・タスク管理
    reply_check_notes = models.TextField(blank=True, verbose_name="返信チェック(伊藤が朝消す)")
    daily_tasks = models.TextField(blank=True, verbose_name="デイリータスク(当日行うべき業務を記載)")
    progress_tasks = models.TextField(blank=True, verbose_name="進行タスク・ネクストタスク・期限")
    remarks = models.TextField(blank=True, verbose_name="備考(現在の状態について記載)")
    complaints_requests = models.TextField(blank=True, verbose_name="クレームor要望（20%上回ったものを最優先処理）")
    
    # NG・課題管理
    client_ng_operational_barriers = models.TextField(blank=True, verbose_name="クライアントNG、運用障壁")
    issues_improvements = models.TextField(blank=True, verbose_name="課題点＋改善点")
    
    # 担当者情報
    director = models.CharField(max_length=100, blank=True, verbose_name="ディレクター")
    operator = models.CharField(max_length=100, blank=True, verbose_name="運用者")
    sales_person = models.CharField(max_length=100, blank=True, verbose_name="営業マン")
    assignment_available = models.BooleanField(default=True, verbose_name="アサイン可否")
    
    # チェックボックス項目
    director_login_available = models.BooleanField(default=False, verbose_name="Dがログインできるアカウント")
    operator_group_invited = models.BooleanField(default=False, verbose_name="運用者グループ招待")
    
    # 契約・期間情報
    contract_period = models.CharField(max_length=100, blank=True, verbose_name="契約期間")
    entry_date_sales = models.DateField(null=True, blank=True, verbose_name="記載日(営業)")
    operation_start_date = models.DateField(null=True, blank=True, verbose_name="運用開始日")
    expected_end_date = models.DateField(null=True, blank=True, verbose_name="終了予定日")
    period_extension = models.CharField(max_length=100, blank=True, verbose_name="期間延期")
    
    # 定例会情報
    regular_meeting_status = models.ForeignKey('RegularMeetingStatus', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="定例会提示")
    regular_meeting_date = models.DateField(null=True, blank=True, verbose_name="定例会実施日")
    
    # リスト情報
    list_availability = models.ForeignKey('ListAvailability', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="リスト有無")
    list_import_source = models.ForeignKey('ListImportSource', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="リスト輸入先")
    list_count = models.IntegerField(default=0, verbose_name="リスト数")
    
    # システム管理
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## 3. Django Admin 設定

### 3.1 各マスターテーブルのAdmin設定
```python
# admin.py
@admin.register(ProjectProgressStatus)
class ProjectProgressStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    list_filter = ['is_active']
    ordering = ['display_order']

@admin.register(MediaType)
class MediaTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active']
    list_editable = ['display_order', 'is_active']
    list_filter = ['is_active']
    ordering = ['display_order']

# 他のマスターテーブルも同様の設定
```

### 3.2 Project Admin設定
```python
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'progress_status', 'director', 'operator', 'operation_start_date']
    list_filter = ['progress_status', 'media_type', 'list_availability', 'regular_meeting_status']
    search_fields = ['name', 'client__name', 'director', 'operator', 'sales_person']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('client', 'name', 'location_prefecture', 'industry', 'service_type')
        }),
        ('リンク情報', {
            'fields': ('operation_sheet_link', 'report_link', 'account_link')
        }),
        ('媒体・制限', {
            'fields': ('media_type', 'restrictions', 'contact_info')
        }),
        ('数値データ', {
            'fields': ('appointment_count', 'approval_count', 'reply_count', 'friends_count')
        }),
        ('状況・進行管理', {
            'fields': ('situation', 'progress_status', 'reply_check_notes', 'daily_tasks', 'progress_tasks', 'remarks', 'complaints_requests')
        }),
        ('NG・課題管理', {
            'fields': ('client_ng_operational_barriers', 'issues_improvements')
        }),
        ('担当者情報', {
            'fields': ('director', 'operator', 'sales_person', 'assignment_available')
        }),
        ('システム設定', {
            'fields': ('director_login_available', 'operator_group_invited')
        }),
        ('契約・期間情報', {
            'fields': ('contract_period', 'entry_date_sales', 'operation_start_date', 'expected_end_date', 'period_extension')
        }),
        ('定例会情報', {
            'fields': ('regular_meeting_status', 'regular_meeting_date')
        }),
        ('リスト情報', {
            'fields': ('list_availability', 'list_import_source', 'list_count')
        }),
    )
```

## 4. マイグレーション手順

1. 新しいマスターテーブルの作成
2. 既存Projectモデルの拡張
3. 初期データの投入
4. Admin設定の適用

## 5. API設計（既存APIの拡張）

### 5.1 既存案件一覧API拡張 (GET /api/v1/projects/)
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "name": "テスト案件",
      "client_name": "テスト企業",
      "progress_status": "運用中",
      "director_login_available": true,
      "operator_group_invited": false,
      "appointment_count": 5,
      "approval_count": 3,
      "reply_count": 8,
      "friends_count": 15,
      "situation": "順調に進行中",
      "is_locked": false,
      "locked_by": null,
      "locked_by_name": null,
      "locked_until": null,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### 5.2 編集ロック取得 (POST /api/v1/projects/{id}/lock/)
```json
// Request: 空
// Response:
{
  "success": true,
  "locked_until": "2024-01-01T12:30:00Z"
}

// エラー時:
{
  "success": false,
  "error": "この案件は田中太郎が編集中です",
  "locked_by_name": "田中太郎",
  "locked_until": "2024-01-01T12:30:00Z"
}
```

### 5.3 編集ロック解除 (DELETE /api/v1/projects/{id}/lock/)
```json
{
  "success": true
}
```

### 5.4 案件更新 (PATCH /api/v1/projects/{id}/)
```json
// Request:
{
  "director_login_available": true,
  "operator_group_invited": false,
  "progress_status": "運用中",
  "appointment_count": 6,
  "approval_count": 4,
  "reply_count": 9,
  "friends_count": 16,
  "situation": "更新された状況"
}

// Response:
{
  "success": true,
  "data": { /* 更新後のデータ */ }
}
```

### 5.5 一括編集 (PATCH /api/v1/projects/bulk-update/)
```json
// Request:
{
  "project_ids": [1, 2, 3],
  "update_data": {
    "director_login_available": true,
    "progress_status_id": 7
  }
}

// Response:
{
  "success": true,
  "updated_count": 3,
  "message": "3件の案件を更新しました"
}
```

### 5.6 期限切れロック自動削除
- バックグラウンドタスクで30分経過したロックを自動削除
- または、API アクセス時にexpired lockをチェック・削除

## 6. 実装方針

### 6.1 段階的実装
1. **フェーズ1**: 既存 `/projects` 画面に表示項目追加
2. **フェーズ2**: インライン編集機能の追加  
3. **フェーズ3**: 排他制御機能の実装
4. **フェーズ4**: 旧フィールドの削除とクリーンアップ

### 6.2 削除予定の不要な実装
- `/project-management` ページとその関連コンポーネント
- 管理モード用の複雑なAPI分岐
- ProjectManagementXXXシリアライザー群

### 6.3 保持する既存実装  
- 既存 `/projects` ページのベース機能
- Projectモデルの新フィールド群
- マスターテーブル群
- 編集ロック機能（ProjectEditLock）

この設計により、既存の「案件管理」を拡張し、顧客要望の「情報追加」と「インライン編集」機能を実現します。