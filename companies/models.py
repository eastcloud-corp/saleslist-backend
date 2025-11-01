import hashlib

from django.conf import settings
from django.db import models
from django.utils import timezone


class Company(models.Model):
    """企業マスタ（営業対象の企業）"""
    # 基本情報
    name = models.CharField(max_length=255, verbose_name="会社名")
    corporate_number = models.CharField(max_length=13, blank=True, verbose_name="法人番号")
    industry = models.CharField(max_length=100, blank=True, verbose_name="業種")
    
    # 担当者情報
    contact_person_name = models.CharField(max_length=100, blank=True, verbose_name="担当者名")
    contact_person_position = models.CharField(max_length=100, blank=True, verbose_name="担当者役職")
    facebook_url = models.URLField(max_length=500, blank=True, verbose_name="Facebookリンク")
    facebook_page_id = models.CharField(max_length=128, blank=True, verbose_name="FacebookページID")
    
    # 事業情報
    tob_toc_type = models.CharField(
        max_length=10, 
        choices=[('toB', 'toB'), ('toC', 'toC'), ('Both', 'Both')],
        blank=True, 
        verbose_name="toB/toC"
    )
    business_description = models.TextField(blank=True, verbose_name="事業内容")
    
    # 所在地情報
    prefecture = models.CharField(max_length=10, blank=True, verbose_name="都道府県")
    city = models.CharField(max_length=100, blank=True, verbose_name="所在地詳細")
    
    # 規模情報
    employee_count = models.IntegerField(null=True, blank=True, verbose_name="従業員数")
    revenue = models.BigIntegerField(null=True, blank=True, verbose_name="売上規模")
    capital = models.BigIntegerField(null=True, blank=True, verbose_name="資本金")
    established_year = models.IntegerField(null=True, blank=True, verbose_name="設立年")
    
    # 連絡先情報
    website_url = models.URLField(max_length=500, blank=True, verbose_name="会社HP")
    contact_email = models.EmailField(blank=True, verbose_name="連絡先メール")
    phone = models.CharField(max_length=20, blank=True, verbose_name="電話番号")
    
    # システム管理
    notes = models.TextField(blank=True, verbose_name="備考")
    is_global_ng = models.BooleanField(default=False, verbose_name="グローバルNG設定")
    facebook_friend_count = models.IntegerField(null=True, blank=True, verbose_name="Facebook友だち数")
    facebook_latest_post_at = models.DateTimeField(null=True, blank=True, verbose_name="Facebook最新投稿日時")
    facebook_data_synced_at = models.DateTimeField(null=True, blank=True, verbose_name="Facebook同期日時")
    latest_activity_at = models.DateTimeField(null=True, blank=True, verbose_name="最新アクティビティ時刻")
    ai_last_enriched_at = models.DateTimeField(null=True, blank=True, verbose_name="AI最終補完日時")
    ai_last_enriched_source = models.CharField(max_length=32, blank=True, verbose_name="AI補完ソース")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'companies'
        verbose_name = "企業"
        verbose_name_plural = "企業"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['industry']),
            models.Index(fields=['prefecture']),
            models.Index(fields=['employee_count']),
            models.Index(fields=['is_global_ng']),
            models.Index(fields=['created_at']),
            models.Index(fields=['latest_activity_at']),
        ]

    def __str__(self):
        return self.name


class CompanyFacebookSnapshot(models.Model):
    """Facebookメトリクスの取得履歴"""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='facebook_snapshots',
        verbose_name="企業"
    )
    friend_count = models.IntegerField(null=True, blank=True, verbose_name="友だち数")
    friend_count_fetched_at = models.DateTimeField(null=True, blank=True, verbose_name="友だち数取得時刻")
    latest_posted_at = models.DateTimeField(null=True, blank=True, verbose_name="最新投稿時刻")
    latest_post_fetched_at = models.DateTimeField(null=True, blank=True, verbose_name="最新投稿取得時刻")
    source = models.CharField(max_length=50, default="celery", verbose_name="取得元")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'company_facebook_snapshots'
        verbose_name = "Facebookスナップショット"
        verbose_name_plural = "Facebookスナップショット"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'created_at']),
        ]

    def __str__(self):
        return f"{self.company.name} snapshot @ {self.created_at:%Y-%m-%d %H:%M}"

