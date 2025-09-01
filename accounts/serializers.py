from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class LoginSerializer(serializers.Serializer):
    """ログイン用シリアライザー"""
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                if user.is_active:
                    data['user'] = user
                    return data
                else:
                    raise serializers.ValidationError('このアカウントは無効化されています。')
            else:
                raise serializers.ValidationError('メールアドレスまたはパスワードが間違っています。')
        else:
            raise serializers.ValidationError('メールアドレスとパスワードの両方を入力してください。')


class UserProfileSerializer(serializers.ModelSerializer):
    """ユーザープロフィール用シリアライザー"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'role', 'is_active',
            'last_login_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """ユーザー作成用シリアライザー"""
    password = serializers.CharField(max_length=128, write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'role']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data.get('email')
        name = validated_data.get('name')
        role = validated_data.get('role', 'user')
        
        # usernameとしてemailを使用（カスタムUserモデルのUSERNAME_FIELD='email'対応）
        user = User.objects.create_user(
            username=email,  # Django要求
            email=email,
            name=name,
            role=role,
            password=password
        )
        return user