from django.db import models


class Client(models.Model):
    """顧客マスタ（営業代行の依頼元企業）"""
    name = models.CharField(max_length=255, verbose_name="顧客企業名")
    company_type = models.CharField(max_length=50, blank=True, verbose_name="企業タイプ")
    industry = models.CharField(max_length=100, blank=True, verbose_name="顧客の業界")
    
    # 連絡先情報
    contact_person = models.CharField(max_length=100, blank=True, verbose_name="担当者名")
    contact_person_position = models.CharField(max_length=100, blank=True, verbose_name="担当者役職")
    contact_email = models.EmailField(blank=True, verbose_name="連絡先メール")
    contact_phone = models.CharField(max_length=50, blank=True, verbose_name="連絡先電話")
    address = models.TextField(blank=True, verbose_name="住所")
    website = models.URLField(blank=True, verbose_name="ウェブサイト")
    notes = models.TextField(blank=True, verbose_name="備考")
    
    # 企業情報
    facebook_url = models.URLField(max_length=500, blank=True, verbose_name="Facebookリンク")
    employee_count = models.IntegerField(null=True, blank=True, verbose_name="従業員数")
    revenue = models.BigIntegerField(null=True, blank=True, verbose_name="売上規模")
    prefecture = models.CharField(max_length=10, blank=True, verbose_name="都道府県")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ状態")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'clients'
        verbose_name = "クライアント"
        verbose_name_plural = "クライアント"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['industry']),
        ]

    def __str__(self):
        return self.name


class ClientNGCompany(models.Model):
    """クライアント単位のNG企業設定"""
    client = models.ForeignKey(
        'Client', 
        on_delete=models.CASCADE, 
        related_name='ng_companies',
        verbose_name="クライアント"
    )
    company_name = models.CharField(max_length=255, verbose_name="企業名")
    company = models.ForeignKey(
        'companies.Company', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="マッチした企業"
    )
    matched = models.BooleanField(default=False, verbose_name="マッチ状態")
    reason = models.TextField(blank=True, verbose_name="NG理由")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ状態")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'client_ng_companies'
        verbose_name = "クライアントNG企業"
        verbose_name_plural = "クライアントNG企業"
        unique_together = ['client', 'company_name']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['company_name']),
            models.Index(fields=['company']),
            models.Index(fields=['matched']),
        ]

    def __str__(self):
        return f"{self.client.name} - {self.company_name}"