class Executive(models.Model):
    """代表者・役員情報"""
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='executives',
        verbose_name="企業"
    )
    name = models.CharField(max_length=100, verbose_name="役員名")
    position = models.CharField(max_length=100, blank=True, verbose_name="役職")
    facebook_url = models.URLField(max_length=500, blank=True, verbose_name="Facebook URL")
    other_sns_url = models.URLField(max_length=500, blank=True, verbose_name="その他SNS URL")
    direct_email = models.EmailField(blank=True, verbose_name="直接メール")
    notes = models.TextField(blank=True, verbose_name="備考")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'executives'
        verbose_name = "役員"
        verbose_name_plural = "役員"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['name']),
            models.Index(fields=['facebook_url'], 
                        condition=models.Q(facebook_url__isnull=False),
                        name='executives_facebook_url_idx'),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.name}"


class CompanyUpdateCandidate(models.Model):
    """企業情報の補完候補"""

    SOURCE_RULE = "RULE"
    SOURCE_AI = "AI"
    SOURCE_MANUAL = "MANUAL"
    SOURCE_CHOICES = [
        (SOURCE_RULE, "Rule"),
        (SOURCE_AI, "AI"),
        (SOURCE_MANUAL, "Manual"),
    ]

    STATUS_PENDING = "pending"
    STATUS_MERGED = "merged"
    STATUS_REJECTED = "rejected"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_MERGED, "Merged"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_EXPIRED, "Expired"),
    ]

    REJECTION_REASON_NONE = ""
    REJECTION_REASON_MISMATCH = "mismatch_company"
    REJECTION_REASON_INVALID = "invalid_value"
    REJECTION_REASON_OUTDATED = "outdated"
    REJECTION_REASON_DUPLICATE = "duplicate"
    REJECTION_REASON_OTHER = "other"
    REJECTION_REASON_CHOICES = [
        (REJECTION_REASON_NONE, "指定なし"),
        (REJECTION_REASON_MISMATCH, "同名別会社"),
        (REJECTION_REASON_INVALID, "不正値"),
        (REJECTION_REASON_OUTDATED, "古い情報"),
        (REJECTION_REASON_DUPLICATE, "重複"),
        (REJECTION_REASON_OTHER, "その他"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="update_candidates",
        verbose_name="企業",
    )
    field = models.CharField(max_length=100, verbose_name="対象フィールド")
    candidate_value = models.TextField(verbose_name="候補値")
    value_hash = models.CharField(max_length=128, blank=True, verbose_name="値ハッシュ")
    source_type = models.CharField(
        max_length=16,
        choices=SOURCE_CHOICES,
        default=SOURCE_RULE,
        verbose_name="取得ソース種別",
    )
    source_detail = models.CharField(max_length=255, blank=True, verbose_name="ソース詳細")
    confidence = models.PositiveSmallIntegerField(
        default=100,
        verbose_name="確信度"
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="ステータス",
    )
    collected_at = models.DateTimeField(default=timezone.now, verbose_name="取得日時")
    merged_at = models.DateTimeField(null=True, blank=True, verbose_name="反映日時")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="否認日時")
    rejection_reason_code = models.CharField(
        max_length=32,
        choices=REJECTION_REASON_CHOICES,
        default=REJECTION_REASON_NONE,
        blank=True,
        verbose_name="否認理由コード",
    )
    rejection_reason_detail = models.TextField(blank=True, verbose_name="否認理由詳細")
    block_reproposal = models.BooleanField(default=False, verbose_name="再提案ブロック")
    source_company_name = models.CharField(max_length=255, blank=True, verbose_name="ソース企業名")
    source_corporate_number = models.CharField(max_length=13, blank=True, verbose_name="ソース法人番号")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "company_update_candidates"
        verbose_name = "企業補完候補"
        verbose_name_plural = "企業補完候補"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "field"]),
            models.Index(fields=["status"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["value_hash"]),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.field}"

    @staticmethod
    def make_value_hash(field: str, value: str) -> str:
        normalized_field = (field or "").strip().lower()
        normalized_value = (value or "").strip()
        payload = f"{normalized_field}::{normalized_value}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def ensure_value_hash(self) -> None:
        """候補値に対応するハッシュが未設定の場合は生成する。"""
        if not self.value_hash and self.candidate_value is not None:
            self.value_hash = self.make_value_hash(self.field, str(self.candidate_value))


