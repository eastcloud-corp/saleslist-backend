-- ソーシャルナビゲーター初期データベース設定

-- データベース作成（既に作成済みだが念のため）
-- CREATE DATABASE social_navigator;

-- ユーザー権限設定
ALTER USER social_navigator_user CREATEDB;

-- 基本設定
SET TIME ZONE 'Asia/Tokyo';

-- 拡張機能有効化（将来使用予定）
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pg_trgm";