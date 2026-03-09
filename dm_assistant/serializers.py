from rest_framework import serializers


class DmGenerateRequestSerializer(serializers.Serializer):
    """DM生成API リクエスト"""
    client_info = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="送信先（DMの送り先）の情報。企業名・担当者・業界・課題など。",
    )
    sender_info = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="自社情報（送信元）。自社の企業名・担当者・提供サービス・強みなど。",
    )
    product_info = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="商材・サービス。内容・価格帯・実績など。",
    )


class DmGenerateResultSerializer(serializers.Serializer):
    """1件の生成結果"""
    provider = serializers.CharField()
    prompt_type = serializers.CharField()
    message = serializers.CharField()
    error = serializers.CharField(allow_null=True, required=False)


class DmGenerateResponseSerializer(serializers.Serializer):
    """DM生成API レスポンス"""
    results = DmGenerateResultSerializer(many=True)
