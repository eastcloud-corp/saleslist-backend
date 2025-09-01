#!/bin/bash

# Django 認証APIテスト

BASE_URL="http://localhost:8080/api/v1"
LOG_FILE="../test_results.log"

echo "🔐 Django認証APIテスト開始" | tee -a $LOG_FILE
echo "================================" | tee -a $LOG_FILE

# 1. ログインテスト
echo "✅ 1. ログインテスト" | tee -a $LOG_FILE
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}')

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo "   ✓ ログイン成功" | tee -a $LOG_FILE
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo "   ✓ トークン取得: ${ACCESS_TOKEN:0:20}..." | tee -a $LOG_FILE
else
    echo "   ❌ ログイン失敗" | tee -a $LOG_FILE
    echo "   レスポンス: $LOGIN_RESPONSE" | tee -a $LOG_FILE
    exit 1
fi

# 2. ユーザー情報取得テスト（v0レポート解決確認）
echo "✅ 2. ユーザー情報取得テスト（v0レポート解決）" | tee -a $LOG_FILE
ME_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" $BASE_URL/auth/me)

if echo "$ME_RESPONSE" | grep -q "user@example.com"; then
    echo "   ✓ /auth/me API正常動作（モックユーザー問題解決）" | tee -a $LOG_FILE
    USER_NAME=$(echo "$ME_RESPONSE" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    echo "   ✓ ユーザー: $USER_NAME" | tee -a $LOG_FILE
else
    echo "   ❌ ユーザー情報取得失敗" | tee -a $LOG_FILE
    echo "   レスポンス: $ME_RESPONSE" | tee -a $LOG_FILE
fi

# 3. 不正ログインテスト
echo "✅ 3. 不正ログインテスト" | tee -a $LOG_FILE
INVALID_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"invalid@example.com","password":"wrongpassword"}')

if echo "$INVALID_RESPONSE" | grep -q "error\|non_field_errors\|間違っています"; then
    echo "   ✓ 不正ログイン正しく拒否" | tee -a $LOG_FILE
else
    echo "   ❌ 不正ログインの処理に問題" | tee -a $LOG_FILE
fi

# 4. 認証なしアクセステスト
echo "✅ 4. 認証なしアクセステスト" | tee -a $LOG_FILE
UNAUTH_RESPONSE=$(curl -s $BASE_URL/auth/me)

if echo "$UNAUTH_RESPONSE" | grep -q "Authentication credentials were not provided\|detail"; then
    echo "   ✓ 認証なしアクセス正しく拒否" | tee -a $LOG_FILE
else
    echo "   ❌ 認証制御に問題" | tee -a $LOG_FILE
    echo "   レスポンス: $UNAUTH_RESPONSE" | tee -a $LOG_FILE
fi

echo "" | tee -a $LOG_FILE
echo "🔐 Django認証APIテスト完了" | tee -a $LOG_FILE
echo "================================" | tee -a $LOG_FILE