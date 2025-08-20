const https = require('https');

// 設定
const API_URL = 'https://saleslist-mock-api.onrender.com/companies';
const INTERVAL = 10 * 60 * 1000; // 10分（600秒）

// ログ出力用の関数
function log(message) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${message}`);
}

// API pingを送信する関数
function pingAPI() {
  log('Sending ping to API...');
  
  https.get(API_URL, (res) => {
    let data = '';
    
    res.on('data', (chunk) => {
      data += chunk;
    });
    
    res.on('end', () => {
      if (res.statusCode === 200) {
        log(`✅ Ping successful (Status: ${res.statusCode})`);
        
        // レスポンスがJSONかどうかチェック
        try {
          const jsonData = JSON.parse(data);
          if (jsonData.results && Array.isArray(jsonData.results)) {
            log(`📊 API returned ${jsonData.results.length} companies`);
          }
        } catch (e) {
          log('📄 API returned non-JSON response');
        }
      } else {
        log(`⚠️ Ping returned status ${res.statusCode}`);
      }
    });
    
  }).on('error', (err) => {
    log(`❌ Ping failed: ${err.message}`);
    
    // 接続エラーの場合の詳細情報
    if (err.code === 'ENOTFOUND') {
      log('🔍 DNS lookup failed - check your internet connection');
    } else if (err.code === 'ECONNREFUSED') {
      log('🔍 Connection refused - API might be down');
    } else if (err.code === 'ETIMEDOUT') {
      log('🔍 Request timed out - API might be slow to respond');
    }
  });
}

// 次回ping時刻を表示する関数
function showNextPing() {
  const nextPing = new Date(Date.now() + INTERVAL);
  log(`⏰ Next ping scheduled for: ${nextPing.toLocaleString()}`);
}

// メイン処理
function startKeepAlive() {
  log('🚀 Keep-alive service starting...');
  log(`🎯 Target URL: ${API_URL}`);
  log(`⏱️ Ping interval: ${INTERVAL / 1000 / 60} minutes`);
  log('');
  
  // 即座に1回実行
  pingAPI();
  showNextPing();
  
  // 定期実行を開始
  const intervalId = setInterval(() => {
    pingAPI();
    showNextPing();
  }, INTERVAL);
  
  // Ctrl+Cでの終了処理
  process.on('SIGINT', () => {
    log('');
    log('🛑 Keep-alive service stopping...');
    clearInterval(intervalId);
    log('✅ Service stopped successfully');
    process.exit(0);
  });
  
  log('💡 Press Ctrl+C to stop the service');
  log('');
}

// サービス開始
startKeepAlive();