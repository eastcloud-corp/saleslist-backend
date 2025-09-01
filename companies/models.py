from django.db import models


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
        ]

    def __str__(self):
        return self.name


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
