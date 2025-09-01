# さくらapp run デプロイガイド

ソーシャルナビゲーターの本番デプロイ手順です。

## 🏗️ デプロイ構成

### **App Run #1: social-navigator-database**
```
コンテナ名: social-navigator-database
ポート: 5432
環境変数:
  POSTGRES_DB=social_navigator
  POSTGRES_USER=social_navigator_user
  POSTGRES_PASSWORD=[本番用パスワード]
```

### **App Run #2: social-navigator-backend** 
```
コンテナ名: social-navigator-backend
ポート: 8000
環境変数:
  DATABASE_URL=postgresql://social_navigator_user:[PASSWORD]@[DB_HOST]:5432/social_navigator
  DEBUG=False
  SECRET_KEY=[本番用シークレットキー]
  ALLOWED_HOSTS=*.app-run.sakura.ne.jp,your-domain.com
```

### **App Run #3: social-navigator-frontend**
```
コンテナ名: social-navigator-frontend
ポート: 3000
環境変数:
  NEXT_PUBLIC_API_BASE_URL=https://[BACKEND_URL]/api/v1
  NODE_ENV=production
```

## 📋 デプロイ手順

### Step 1: データベース作成
1. さくらapp runでPostgreSQLコンテナデプロイ
2. 外部接続用URLを取得: `postgresql://...@xxx.app-run.sakura.ne.jp:5432/social_navigator`

### Step 2: バックエンドデプロイ
1. Django設定で本番環境変数設定
2. DockerfileでGunicorn起動
3. マイグレーション・初期データ投入

### Step 3: フロントエンドデプロイ
1. Next.js本番ビルド
2. バックエンドURLを環境変数で設定
3. Dockerfileでサーバー起動

## 🔧 本番用設定

### Django本番設定 (settings.py)
```python
# 本番環境設定
DEBUG = False
ALLOWED_HOSTS = [
    'your-backend.app-run.sakura.ne.jp',
    'your-domain.com'
]

# セキュリティ設定
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# CORS設定（本番フロントエンドURL）
CORS_ALLOWED_ORIGINS = [
    "https://your-frontend.app-run.sakura.ne.jp",
    "https://your-domain.com"
]
```

## 💰 想定コスト

```
App Run #1 (DB):       550円/月〜
App Run #2 (API):      550円/月〜  
App Run #3 (Frontend): 550円/月〜
合計:                  1,650円/月〜
```

## 🚀 キャッシュ戦略

### Phase 1: DatabaseCache（リリース用）
- PostgreSQL内蔵キャッシュ使用
- 追加コストなし
- 中小規模なら十分

### Phase 2: Redis追加（運用改善時）
- App Run #4でRedis追加
- 月550円追加でパフォーマンス大幅向上

## ⚡ さくらクラウド最適化

### **さくらの利点活用**
- ✅ **国内データセンター**: 低遅延
- ✅ **日本語サポート**: トラブル時安心
- ✅ **統一請求**: コスト管理簡単
- ✅ **ネットワーク最適化**: app run間高速接続

### **推奨設定**
- **ヘルスチェック**: 各コンテナで適切設定
- **ログ監視**: さくらの監視機能活用
- **バックアップ**: PostgreSQLの定期バックアップ設定