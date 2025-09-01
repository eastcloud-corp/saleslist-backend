from django.db import models


class Industry(models.Model):
    """業界マスタ"""
    name = models.CharField(max_length=100, unique=True, verbose_name="業界名")
    display_order = models.IntegerField(default=0, verbose_name="表示順序")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ状態")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'industries'
        verbose_name = "業界"
        verbose_name_plural = "業界"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


class Status(models.Model):
    """ステータスマスタ"""
    CATEGORY_CHOICES = [
        ('company', '企業'),
        ('project', '案件'),
        ('contact', '営業'),
    ]
    
    name = models.CharField(max_length=50, verbose_name="ステータス名")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="カテゴリ")
    display_order = models.IntegerField(default=0, verbose_name="表示順序")
    color_code = models.CharField(max_length=7, blank=True, verbose_name="表示色")
    description = models.TextField(blank=True, verbose_name="ステータス説明")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ状態")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    class Meta:
        db_table = 'statuses'
        verbose_name = "ステータス"
        verbose_name_plural = "ステータス"
        ordering = ['category', 'display_order', 'name']
        unique_together = ['category', 'name']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class Prefecture(models.Model):
    """都道府県マスタ"""
    name = models.CharField(max_length=10, unique=True, verbose_name="都道府県名")
    region = models.CharField(max_length=10, verbose_name="地方区分")
    display_order = models.IntegerField(default=0, verbose_name="表示順序")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ状態")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    class Meta:
        db_table = 'prefectures'
        verbose_name = "都道府県"
        verbose_name_plural = "都道府県"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['region']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name
