#!/bin/bash

# APIテストスクリプト
# すべてのAPIエンドポイントをテストする

BASE_URL="http://localhost:4010"
TOKEN=""

# 色付きの出力用
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# テスト結果を格納する配列
declare -a TEST_RESULTS=()
PASS_COUNT=0
FAIL_COUNT=0

# テスト関数
test_api() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local expected_status=$5
    
    echo -e "\n${YELLOW}Testing: $description${NC}"
    echo "Method: $method"
    echo "Endpoint: $endpoint"
    
    # cURLコマンドを構築
    if [ "$method" == "GET" ] || [ "$method" == "DELETE" ]; then
        if [ -n "$TOKEN" ]; then
            response=$(curl -s -w "\n%{http_code}" -X $method \
                -H "Authorization: Bearer $TOKEN" \
                "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" -X $method \
                "$BASE_URL$endpoint")
        fi
    else
        if [ -n "$TOKEN" ]; then
            response=$(curl -s -w "\n%{http_code}" -X $method \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $TOKEN" \
                -d "$data" \
                "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" -X $method \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$endpoint")
        fi
    fi
    
    # ステータスコードを抽出
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    # 結果を確認
    if [ "$http_code" == "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} - Status: $http_code"
        TEST_RESULTS+=("✓ $description")
        ((PASS_COUNT++))
    else
        echo -e "${RED}✗ FAILED${NC} - Expected: $expected_status, Got: $http_code"
        TEST_RESULTS+=("✗ $description (Expected: $expected_status, Got: $http_code)")
        ((FAIL_COUNT++))
    fi
    
    # レスポンスボディの一部を表示
    if [ -n "$body" ]; then
        echo "Response (first 200 chars): ${body:0:200}..."
    fi
}

echo "========================================="
echo "     API Endpoint Test Suite"
echo "========================================="

# Phase 1: 認証API
echo -e "\n${YELLOW}=== Phase 1: Authentication APIs ===${NC}"

test_api "POST" "/auth/login" "Login" \
    '{"email":"user@example.com","password":"password123"}' "200"

# トークンを取得（実際のレスポンスから抽出する必要がある場合）
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

test_api "POST" "/auth/refresh" "Refresh Token" \
    '{"refresh_token":"refresh_token_here"}' "200"

test_api "POST" "/auth/logout" "Logout" "" "200"

# Phase 2: マスターデータAPI
echo -e "\n${YELLOW}=== Phase 2: Master Data APIs ===${NC}"

test_api "GET" "/master/industries" "Get Industries" "" "200"
test_api "GET" "/master/prefectures" "Get Prefectures" "" "200"
test_api "GET" "/master/statuses" "Get Statuses" "" "200"

# Phase 3: クライアント管理API
echo -e "\n${YELLOW}=== Phase 3: Client Management APIs ===${NC}"

test_api "GET" "/clients" "Get Clients List" "" "200"
test_api "POST" "/clients" "Create Client" \
    '{"name":"テスト株式会社","industry":"IT","contact_email":"test@example.com"}' "201"
test_api "GET" "/clients/1" "Get Client Details" "" "200"
test_api "PUT" "/clients/1" "Update Client" \
    '{"name":"更新テスト株式会社","industry":"IT","contact_email":"update@example.com"}' "200"
test_api "GET" "/clients/1/projects" "Get Client Projects" "" "200"
test_api "GET" "/clients/1/stats" "Get Client Stats" "" "200"

# Phase 4: NG リスト管理API
echo -e "\n${YELLOW}=== Phase 4: NG List Management APIs ===${NC}"

test_api "GET" "/clients/1/ng-companies" "Get Client NG Companies" "" "200"
test_api "POST" "/clients/1/ng-companies" "Add NG Company" \
    '{"company_name":"NG企業株式会社","reason":"取引停止"}' "201"
test_api "POST" "/clients/1/ng-companies/import" "Import NG Companies CSV" \
    '{"csv_data":"company_name\nNG企業1\nNG企業2"}' "200"
test_api "DELETE" "/clients/1/ng-companies/1" "Delete NG Company" "" "204"
test_api "GET" "/ng-companies/template" "Get CSV Template" "" "200"
test_api "POST" "/ng-companies/match" "Match NG Companies" \
    '{"client_id":1}' "200"
