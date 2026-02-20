from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import DmGenerateRequestSerializer
from .services.generators import generate_dm_messages, GenerationResult


class DmGenerateView(APIView):
    """
    DM作成補助: クライアント情報をもとに、GPT・Gemini で4つのメッセージを並列生成する。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DmGenerateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        client_info = serializer.validated_data["client_info"]
        results = generate_dm_messages(client_info)

        response_data = {
            "results": [
                {
                    "provider": r.provider,
                    "prompt_type": r.prompt_type,
                    "message": r.message,
                    "error": r.error,
                }
                for r in results
            ]
        }
        return Response(response_data, status=status.HTTP_200_OK)
