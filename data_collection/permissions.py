"""
データ収集API用の権限クラス。
フロントの「管理者」表示（role=admin）と揃え、role='admin' または is_staff を許可する。
"""
from rest_framework.permissions import BasePermission


class IsAdminOrStaffUser(BasePermission):
    """
    管理者（role=admin）または Django の is_staff を許可する。
    設定画面で「管理者」として作成されたユーザーは is_staff=False のことがあるため、
    role も見る。
    """
    message = "このアクションを実行する権限がありません。"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return bool(getattr(request.user, "is_staff", False) or getattr(request.user, "role", None) == "admin")