test_api "GET" "/clients/1/available-companies" "Get Available Companies" "" "200"

# Phase 5: 企業管理API
echo -e "\n${YELLOW}=== Phase 5: Company Management APIs ===${NC}"

test_api "GET" "/companies" "Get Companies List" "" "200"
test_api "POST" "/companies" "Create Company" \
    '{"name":"新規企業株式会社","industry":"製造業","employee_count":100}' "201"
test_api "GET" "/companies/1" "Get Company Details" "" "200"
test_api "PUT" "/companies/1" "Update Company" \
    '{"name":"更新企業株式会社","industry":"製造業","employee_count":150}' "200"
test_api "PATCH" "/companies/1" "Patch Company" \
    '{"employee_count":200}' "200"
test_api "POST" "/companies/1/toggle_ng" "Toggle NG Status" "" "200"
test_api "POST" "/companies/import_csv" "Import Companies CSV" \
    '{"csv_data":"name,industry,employee_count\n企業A,IT,50\n企業B,製造,100"}' "200"
test_api "GET" "/companies/export_csv" "Export Companies CSV" "" "200"

# Phase 6: 役員管理API
echo -e "\n${YELLOW}=== Phase 6: Executive Management APIs ===${NC}"

test_api "GET" "/companies/1/executives" "Get Company Executives" "" "200"
test_api "POST" "/companies/1/executives" "Create Executive" \
    '{"name":"山田太郎","position":"代表取締役"}' "201"
test_api "PUT" "/executives/1" "Update Executive" \
    '{"name":"山田太郎","position":"CEO"}' "200"
test_api "PATCH" "/executives/1" "Patch Executive" \
    '{"position":"会長"}' "200"
test_api "DELETE" "/executives/1" "Delete Executive" "" "204"

# Phase 7: プロジェクト管理API
echo -e "\n${YELLOW}=== Phase 7: Project Management APIs ===${NC}"

test_api "GET" "/projects" "Get Projects List" "" "200"
test_api "POST" "/projects" "Create Project" \
    '{"name":"新規プロジェクト","client_id":1,"status":"active"}' "201"
test_api "GET" "/projects/1" "Get Project Details" "" "200"
test_api "PUT" "/projects/1" "Update Project" \
    '{"name":"更新プロジェクト","client_id":1,"status":"active"}' "200"
test_api "PATCH" "/projects/1" "Patch Project" \
    '{"status":"completed"}' "200"
test_api "POST" "/projects/1/add-companies" "Add Companies to Project" \
    '{"company_ids":[1,2,3]}' "200"
test_api "GET" "/projects/1/available-companies" "Get Available Companies for Project" "" "200"
test_api "GET" "/projects/1/companies" "Get Project Companies" "" "200"
test_api "PATCH" "/projects/1/companies/1" "Update Company Status in Project" \
    '{"status":"contacted"}' "200"
test_api "DELETE" "/projects/1/companies/1" "Remove Company from Project" "" "204"
test_api "POST" "/projects/1/bulk_update_status" "Bulk Update Status" \
    '{"company_ids":[2,3],"status":"contacted"}' "200"
test_api "POST" "/projects/1/ng_companies" "Add Project NG Company" \
    '{"company_id":4,"reason":"プロジェクト対象外"}' "201"
test_api "GET" "/projects/1/export_csv" "Export Project CSV" "" "200"

# Phase 8: フィルタ管理API
echo -e "\n${YELLOW}=== Phase 8: Filter Management APIs ===${NC}"

test_api "GET" "/saved_filters" "Get Saved Filters" "" "200"
test_api "POST" "/saved_filters" "Create Filter" \
    '{"name":"IT企業フィルタ","filters":{"industry":"IT"}}' "201"
test_api "DELETE" "/saved_filters/1" "Delete Filter" "" "204"

# テスト結果のサマリー
echo -e "\n========================================="
echo -e "           TEST SUMMARY"
echo -e "========================================="
echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo -e "\nDetailed Results:"
for result in "${TEST_RESULTS[@]}"; do
    echo "$result"
done

# 終了コード
if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi