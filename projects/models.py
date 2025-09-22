from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Project(models.Model):
    """案件マスタ（拡張版）"""
    STATUS_CHOICES = [
        ('進行中', '進行中'),
        ('完了', '完了'),
        ('中止', '中止'),
    ]
    
    # 基本情報
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.RESTRICT,
        related_name='projects',
        verbose_name="クライアント"
    )
    name = models.CharField(max_length=255, verbose_name="案件名")
    location_prefecture = models.CharField(max_length=10, blank=True, verbose_name="所在地(都道府県)")
    industry = models.CharField(max_length=100, blank=True, verbose_name="業種")
    service_type = models.ForeignKey(
        'masters.ServiceType', 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        verbose_name="サービス"
    )
    
    # リンク情報
    operation_sheet_link = models.URLField(blank=True, verbose_name="運用シートリンク")
    report_link = models.URLField(blank=True, verbose_name="レポートリンク")
    account_link = models.URLField(blank=True, verbose_name="アカウントリンク")
    
    # 媒体・制限情報
    media_type = models.ForeignKey(
        'masters.MediaType', 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        verbose_name="媒体"
    )
    restrictions = models.TextField(blank=True, verbose_name="制限")
    contact_info = models.TextField(blank=True, verbose_name="連絡先")
    
    # 数値データ
    appointment_count = models.IntegerField(default=0, verbose_name="アポ数")
    approval_count = models.IntegerField(default=0, verbose_name="承認数")
    reply_count = models.IntegerField(default=0, verbose_name="返信数")
    friends_count = models.IntegerField(default=0, verbose_name="友達数")
    
    # 状況・進行管理
    situation = models.TextField(blank=True, verbose_name="状況")
    progress_status = models.ForeignKey(
        'masters.ProjectProgressStatus', 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        verbose_name="進行状況"
    )
    
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
    regular_meeting_status = models.ForeignKey(
        'masters.RegularMeetingStatus', 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        verbose_name="定例会提示"
    )
    regular_meeting_date = models.DateField(null=True, blank=True, verbose_name="定例会実施日")
    
    # リスト情報
    list_availability = models.ForeignKey(
        'masters.ListAvailability', 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        verbose_name="リスト有無"
    )
    list_import_source = models.ForeignKey(
        'masters.ListImportSource', 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        verbose_name="リスト輸入先"
    )
    list_count = models.IntegerField(default=0, verbose_name="リスト数")
    
    # 旧フィールド（互換性維持のため残す）
    description = models.TextField(blank=True, verbose_name="案件概要")
    manager = models.CharField(max_length=100, blank=True, verbose_name="バジェット側担当者")
    assigned_user = models.CharField(max_length=100, blank=True, verbose_name="担当ユーザー")
    target_industry = models.CharField(max_length=100, blank=True, verbose_name="ターゲット業界")
    target_company_size = models.CharField(max_length=50, blank=True, verbose_name="ターゲット企業規模")
    dm_template = models.TextField(blank=True, verbose_name="DMテンプレート")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='進行中', verbose_name="ステータス")
    start_date = models.DateField(null=True, blank=True, verbose_name="開始日")
    end_date = models.DateField(null=True, blank=True, verbose_name="終了予定日")
    
    # システム管理
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'projects'
        verbose_name = "案件"
        verbose_name_plural = "案件"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['name']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name


class ProjectCompany(models.Model):
    """案件企業リスト（営業ステータス管理）"""
    CONTACT_STATUS_CHOICES = [
        ('未接触', '未接触'),
        ('DM送信予定', 'DM送信予定'),
        ('DM送信済み', 'DM送信済み'),
        ('返信あり', '返信あり'),
        ('アポ獲得', 'アポ獲得'),
        ('成約', '成約'),
        ('NG', 'NG'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='project_companies',
        verbose_name="案件"
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='project_companies',
        verbose_name="企業"
    )
    status = models.CharField(
        max_length=20, 
        choices=CONTACT_STATUS_CHOICES, 
        default='未接触',
        verbose_name="営業ステータス"
    )
    contact_date = models.DateField(null=True, blank=True, verbose_name="最終接触日")
    staff_name = models.CharField(max_length=100, blank=True, verbose_name="担当者")
    notes = models.TextField(blank=True, verbose_name="個別メモ")
    
    # アポ実績管理
    appointment_count = models.IntegerField(default=0, verbose_name="アポ獲得数")
    last_appointment_date = models.DateField(null=True, blank=True, verbose_name="最終アポ日")
    appointment_result = models.CharField(
        max_length=20,
        choices=[('成約', '成約'), ('継続検討', '継続検討'), ('見送り', '見送り')],
        blank=True,
        verbose_name="アポ結果"
    )
    is_active = models.BooleanField(default=True, verbose_name="アクティブ状態")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'project_companies'
        verbose_name = "案件企業"
        verbose_name_plural = "案件企業"
        unique_together = ['project', 'company']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['company']),
            models.Index(fields=['status']),
            models.Index(fields=['contact_date']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.company.name}"


