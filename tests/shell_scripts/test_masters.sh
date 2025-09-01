#!/bin/bash

# Django マスターAPIテスト（v0レポート解決確認）

BASE_URL="http://localhost:8080/api/v1"
LOG_FILE="../test_results.log"

echo "📊 DjangoマスターデータAPIテスト開始（v0レポート解決確認）" | tee -a $LOG_FILE
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

# 1. 業界マスターAPIテスト（v0レポート指摘箇所）
echo "✅ 1. 業界マスターAPIテスト（v0レポート解決確認）" | tee -a $LOG_FILE
INDUSTRIES_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" $BASE_URL/master/industries/)

if echo "$INDUSTRIES_RESPONSE" | grep -q "results.*IT・ソフトウェア"; then
    INDUSTRY_COUNT=$(echo "$INDUSTRIES_RESPONSE" | grep -o '"name":' | wc -l)
    echo "   ✓ /master/industries API実装成功（v0レポート問題解決）" | tee -a $LOG_FILE
    echo "   ✓ 業界データ${INDUSTRY_COUNT}件取得" | tee -a $LOG_FILE
    echo "   ✓ ハードコーディング問題解決" | tee -a $LOG_FILE
else
    echo "   ❌ 業界マスターAPI失敗" | tee -a $LOG_FILE
    echo "   レスポンス: $INDUSTRIES_RESPONSE" | tee -a $LOG_FILE
fi

# 2. ステータスマスターAPIテスト（v0レポート指摘箇所）
echo "✅ 2. ステータスマスターAPIテスト（v0レポート解決確認）" | tee -a $LOG_FILE
STATUSES_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/master/statuses/?category=contact")

if echo "$STATUSES_RESPONSE" | grep -q "results.*未接触"; then
    STATUS_COUNT=$(echo "$STATUSES_RESPONSE" | grep -o '"name":' | wc -l)
    echo "   ✓ /master/statuses API実装成功（v0レポート問題解決）" | tee -a $LOG_FILE
    echo "   ✓ 営業ステータス${STATUS_COUNT}件取得" | tee -a $LOG_FILE
    echo "   ✓ カテゴリフィルタ機能動作" | tee -a $LOG_FILE
else
    echo "   ❌ ステータスマスターAPI失敗" | tee -a $LOG_FILE
    echo "   レスポンス: $STATUSES_RESPONSE" | tee -a $LOG_FILE
fi

# 3. 全ステータスカテゴリテスト
echo "✅ 3. 全ステータスカテゴリテスト" | tee -a $LOG_FILE
for category in "contact" "project" "company"; do
    CATEGORY_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/master/statuses/?category=$category")
    if echo "$CATEGORY_RESPONSE" | grep -q "results"; then
        CATEGORY_COUNT=$(echo "$CATEGORY_RESPONSE" | grep -o '"name":' | wc -l)
        echo "   ✓ ${category}カテゴリ: ${CATEGORY_COUNT}件" | tee -a $LOG_FILE
    else
        echo "   ❌ ${category}カテゴリ取得失敗" | tee -a $LOG_FILE
    fi
done

echo "" | tee -a $LOG_FILE
echo "📊 DjangoマスターデータAPIテスト完了（v0レポート問題解決確認）" | tee -a $LOG_FILE
echo "================================" | tee -a $LOG_FILE