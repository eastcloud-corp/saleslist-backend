# データベース設計書

## 1. 全体構成

### 1.1 使用DBMS
- **メインDB**: Supabase (PostgreSQL 15+)
- **キャッシュ**: Redis (将来実装)

### 1.2 テーブル一覧
1. **clients** - 顧客マスタ（営業代行の依頼元企業）
2. **companies** - 企業マスタ（営業対象の企業）
3. **executives** - 代表者・役員情報
4. **projects** - 案件マスタ
5. **project_companies** - 案件企業リスト（営業ステータス管理）
6. **project_ng_companies** - 案件NG企業設定
7. **client_ng_companies** - クライアント単位のNG企業設定
8. **ng_import_logs** - NGリストインポート履歴
9. **saved_filters** - 保存済みフィルタ
10. **random_orders** - ランダム表示順序保持

### 1.3 拡張予定テーブル（Phase 3+）
- **tenants** - テナントマスタ（マルチテナント対応）
- **users** - ユーザー管理（権限管理）
- **external_api_logs** - 外部API連携ログ

---

## 2. テーブル詳細設計

### 2.1 clients（顧客マスタ）
```sql
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,           -- 顧客企業名
    company_type VARCHAR(50),             -- 企業タイプ
    industry VARCHAR(100),                -- 顧客の業界
    contact_person VARCHAR(100),          -- 担当者名
    contact_email VARCHAR(255),           -- 連絡先メール
    contact_phone VARCHAR(50),            -- 連絡先電話
    address TEXT,                         -- 住所
    website VARCHAR(255),                 -- ウェブサイト
    notes TEXT,                           -- 備考
    is_active BOOLEAN DEFAULT TRUE,       -- アクティブ状態
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_clients_name ON clients(name);
CREATE INDEX idx_clients_is_active ON clients(is_active);
CREATE INDEX idx_clients_industry ON clients(industry);
```

**説明**
- バジェットアドテクノロジーの顧客（営業代行を依頼する企業）を管理
- 1顧客から複数の案件を受注する可能性がある（1:N関係）
- クライアント中心のビジネスフローの起点となるテーブル

### 2.2 companies（企業マスタ）
```sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    employee_count INTEGER,
    revenue BIGINT,                    -- 売上高（円）
    prefecture VARCHAR(10),
    city VARCHAR(100),
    established_year INTEGER,
    website_url VARCHAR(500),
    contact_email VARCHAR(255),
    phone VARCHAR(20),
    notes TEXT,
    is_global_ng BOOLEAN DEFAULT FALSE,  -- グローバルNG設定
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_companies_prefecture ON companies(prefecture);
CREATE INDEX idx_companies_employee_count ON companies(employee_count);
CREATE INDEX idx_companies_is_global_ng ON companies(is_global_ng);
CREATE INDEX idx_companies_created_at ON companies(created_at);
```

**説明**
- 企業の基本情報を管理
- `is_global_ng`: 全案件で除外する企業フラグ
- 検索頻度が高い項目にインデックスを設定

### 2.2 executives（代表者・役員情報）
```sql
CREATE TABLE executives (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(100),              -- 役職
    facebook_url VARCHAR(500),
    other_sns_url VARCHAR(500),         -- LinkedIn等
    direct_email VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_executives_company_id ON executives(company_id);
CREATE INDEX idx_executives_name ON executives(name);
CREATE INDEX idx_executives_facebook_url ON executives(facebook_url) WHERE facebook_url IS NOT NULL;
```

**説明**
- 企業の代表者・役員情報
- 1企業に複数の役員が紐づく（1:N関係）
- Facebook URLの有無での検索が頻繁なため条件付きインデックス

### 2.4 projects（案件マスタ）
```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    description TEXT,                   -- 案件概要
    manager VARCHAR(100),               -- バジェット側担当者
    target_industry VARCHAR(100),      -- ターゲット業界
    target_company_size VARCHAR(50),   -- ターゲット企業規模
    dm_template TEXT,                   -- DMテンプレート（将来使用）
    status VARCHAR(20) DEFAULT '進行中',  -- 進行中/完了/中止
    start_date DATE,                    -- 開始日
    end_date DATE,                      -- 終了予定日
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_projects_client_id ON projects(client_id);
CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at);
```

**説明**
- 営業案件の基本情報
- 顧客（clients）との関連を持つ
- ターゲット企業の条件も記録

