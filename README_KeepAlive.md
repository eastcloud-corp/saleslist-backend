# Keep-Alive サービス

Renderの無料プランでモックAPIをスリープさせないためのサービスです。

## 使用方法

### Windows
```bash
# Node.jsで直接実行
node keep-alive.js

# またはバッチファイルで実行
keep-alive.bat
```

### Linux/Mac
```bash
# Node.jsで直接実行
node keep-alive.js

# またはシェルスクリプトで実行
./keep-alive.sh
```

## 動作内容

- **対象URL**: https://saleslist-mock-api.onrender.com/auth/login
- **ping間隔**: 10分（600秒）
- **動作**: 認証APIへのPOSTリクエストを定期送信
- **ログ**: ping結果とAPI応答をコンソールに表示

## 出力例

```
[2025-08-21T03:30:00.000Z] 🚀 Keep-alive service starting...
[2025-08-21T03:30:00.000Z] 🎯 Target URL: https://saleslist-mock-api.onrender.com/auth/login
[2025-08-21T03:30:00.000Z] ⏱️ Ping interval: 10 minutes

[2025-08-21T03:30:01.000Z] Sending ping to API...
[2025-08-21T03:30:02.500Z] ✅ Ping successful (Status: 200)
[2025-08-21T03:30:02.500Z] 🔐 Authentication successful
[2025-08-21T03:30:02.500Z] ⏰ Next ping scheduled for: 8/21/2025, 3:40:02 AM
```

## 停止方法

`Ctrl+C` でサービスを停止できます。

## 注意事項

- Node.jsが必要です
- インターネット接続が必要です
- PCをスリープ/シャットダウンするとサービスも停止します
- Renderの月間制限（750時間）にご注意ください

## トラブルシューティング

### DNS lookup failed
- インターネット接続を確認してください

### Connection refused
- RenderのAPIが停止している可能性があります
- Renderダッシュボードでサービス状態を確認してください

### Request timed out
- APIの応答が遅い可能性があります
- しばらく待ってから再試行してください