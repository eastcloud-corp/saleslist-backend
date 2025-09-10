#!/bin/bash

# =============================================================================
# 本番環境疎通テスト - sales-navigator.east-cloud.jp
# お客様環境での動作確認用
# =============================================================================

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 本番環境設定
PROD_DOMAIN="sales-navigator.east-cloud.jp"
PROD_URL="https://${PROD_DOMAIN}"
PROD_IP="153.120.128.27"
TEST_LOG_DIR="/tmp/production_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEST_LOG_DIR"

# テスト結果追跡
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a FAILED_DETAILS=()

print_header() {
    echo -e "${PURPLE}=================================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}=================================================${NC}"
}

print_section() {
    echo -e "\n${CYAN}🔍 $1${NC}"
    echo "----------------------------------------"
}

log_test() {
    local test_name="$1"
    local success="$2"
    local details="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$success" = "true" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "✅ ${GREEN}PASS${NC}: $test_name"
        if [ -n "$details" ]; then
            echo "   $details"
        fi
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "❌ ${RED}FAIL${NC}: $test_name"
        if [ -n "$details" ]; then
            echo "   $details"
            FAILED_DETAILS+=("$test_name: $details")
        fi
    fi
}

# =============================================================================
# テスト実行関数群
# =============================================================================

test_basic_connectivity() {
    print_section "基本接続テスト"
    
    # Frontend接続テスト
    echo "🌐 Frontend接続テスト..."
    if curl -s -I "$PROD_URL" | grep -q "200\|302"; then
        log_test "Frontend接続" "true" "正常レスポンス"
    else
        log_test "Frontend接続" "false" "接続失敗または異常レスポンス"
    fi
    
    # Backend Admin接続テスト
    echo "🔧 Backend Admin接続テスト..."
    admin_status=$(curl -s -I "$PROD_URL/admin/" | head -1)
    if echo "$admin_status" | grep -q "200\|302"; then
        log_test "Backend Admin接続" "true" "$admin_status"
    else
        log_test "Backend Admin接続" "false" "$admin_status"
    fi
    
    # API Base接続テスト
    echo "📡 API Base接続テスト..."
    api_status=$(curl -s -I "$PROD_URL/api/" | head -1)
    if echo "$api_status" | grep -q "200\|404"; then  # 404は正常（エンドポイント一覧がない）
        log_test "API Base接続" "true" "$api_status"
    else
        log_test "API Base接続" "false" "$api_status"
    fi
}

