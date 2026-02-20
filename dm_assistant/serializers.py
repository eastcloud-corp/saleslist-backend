from rest_framework import serializers


class DmGenerateRequestSerializer(serializers.Serializer):
    """DM生成API リクエスト"""
    client_info = serializers.CharField(required=True, allow_blank=False, help_text="クライアント情報（テキスト）")


class DmGenerateResultSerializer(serializers.Serializer):
    """1件の生成結果"""
    provider = serializers.CharField()
    prompt_type = serializers.CharField()
    message = serializers.CharField()
    error = serializers.CharField(allow_null=True, required=False)


class DmGenerateResponseSerializer(serializers.Serializer):
    """DM生成API レスポンス"""
    results = DmGenerateResultSerializer(many=True)
