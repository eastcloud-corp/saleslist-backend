from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """カスタムユーザーモデル"""
    email = models.EmailField(unique=True, verbose_name="メールアドレス")
    name = models.CharField(max_length=100, verbose_name="ユーザー名")
    role = models.CharField(
        max_length=20, 
        choices=[('admin', '管理者'), ('user', '一般ユーザー')],
        default='user',
        verbose_name="権限レベル"
    )
    is_active = models.BooleanField(default=True, verbose_name="アクティブ状態")
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name="最終ログイン日時")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_login_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.email})"