class ExternalSourceRecord(models.Model):
    """外部データソースからの取得履歴を管理する。"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="external_source_records",
        verbose_name="企業",
    )
    field = models.CharField(max_length=100, verbose_name="対象フィールド")
    source = models.CharField(max_length=100, verbose_name="ソースID")
    last_fetched_at = models.DateTimeField(null=True, blank=True, verbose_name="最終取得日時")
    data_hash = models.CharField(max_length=128, blank=True, verbose_name="データハッシュ")
    metadata = models.JSONField(blank=True, null=True, verbose_name="メタデータ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "company_external_source_records"
        verbose_name = "外部データ取得履歴"
        verbose_name_plural = "外部データ取得履歴"
        unique_together = ("company", "field", "source")

    def __str__(self):
        return f"{self.company.name} - {self.field} ({self.source})"


class CompanyReviewBatch(models.Model):
    """レビュー単位（企業ごとの候補を束ねる）"""

    STATUS_PENDING = "pending"
    STATUS_IN_REVIEW = "in_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_PARTIAL = "partial"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_REVIEW, "In Review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_PARTIAL, "Partial"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="review_batches",
        verbose_name="企業",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="ステータス",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_company_review_batches",
        verbose_name="担当者",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "company_review_batches"
        verbose_name = "企業レビュー"
        verbose_name_plural = "企業レビュー"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["company"]),
        ]

    def __str__(self):
        return f"ReviewBatch({self.company.name})"


class CompanyReviewItem(models.Model):
    """レビュー項目（候補ごとの判断内容）"""

    DECISION_PENDING = "pending"
    DECISION_APPROVED = "approved"
    DECISION_REJECTED = "rejected"
    DECISION_UPDATED = "updated"
    DECISION_CHOICES = [
        (DECISION_PENDING, "Pending"),
        (DECISION_APPROVED, "Approved"),
        (DECISION_REJECTED, "Rejected"),
        (DECISION_UPDATED, "Updated"),
    ]

    batch = models.ForeignKey(
        CompanyReviewBatch,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="レビュー",
    )
    candidate = models.ForeignKey(
        CompanyUpdateCandidate,
        on_delete=models.PROTECT,
        related_name="review_items",
        verbose_name="候補",
    )
    field = models.CharField(max_length=100, verbose_name="対象フィールド")
    current_value = models.TextField(blank=True, verbose_name="現在値")
    candidate_value = models.TextField(verbose_name="候補値")
    confidence = models.PositiveSmallIntegerField(default=100, verbose_name="確信度")
    decision = models.CharField(
        max_length=16,
        choices=DECISION_CHOICES,
        default=DECISION_PENDING,
        verbose_name="判断",
    )
    comment = models.TextField(blank=True, verbose_name="コメント")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decided_company_review_items",
        verbose_name="決裁者",
    )
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="判断日時")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = "company_review_items"
        verbose_name = "企業レビュー項目"
        verbose_name_plural = "企業レビュー項目"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["batch"]),
            models.Index(fields=["decision"]),
        ]

    def __str__(self):
        return f"ReviewItem({self.batch_id}, {self.field})"


class CompanyUpdateHistory(models.Model):
    """企業情報更新履歴"""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="update_history",
        verbose_name="企業",
    )
    field = models.CharField(max_length=100, verbose_name="対象フィールド")
    old_value = models.TextField(blank=True, verbose_name="旧値")
    new_value = models.TextField(blank=True, verbose_name="新値")
    source_type = models.CharField(
        max_length=16,
        choices=CompanyUpdateCandidate.SOURCE_CHOICES,
        default=CompanyUpdateCandidate.SOURCE_RULE,
        verbose_name="ソース種別",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_company_updates",
        verbose_name="承認者",
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="承認日時")
    comment = models.TextField(blank=True, verbose_name="コメント")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = "company_update_history"
        verbose_name = "企業更新履歴"
        verbose_name_plural = "企業更新履歴"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "field"]),
        ]
        indexes = [
            models.Index(fields=["company", "field"]),
        ]

    def __str__(self):
        return f"UpdateHistory({self.company.name}, {self.field})"
