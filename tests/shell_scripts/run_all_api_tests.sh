#!/bin/bash

# Django API全テスト実行スクリプト

echo "🧪 Django APIテストスイート"
echo "================================================"
echo "開始時刻: $(date)"
echo ""

# ログファイル初期化
LOG_FILE="../test_results.log"
echo "🧪 Django APIテストスイート実行開始 - $(date)" > $LOG_FILE
echo "================================================" >> $LOG_FILE

# Django サーバーが起動しているかチェック
echo "🔍 Django サーバー状態確認中..." | tee -a $LOG_FILE
if curl -s http://localhost:8080/api/v1/auth/login > /dev/null 2>&1; then
    echo "✅ Django サーバー稼働中 (localhost:8080)" | tee -a $LOG_FILE
else
    echo "❌ Django サーバーが応答しません" | tee -a $LOG_FILE
    echo "   サーバーを起動してください:" | tee -a $LOG_FILE
    echo "   cd saleslist-backend && python3 manage.py runserver 8080" | tee -a $LOG_FILE
    exit 1
fi

echo "" | tee -a $LOG_FILE

# 個別テスト実行
echo "🔐 Django認証APIテスト実行中..." | tee -a $LOG_FILE
./test_auth.sh

echo "🏢 Django企業APIテスト実行中..." | tee -a $LOG_FILE  
./test_companies.sh

echo "📊 DjangoマスターAPIテスト実行中..." | tee -a $LOG_FILE
./test_masters.sh

# Python包括テスト
echo "🐍 Python包括APIテスト実行中..." | tee -a $LOG_FILE
python3 ../integration/test_comprehensive_api.py

# 結果サマリー
echo "" | tee -a $LOG_FILE
echo "================================================" | tee -a $LOG_FILE
echo "🏁 Django APIテスト完了 - $(date)" | tee -a $LOG_FILE

# ログファイル表示
echo ""
echo "📄 詳細ログ: tests/$LOG_FILE"
echo ""
echo "主要テスト結果:"
grep -E "(✅|❌)" $LOG_FILE | tail -10