class ProjectNGCompany(models.Model):
    """案件NG企業設定"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='ng_companies',
        verbose_name="案件"
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='ng_projects',
        verbose_name="企業"
    )
    reason = models.TextField(blank=True, verbose_name="NG理由")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = 'project_ng_companies'
        verbose_name = "案件NG企業"
        verbose_name_plural = "案件NG企業"
        unique_together = ['project', 'company']
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['company']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.company.name} (NG)"


class NGImportLog(models.Model):
    """NGリストインポート履歴"""
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="クライアント"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="案件"
    )
    file_name = models.CharField(max_length=255, blank=True, verbose_name="ファイル名")
    imported_count = models.IntegerField(default=0, verbose_name="インポート総数")
    matched_count = models.IntegerField(default=0, verbose_name="マッチした数")
    unmatched_count = models.IntegerField(default=0, verbose_name="マッチしなかった数")
    imported_by = models.CharField(max_length=100, blank=True, verbose_name="インポート実行者")
    error_messages = models.TextField(blank=True, verbose_name="エラーメッセージ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = 'ng_import_logs'
        verbose_name = "NGリストインポート履歴"
        verbose_name_plural = "NGリストインポート履歴"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['project']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Import {self.id}: {self.file_name}"


class SavedFilter(models.Model):
    """保存済みフィルタ"""
    user_id = models.IntegerField(null=True, blank=True, verbose_name="ユーザーID")
    name = models.CharField(max_length=100, verbose_name="フィルタ名")
    filter_conditions = models.JSONField(verbose_name="検索条件")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'saved_filters'
        verbose_name = "保存済みフィルタ"
        verbose_name_plural = "保存済みフィルタ"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class RandomOrder(models.Model):
    """ランダム表示順序保持"""
    user_id = models.IntegerField(null=True, blank=True, verbose_name="ユーザーID")
    session_id = models.CharField(max_length=255, blank=True, verbose_name="セッションID")
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="案件"
    )
    filter_hash = models.CharField(max_length=64, verbose_name="フィルタハッシュ")
    company_ids_order = models.JSONField(
        default=list,
        verbose_name="企業ID表示順序"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = 'random_orders'
        verbose_name = "ランダム表示順序"
        verbose_name_plural = "ランダム表示順序"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['filter_hash']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"RandomOrder {self.id}: {self.filter_hash}"


class SalesHistory(models.Model):
    """営業履歴（詳細ステータス管理）"""
    project_company = models.ForeignKey(
        ProjectCompany,
        on_delete=models.CASCADE,
        related_name='sales_history',
        verbose_name="案件企業"
    )
    status = models.CharField(max_length=50, verbose_name="営業ステータス")
    status_date = models.DateField(verbose_name="ステータス日付")
    staff_name = models.CharField(max_length=100, blank=True, verbose_name="担当者")
    notes = models.TextField(blank=True, verbose_name="履歴メモ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = 'sales_history'
        verbose_name = "営業履歴"
        verbose_name_plural = "営業履歴"
        ordering = ['-status_date', '-created_at']
        indexes = [
            models.Index(fields=['project_company']),
            models.Index(fields=['status']),
            models.Index(fields=['status_date']),
        ]

    def __str__(self):
        return f"{self.project_company} - {self.status} ({self.status_date})"


class ProjectEditLock(models.Model):
    """案件編集ロック"""
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='edit_lock',
        verbose_name="案件"
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        verbose_name="編集中ユーザー"
    )
    locked_at = models.DateTimeField(auto_now_add=True, verbose_name="ロック開始日時")
    expires_at = models.DateTimeField(verbose_name="ロック期限")
    
    class Meta:
        db_table = 'project_edit_locks'
        verbose_name = "案件編集ロック"
        verbose_name_plural = "案件編集ロック"
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"Lock: {self.project.name} by {self.user.name}"


class PageEditLock(models.Model):
    """ページ単位編集ロック"""
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        verbose_name="編集中ユーザー"
    )
    page_number = models.IntegerField(verbose_name="ページ番号")
    page_size = models.IntegerField(default=20, verbose_name="ページサイズ")
    filter_hash = models.CharField(max_length=64, blank=True, verbose_name="フィルタハッシュ")
    locked_at = models.DateTimeField(auto_now_add=True, verbose_name="ロック開始日時")
    expires_at = models.DateTimeField(verbose_name="ロック期限")
    
    class Meta:
        db_table = 'page_edit_locks'
        verbose_name = "ページ編集ロック"
        verbose_name_plural = "ページ編集ロック"
        unique_together = ['page_number', 'filter_hash']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['page_number']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['filter_hash']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"PageLock: Page {self.page_number} by {self.user.name}"


class ProjectSnapshot(models.Model):
    """案件一括編集に備えるスナップショット"""

    SOURCE_CHOICES = [
        ("bulk_edit", "一括編集"),
        ("undo", "取り消し"),
        ("restore", "復元"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="snapshots",
        verbose_name="案件"
    )
    data = models.JSONField(verbose_name="スナップショットデータ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_snapshots",
        verbose_name="作成者"
    )
    reason = models.CharField(max_length=255, blank=True, verbose_name="理由")
    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default="bulk_edit",
        verbose_name="生成元"
    )

    class Meta:
        db_table = "project_snapshots"
        verbose_name = "案件スナップショット"
        verbose_name_plural = "案件スナップショット"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "created_at"]),
        ]

    def __str__(self):
        timestamp = self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "unknown"
        return f"Snapshot(Project={self.project_id}, at={timestamp})"
