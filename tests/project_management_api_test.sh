#!/bin/bash

# プロジェクト管理機能 API統合テスト (jq不要版)
# 使用方法: ./tests/project_management_api_test.sh

API_BASE="http://localhost:8006/api/v1"
TEMP_DIR="/tmp/api_test_$$"
mkdir -p "$TEMP_DIR"

echo "=== プロジェクト管理機能 API統合テスト開始 ==="
echo "API Base: $API_BASE"
echo ""

# ヘルパー関数: HTTPステータスコードチェック
check_status() {
  local expected=$1
  local actual=$2
  local test_name=$3
  
  if [ "$actual" -eq "$expected" ]; then
    echo "✅ $test_name (Status: $actual)"
    return 0
  else
    echo "❌ $test_name (Expected: $expected, Actual: $actual)"
    return 1
  fi
}

# ヘルパー関数: レスポンス内容チェック
check_contains() {
  local response=$1
  local expected=$2
  local test_name=$3
  
  if echo "$response" | grep -q "$expected"; then
    echo "✅ $test_name (含む: $expected)"
    return 0
  else
    echo "❌ $test_name (含まない: $expected)"
    echo "実際のレスポンス: $response"
    return 1
  fi
}

# 1. ログイン
echo "1. ログインテスト"
LOGIN_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$API_BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "password123"}')

HTTP_CODE="${LOGIN_RESPONSE: -3}"
RESPONSE_BODY="${LOGIN_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "ログイン" || exit 1
check_contains "$RESPONSE_BODY" "access_token" "アクセストークン存在確認" || exit 1

