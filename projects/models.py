from django.db import models


class Project(models.Model):
    """案件マスタ"""
    STATUS_CHOICES = [
        ('進行中', '進行中'),
        ('完了', '完了'),
        ('中止', '中止'),
    ]
    
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.RESTRICT,
        related_name='projects',
        verbose_name="クライアント"
    )
    name = models.CharField(max_length=255, verbose_name="案件名")
    description = models.TextField(blank=True, verbose_name="案件概要")
    manager = models.CharField(max_length=100, blank=True, verbose_name="バジェット側担当者")
    assigned_user = models.CharField(max_length=100, blank=True, verbose_name="担当ユーザー")
    target_industry = models.CharField(max_length=100, blank=True, verbose_name="ターゲット業界")
    target_company_size = models.CharField(max_length=50, blank=True, verbose_name="ターゲット企業規模")
    dm_template = models.TextField(blank=True, verbose_name="DMテンプレート")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='進行中', verbose_name="ステータス")
    start_date = models.DateField(null=True, blank=True, verbose_name="開始日")
    end_date = models.DateField(null=True, blank=True, verbose_name="終了予定日")
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