### 2.5 project_companies（案件企業リスト）
```sql
CREATE TABLE project_companies (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT '未接触',    -- 営業ステータス
    contact_date DATE,                      -- 最終接触日
    staff_name VARCHAR(100),                -- 担当者
    notes TEXT,                             -- 個別メモ
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 複合ユニーク制約（同一案件に同一企業は1回のみ）
    UNIQUE(project_id, company_id)
);

-- インデックス
CREATE INDEX idx_project_companies_project_id ON project_companies(project_id);
CREATE INDEX idx_project_companies_company_id ON project_companies(company_id);
CREATE INDEX idx_project_companies_status ON project_companies(status);
CREATE INDEX idx_project_companies_contact_date ON project_companies(contact_date);
```

**営業ステータス一覧**
- `未接触` - 初期状態
- `DM送信予定` - 送信準備中
- `DM送信済み` - 送信完了
- `返信あり` - 相手から返信
- `アポ獲得` - 商談約束
- `成約` - 契約成立
- `NG` - 対応不可・拒否

**説明**
- 案件と企業の多対多関係を管理
- 営業活動の進捗状況を詳細に記録

### 2.6 project_ng_companies（案件NG企業）
```sql
CREATE TABLE project_ng_companies (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    reason TEXT,                            -- NG理由
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 複合ユニーク制約
    UNIQUE(project_id, company_id)
);

-- インデックス
CREATE INDEX idx_project_ng_companies_project_id ON project_ng_companies(project_id);
CREATE INDEX idx_project_ng_companies_company_id ON project_ng_companies(company_id);
```

**説明**
- 案件ごとのNG企業設定
- クライアントから指定されたNG企業を管理

### 2.7 client_ng_companies（クライアント単位のNG企業）
```sql
CREATE TABLE client_ng_companies (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,     -- 企業名（部分一致用）
    company_id INTEGER REFERENCES companies(id),  -- マッチした企業ID（NULL可）
    matched BOOLEAN DEFAULT FALSE,          -- マッチ状態
    reason TEXT,                            -- NG理由
    is_active BOOLEAN DEFAULT TRUE,         -- アクティブ状態
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 複合ユニーク制約
    UNIQUE(client_id, company_name)
);

-- インデックス
CREATE INDEX idx_client_ng_companies_client_id ON client_ng_companies(client_id);
CREATE INDEX idx_client_ng_companies_company_name ON client_ng_companies(company_name);
CREATE INDEX idx_client_ng_companies_company_id ON client_ng_companies(company_id);
CREATE INDEX idx_client_ng_companies_matched ON client_ng_companies(matched);
```

**説明**
- クライアント単位でのNG企業管理
- CSVインポートに対応し、企業名の部分一致で管理
- マッチング状態を管理し、既存企業との紐付けを保持

### 2.8 ng_import_logs（NGリストインポート履歴）
```sql
CREATE TABLE ng_import_logs (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    file_name VARCHAR(255),                 -- インポートファイル名
    imported_count INTEGER,                 -- インポート総数
    matched_count INTEGER,                  -- 既存企業とマッチした数
    unmatched_count INTEGER,                -- マッチしなかった数
    imported_by VARCHAR(100),               -- インポート実行者
    error_messages TEXT,                    -- エラーメッセージ（JSON形式）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_ng_import_logs_client_id ON ng_import_logs(client_id);
CREATE INDEX idx_ng_import_logs_project_id ON ng_import_logs(project_id);
CREATE INDEX idx_ng_import_logs_created_at ON ng_import_logs(created_at);
```

**説明**
- NGリストのインポート履歴を管理
- インポート結果の統計情報を保持
- エラー発生時のトラブルシューティングに使用

### 2.10 saved_filters（保存済みフィルタ）
```sql
CREATE TABLE saved_filters (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,                        -- 将来のユーザー管理用（現在は不使用）
    name VARCHAR(100) NOT NULL,
    filter_conditions JSONB NOT NULL,       -- 検索条件をJSON形式で保存
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_saved_filters_user_id ON saved_filters(user_id);
CREATE INDEX idx_saved_filters_name ON saved_filters(name);
```

**filter_conditions例**
```json
{
  "search": "人材",
  "industry": "人材・派遣",
  "employee_min": 50,
  "employee_max": 500,
  "prefecture": "東京都",
  "has_facebook": true,
  "exclude_ng": true
}
```