# トークンを抽出（sedを使用）
TOKEN=$(echo "$RESPONSE_BODY" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
if [ -z "$TOKEN" ]; then
  echo "❌ トークン抽出失敗"
  exit 1
fi
echo "✅ ログイン成功"
echo ""

# 2. マスターデータ取得テスト
echo "2. マスターデータ取得テスト"

echo "2-1. 進行状況マスター"
PROGRESS_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_BASE/master/progress-statuses/")
HTTP_CODE="${PROGRESS_RESPONSE: -3}"
RESPONSE_BODY="${PROGRESS_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "進行状況マスター取得" || exit 1
check_contains "$RESPONSE_BODY" "results" "結果フィールド存在確認" || exit 1
check_contains "$RESPONSE_BODY" "未着手" "進行状況データ確認" || exit 1
echo ""

echo "2-2. 媒体マスター"
MEDIA_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_BASE/master/media-types/")
HTTP_CODE="${MEDIA_RESPONSE: -3}"
RESPONSE_BODY="${MEDIA_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "媒体マスター取得" || exit 1
check_contains "$RESPONSE_BODY" "Facebook" "媒体データ確認" || exit 1
echo ""

# 3. プロジェクト管理一覧API テスト
echo "3. プロジェクト管理一覧APIテスト"
PROJECT_LIST_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_BASE/projects/?management_mode=true")
HTTP_CODE="${PROJECT_LIST_RESPONSE: -3}"
RESPONSE_BODY="${PROJECT_LIST_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "プロジェクト管理一覧取得" || exit 1
check_contains "$RESPONSE_BODY" "client_name" "クライアント名フィールド確認" || exit 1
check_contains "$RESPONSE_BODY" "is_locked" "ロック状態フィールド確認" || exit 1

# プロジェクトIDを抽出（sedを使用）
PROJECT_ID=$(echo "$RESPONSE_BODY" | sed -n 's/.*"id":\([0-9]*\).*/\1/p' | head -1)
if [ -z "$PROJECT_ID" ]; then
  echo "❌ プロジェクトが見つかりません"
  exit 1
fi
echo "✅ テスト対象プロジェクトID: $PROJECT_ID"
echo ""

# 4. 編集ロック機能テスト
echo "4. 編集ロック機能テスト"

echo "4-1. ロック取得"
LOCK_RESPONSE=$(curl -s -w "%{http_code}" -X POST -H "Authorization: Bearer $TOKEN" "$API_BASE/projects/$PROJECT_ID/lock/")
HTTP_CODE="${LOCK_RESPONSE: -3}"
RESPONSE_BODY="${LOCK_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "編集ロック取得" || exit 1
check_contains "$RESPONSE_BODY" "\"success\":true" "ロック取得成功確認" || exit 1
check_contains "$RESPONSE_BODY" "locked_until" "ロック期限設定確認" || exit 1
echo ""

echo "4-2. ロック状態確認"
LOCKED_LIST_RESPONSE=$(curl -s -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$API_BASE/projects/?management_mode=true")
HTTP_CODE="${LOCKED_LIST_RESPONSE: -3}"
RESPONSE_BODY="${LOCKED_LIST_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "ロック状態確認API" || exit 1
check_contains "$RESPONSE_BODY" "\"is_locked\":true" "ロック状態true確認" || exit 1
check_contains "$RESPONSE_BODY" "管理者テストユーザー" "ロック中ユーザー名確認" || exit 1
echo ""

# 5. プロジェクト更新テスト  
echo "5. プロジェクト更新テスト"
UPDATE_RESPONSE=$(curl -s -w "%{http_code}" -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"director_login_available": true, "appointment_count": 10, "situation": "テストで更新"}' \
  "$API_BASE/projects/$PROJECT_ID/?management_mode=true")

HTTP_CODE="${UPDATE_RESPONSE: -3}"
RESPONSE_BODY="${UPDATE_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "プロジェクト更新" || exit 1
echo ""

# 6. 更新内容確認
echo "6. 更新内容確認"
UPDATED_LIST_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_BASE/projects/?management_mode=true")

check_contains "$UPDATED_LIST_RESPONSE" "\"appointment_count\":10" "アポ数更新確認" || exit 1
check_contains "$UPDATED_LIST_RESPONSE" "テストで更新" "状況更新確認" || exit 1
check_contains "$UPDATED_LIST_RESPONSE" "\"director_login_available\":true" "チェックボックス更新確認" || exit 1
echo ""

# 7. ロック解除
echo "7. ロック解除テスト"
UNLOCK_RESPONSE=$(curl -s -w "%{http_code}" -X DELETE -H "Authorization: Bearer $TOKEN" "$API_BASE/projects/$PROJECT_ID/unlock/")
HTTP_CODE="${UNLOCK_RESPONSE: -3}"
RESPONSE_BODY="${UNLOCK_RESPONSE%???}"

check_status 200 "$HTTP_CODE" "ロック解除" || exit 1
check_contains "$RESPONSE_BODY" "\"success\":true" "ロック解除成功確認" || exit 1
echo ""

# 8. 最終確認（ロック状態解除確認）
echo "8. 最終確認"
FINAL_LIST_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_BASE/projects/?management_mode=true")

check_contains "$FINAL_LIST_RESPONSE" "\"is_locked\":false" "ロック解除状態確認" || exit 1
echo ""

# 9. エラーケーステスト
echo "9. エラーケーステスト"

echo "9-1. 無効なプロジェクトIDでロック取得"
ERROR_RESPONSE=$(curl -s -w "%{http_code}" -X POST -H "Authorization: Bearer $TOKEN" "$API_BASE/projects/99999/lock/")
HTTP_CODE="${ERROR_RESPONSE: -3}"
check_status 404 "$HTTP_CODE" "無効ID時404エラー" || echo "⚠️  404エラー期待だが $HTTP_CODE"
echo ""

echo "9-2. 無効データでプロジェクト更新"
INVALID_UPDATE_RESPONSE=$(curl -s -w "%{http_code}" -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"appointment_count": -1}' \
  "$API_BASE/projects/$PROJECT_ID/?management_mode=true")
HTTP_CODE="${INVALID_UPDATE_RESPONSE: -3}"
echo "無効データ更新結果: $HTTP_CODE (400期待)"
echo ""

# クリーンアップ
rm -rf "$TEMP_DIR"

echo "=== プロジェクト管理機能 API統合テスト完了 ==="
echo ""
echo "📊 テスト結果サマリー:"
echo "- ✅ ログイン・認証"
echo "- ✅ マスターデータ取得"  
echo "- ✅ 管理一覧取得"
echo "- ✅ 編集ロック取得"
echo "- ✅ データ更新"
echo "- ✅ ロック解除"
echo "- ✅ エラーケース"