test_authentication() {
    print_section "認証システムテスト"
    
    echo "🔐 管理者認証テスト..."
    auth_response=$(curl -s -X POST "$PROD_URL/api/v1/auth/login/" \
        -H "Content-Type: application/json" \
        -d '{"email": "salesnav_admin@budget-sales.com", "password": "salesnav20250901"}')
    
    if echo "$auth_response" | grep -q "access_token"; then
        log_test "管理者認証" "true" "トークン取得成功"
        
        # 認証トークン取得
        ADMIN_TOKEN=$(echo "$auth_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        
        # 認証ヘッダー作成
        AUTH_HEADER="Authorization: Bearer $ADMIN_TOKEN"
        
        return 0
    else
        log_test "管理者認証" "false" "認証失敗: $auth_response"
        return 1
    fi
}

test_master_data() {
    print_section "マスターデータテスト"
    
    if [ -z "$ADMIN_TOKEN" ]; then
        log_test "マスターデータテスト" "false" "認証トークンなし"
        return 1
    fi
    
    # 各マスターデータの確認
    declare -A master_endpoints=(
        ["進行状況ステータス"]="progress-statuses"
        ["サービス種別"]="service-types"
        ["媒体種別"]="media-types"
        ["定例会議ステータス"]="meeting-statuses"
        ["リスト利用可能性"]="list-availabilities"
        ["リストインポートソース"]="list-import-sources"
    )
    
    local total_master_count=0
    
    for name in "${!master_endpoints[@]}"; do
        endpoint="${master_endpoints[$name]}"
        echo "📊 ${name}データ確認..."
        
        response=$(curl -s -H "$AUTH_HEADER" "$PROD_URL/api/v1/master/${endpoint}/")
        count=$(echo "$response" | grep -o '"id"' | wc -l)
        
        if [ "$count" -gt "0" ]; then
            log_test "${name}マスター" "true" "${count}件"
            total_master_count=$((total_master_count + count))
        else
            log_test "${name}マスター" "false" "データなし (${count}件)"
        fi
    done
    
    # 総合マスターデータ判定
    if [ "$total_master_count" -gt "50" ]; then
        log_test "マスターデータ総合" "true" "合計${total_master_count}件（十分なデータ量）"
    else
        log_test "マスターデータ総合" "false" "合計${total_master_count}件（データ不足）"
    fi
}

test_core_functionality() {
    print_section "核心機能テスト"
    
    if [ -z "$ADMIN_TOKEN" ]; then
        log_test "核心機能テスト" "false" "認証トークンなし"
        return 1
    fi
    
    # プロジェクト一覧API
    echo "📋 プロジェクト一覧API..."
    projects_response=$(curl -s -H "$AUTH_HEADER" "$PROD_URL/api/v1/projects/")
    if echo "$projects_response" | grep -q '\[\]' || echo "$projects_response" | grep -q '"id"'; then
        log_test "プロジェクト一覧API" "true" "正常レスポンス"
    else
        log_test "プロジェクト一覧API" "false" "異常レスポンス"
    fi
    
    # 企業一覧API
    echo "🏢 企業一覧API..."
    companies_response=$(curl -s -H "$AUTH_HEADER" "$PROD_URL/api/v1/companies/")
    if echo "$companies_response" | grep -q '\[\]' || echo "$companies_response" | grep -q '"id"'; then
        log_test "企業一覧API" "true" "正常レスポンス"
    else
        log_test "企業一覧API" "false" "異常レスポンス"
    fi
    
    # 主要ページ表示確認
    echo "📄 主要ページ表示確認..."
    pages=("/login" "/dashboard" "/projects" "/companies")
    
    for page in "${pages[@]}"; do
        page_status=$(curl -s -I "$PROD_URL$page" | head -1)
        if echo "$page_status" | grep -q "200"; then
            log_test "ページ${page}" "true" "$page_status"
        else
            log_test "ページ${page}" "false" "$page_status"
        fi
    done
}

generate_summary() {
    print_header "本番環境疎通テスト結果"
    
    echo -e "${BLUE}実行時刻${NC}: $(date)"
    echo -e "${BLUE}対象環境${NC}: $PROD_URL"
    echo -e "${BLUE}IP直接${NC}: http://$PROD_IP"
    echo ""
    
    echo -e "${BLUE}📊 テスト結果統計${NC}"
    echo "----------------------------------------"
    echo -e "総テスト数: ${TOTAL_TESTS}"
    echo -e "✅ 成功: ${GREEN}${PASSED_TESTS}${NC}"
    echo -e "❌ 失敗: ${RED}${FAILED_TESTS}${NC}"
    
    if [ $TOTAL_TESTS -gt 0 ]; then
        local success_rate=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
        echo -e "🎯 成功率: ${success_rate}%"
    fi
    
    echo ""
    echo -e "${BLUE}🚨 検出された問題${NC}"
    echo "----------------------------------------"
    
    if [ ${#FAILED_DETAILS[@]} -eq 0 ]; then
        echo -e "${GREEN}問題は検出されませんでした${NC}"
    else
        for i in "${!FAILED_DETAILS[@]}"; do
            echo -e "${RED}$((i+1)).${NC} ${FAILED_DETAILS[$i]}"
        done
    fi
    
    echo ""
    echo -e "${BLUE}📄 詳細ログ保存先${NC}: $TEST_LOG_DIR"
    
    # 結果をJSONで保存
    cat > "$TEST_LOG_DIR/test_results.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "target_url": "$PROD_URL",
    "total_tests": $TOTAL_TESTS,
    "passed": $PASSED_TESTS,
    "failed": $FAILED_TESTS,
    "success_rate": $(( TOTAL_TESTS > 0 ? PASSED_TESTS * 100 / TOTAL_TESTS : 0 )),
    "failed_tests": [$(printf '"%s",' "${FAILED_DETAILS[@]}" | sed 's/,$//')],
    "production_ready": $([ $FAILED_TESTS -eq 0 ] && echo "true" || echo "false")
}
EOF
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}🎉 本番環境は正常に動作しています${NC}"
        exit 0
    else
        echo -e "\n${RED}⚠️  本番環境で問題が検出されました。修正が必要です${NC}"
        exit 1
    fi
}

# =============================================================================
# メイン実行
# =============================================================================

main() {
    print_header "本番環境疎通テスト実行"
    
    echo -e "${CYAN}🚀 本番環境の動作確認を開始します...${NC}"
    echo -e "対象: $PROD_URL"
    echo ""
    
    # 各テストカテゴリ実行
    test_basic_connectivity
    
    # 認証成功時のみ続行
    if test_authentication; then
        test_master_data
        test_core_functionality
    fi
    
    # 結果サマリー生成
    generate_summary
}

# スクリプト実行
main "$@"