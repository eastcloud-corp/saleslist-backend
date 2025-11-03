-- Saleslist 初期データベース設定

-- ユーザー権限設定
ALTER USER saleslist_user CREATEDB;

-- 基本設定
SET TIME ZONE 'Asia/Tokyo';

-- 拡張機能有効化（将来使用予定）
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pg_trgm";