### 2.11 random_orders（ランダム表示順序）
```sql
CREATE TABLE random_orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,                        -- 将来のユーザー管理用
    session_id VARCHAR(255),                -- セッションID（現在はこちらを使用）
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    filter_hash VARCHAR(64),                -- フィルタ条件のハッシュ値
    company_ids_order INTEGER[],            -- 企業IDの表示順序配列
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_random_orders_session_id ON random_orders(session_id);
CREATE INDEX idx_random_orders_filter_hash ON random_orders(filter_hash);
CREATE INDEX idx_random_orders_project_id ON random_orders(project_id);
```

**説明**
- ユーザーごと・フィルタ条件ごとのランダム表示順序を保持
- 同じ条件で再検索した際に同じ順序で表示

---

## 3. リレーション図

```
clients (1) ←→ (N) projects
    ↓                    ↓
    ↓ (1)                ↓ (1)
    ↓                    ↓
client_ng_companies (N)  ↓
                         ↓
companies (1) ←→ (N) executives
    ↓
    ↓ (N)
    ↓
project_companies (N) ←→ (1) projects
    ↓
    ↓ 
    ↓
project_ng_companies (N) ←→ (1) projects

ng_import_logs ←→ clients, projects
saved_filters (独立)
random_orders (独立、将来的にprojectsと関連)
```

### 業務フローでのデータ関係
1. **顧客から案件受注**: clients → projects
2. **クライアントNGリスト登録**: clients → client_ng_companies
3. **案件にターゲット企業追加**: projects + companies → project_companies  
4. **営業活動実施**: project_companies のステータス更新
5. **案件NG企業設定**: projects + companies → project_ng_companies
6. **NGリストインポート履歴**: clients/projects → ng_import_logs

---

## 4. 制約事項

### 4.1 外部キー制約
- 全ての外部キー参照に`ON DELETE CASCADE`設定
- 親データ削除時に関連データも自動削除

### 4.2 ユニーク制約
- `project_companies`: 同一案件に同一企業は1度のみ
- `project_ng_companies`: 同一案件に同一企業のNG設定は1度のみ

### 4.3 データ型選択理由
- `SERIAL`: 自動増分主キー
- `TIMESTAMP WITH TIME ZONE`: タイムゾーン対応の日時
- `JSONB`: 高速検索可能なJSON型（PostgreSQL特有）
- `INTEGER[]`: PostgreSQL配列型（ランダム順序保存用）

---

## 5. パフォーマンス考慮

### 5.1 インデックス設計
- 検索頻度の高いカラムに適切なインデックス
- 複合検索を考慮したインデックス設計
- 条件付きインデックス（Facebook URL等）

### 5.2 データ量想定
- **clients**: 数十〜数百件
- **companies**: 数万〜10万件
- **executives**: 数万〜20万件（1企業あたり平均2名）
- **projects**: 数十〜数百件
- **project_companies**: 数千〜数万件
- **client_ng_companies**: 数百〜数千件（1クライアントあたり10-100件）
- **ng_import_logs**: 数十〜数百件

### 5.3 将来のスケーラビリティ
- パーティショニング対応可能な設計
- マルチテナント対応への拡張性

---

## 6. セキュリティ考慮

### 6.1 Row Level Security（RLS）準備
```sql
-- 将来のマルチテナント対応用
-- ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY tenant_isolation ON companies FOR ALL TO authenticated 
--   USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);
```

### 6.2 データ暗号化
- 機密度の高いデータ（メールアドレス等）の暗号化検討
- PostgreSQLの暗号化機能活用

---

## 7. バックアップ・運用

### 7.1 バックアップ戦略
- Supabaseの自動バックアップ機能活用
- 日次フルバックアップ
- 重要データの差分バックアップ

### 7.2 データメンテナンス
- 定期的なVACUUMの実行
- 不要なランダム順序データの定期削除
- 統計情報の更新

---

## 8. 初期データ投入

### 8.1 マスタデータ
```sql
-- 業界マスタ（アプリケーション側で管理）
-- 都道府県マスタ（アプリケーション側で管理）
-- ステータスマスタ（アプリケーション側で管理）
```

### 8.2 CSVインポート用テンプレート
```csv
企業名,業界,従業員数,売上高,都道府県,市区町村,設立年,企業HP,連絡先メール,電話番号,代表者名,代表者役職,Facebook URL
株式会社サンプル,IT・ソフトウェア,150,500000000,東京都,渋谷区,2010,https://example.com,info@example.com,03-1234-5678,山田太郎,代表取締役,https://facebook.com/yamada
```

この設計でDjango ORMのモデル作成とマイグレーションファイル生成が可能です！