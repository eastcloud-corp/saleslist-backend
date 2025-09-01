#!/bin/bash

# Django 企業APIテスト（v0レポート解決確認）

BASE_URL="http://localhost:8080/api/v1"
LOG_FILE="../test_results.log"

echo "🏢 Django企業APIテスト開始（v0レポート解決確認）" | tee -a $LOG_FILE
echo "================================" | tee -a $LOG_FILE

# 認証トークン取得
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}')
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ 認証トークン取得失敗" | tee -a $LOG_FILE
    exit 1
fi

# 1. 企業一覧取得テスト
echo "✅ 1. 企業一覧取得テスト" | tee -a $LOG_FILE
COMPANIES_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" $BASE_URL/companies/)

if echo "$COMPANIES_RESPONSE" | grep -q "count\|results"; then
    COMPANY_COUNT=$(echo "$COMPANIES_RESPONSE" | grep -o '"count":[0-9]*' | cut -d':' -f2)
    echo "   ✓ 企業一覧取得成功 (${COMPANY_COUNT}社)" | tee -a $LOG_FILE
else
    echo "   ❌ 企業一覧取得失敗" | tee -a $LOG_FILE
fi

# 2. 企業作成テスト（v0レポート指摘箇所）
echo "✅ 2. 企業作成テスト（v0レポート解決確認）" | tee -a $LOG_FILE
CREATE_RESPONSE=$(curl -s -X POST $BASE_URL/companies/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "v0レポート解決テスト株式会社",
    "industry": "IT・ソフトウェア",
    "employee_count": 100,
    "revenue": 300000000,
    "prefecture": "東京都",
    "city": "新宿区",
    "established_year": 2015,
    "website_url": "https://v0test.com",
    "contact_email": "v0test@test.com",
    "phone": "03-9999-8888"
  }')

if echo "$CREATE_RESPONSE" | grep -q "v0レポート解決テスト株式会社"; then
    COMPANY_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo "   ✓ 企業作成API実装成功（v0レポート問題解決）" | tee -a $LOG_FILE
    echo "   ✓ 作成企業ID: $COMPANY_ID" | tee -a $LOG_FILE
else
    echo "   ❌ 企業作成失敗" | tee -a $LOG_FILE
    echo "   レスポンス: $CREATE_RESPONSE" | tee -a $LOG_FILE
fi

# 3. 企業詳細取得テスト
if [ -n "$COMPANY_ID" ]; then
    echo "✅ 3. 企業詳細取得テスト" | tee -a $LOG_FILE
    DETAIL_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" $BASE_URL/companies/$COMPANY_ID/)
    
    if echo "$DETAIL_RESPONSE" | grep -q "v0レポート解決テスト株式会社"; then
        echo "   ✓ 企業詳細取得成功" | tee -a $LOG_FILE
    else
        echo "   ❌ 企業詳細取得失敗" | tee -a $LOG_FILE
    fi
fi

# 4. 企業検索テスト
echo "✅ 4. 企業検索・フィルタテスト" | tee -a $LOG_FILE
SEARCH_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/companies/?search=v0レポート")

if echo "$SEARCH_RESPONSE" | grep -q "v0レポート解決テスト株式会社"; then
    echo "   ✓ 企業検索機能正常動作" | tee -a $LOG_FILE
else
    echo "   ❌ 企業検索失敗" | tee -a $LOG_FILE
fi

# 5. 企業フィルタテスト  
FILTER_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/companies/?industry=IT・ソフトウェア&employee_min=50")

if echo "$FILTER_RESPONSE" | grep -q "IT・ソフトウェア"; then
    echo "   ✓ 企業フィルタ機能正常動作" | tee -a $LOG_FILE
else
    echo "   ❌ 企業フィルタ失敗" | tee -a $LOG_FILE
fi

echo "" | tee -a $LOG_FILE
echo "🏢 Django企業APIテスト完了（v0レポート問題解決確認）" | tee -a $LOG_FILE
echo "================================" | tee -a $LOG_FILE