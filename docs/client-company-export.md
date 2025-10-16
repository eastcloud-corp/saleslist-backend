# クライアント企業リストエクスポート & 7200件上限設計

## 目的
- クライアントが管理する案件に追加済みの企業リスト（ProjectCompany）を CSV で取得できるようにする。
- クライアント単位で登録可能な企業件数を 7,200 件に制限し、過剰なリスト投入を防ぐ。

## 背景・現状
- 現在は案件単位で `/projects/{id}/export_csv/` によるエクスポート機能が存在するが、クライアント全体の企業リストをまとめて取得する手段がない。
- クライアントビュー (`ClientViewSet`) には `available_companies` などの操作用エンドポイントが提供されているが、リミット制御は未実装。
- フロントエンドでは `/clients/[id]/select-companies` 画面から案件へ企業を追加できるが、追加件数に上限がなくパフォーマンス劣化が懸念される。

## 要件
1. **CSV エクスポート**
   - 対象: 指定クライアントに紐づく全ての `ProjectCompany`。
   - 出力形式: CSV (`text/csv; charset=utf-8`)、ファイル名例 `client_{client_id}_companies.csv`。
   - カラム候補:
     - `client_name`, `project_name`, `company_name`, `industry`, `status`, `contact_date`, `staff_name`, `notes`, `is_active`, `created_at`, `updated_at`
   - 認可: `IsAuthenticated`（現行クライアント API と同等）。
   - ページング不要（全件吐き出し）。

2. **7,200 件上限**
   - 条件: クライアントに紐づく `ProjectCompany` レコード総数が 7,200 件を超えないようにする。
   - 判定タイミング:
     - `projects/views.py::add_companies`（案件に企業を追加する API）で、追加予定件数と既存件数を合算して上限を超える場合はエラーを返す。
     - 将来的に他経路からの追加（CSV インポートなど）が生じた場合も同様にチェックを追加する必要あり。
   - エラーレスポンス:
     - `400 Bad Request` などで「クライアントの登録上限（7,200件）を超えるため追加できません」を返却。
   - フロント側では API のエラーメッセージをダイアログ／トーストで表示。

## 影響範囲
- **バックエンド**
  - `clients/views.py`
    - 新規エンドポイント `@action(detail=True, methods=['get'], url_path='export-companies')`
    - CSV 生成処理（`csv.writer` + `HttpResponse`）を実装。`ProjectCompany` を `select_related('project', 'company')` で取得。
  - `projects/views.py::add_companies`
    - クライアントの既存件数を集計し、上限チェックを追加。
  - 既存のテスト (`projects/tests.py`, `clients/tests.py`) にユースケースを追加。

- **フロントエンド**
  - `app/clients/[id]/page.tsx` などクライアント詳細ページに「企業リストをエクスポート」ボタンを追加。
  - `apiClient` から新 API (`GET /clients/{id}/export-companies`) を呼び、CSV をダウンロード。既存の `exportCompaniesToCSV` ユーティリティを流用可能。
  - 企業追加 UI (`select-companies` ページ) で 7200 件超過エラーの表示を追加（リトライ時も提示）。

- **ドキュメント / 運用**
  - API 仕様書（OpenAPI）更新。
  - 運用マニュアルに上限値とエクスポート方法を記載。

## 実装方針
1. **CSV 生成処理**
   ```python
   @action(detail=True, methods=['get'], url_path='export-companies')
   def export_companies(self, request, pk=None):
       client = self.get_object()
       companies = (
           ProjectCompany.objects
           .filter(project__client=client)
           .select_related('project', 'company')
           .order_by('project__id', 'company__name')
       )

       response = HttpResponse(content_type='text/csv; charset=utf-8')
       response['Content-Disposition'] = f'attachment; filename=\"client_{client.id}_companies.csv\"'

       writer = csv.writer(response)
       writer.writerow([...headers...])
       for row in companies:
           writer.writerow([...])
       return response
   ```

2. **上限チェック**
   ```python
   client_company_count = ProjectCompany.objects.filter(project__client=project.client).count()
   if client_company_count + len(company_ids) > 7200:
       return Response({
           'error': 'クライアントの企業登録数が上限(7200件)を超えるため追加できません。'
       }, status=status.HTTP_400_BAD_REQUEST)
   ```
   - 実際の追加数は NG 判定などで減る可能性があるため、厳密には追加予定の「新規作成される件数」を算出する。
   - ループ前に `existing_company_ids` を取得し、新規追加対象数を算出 (`len(pending_new_ids)`)。

3. **テスト**
   - `clients/tests.py`：新規エクスポート API の正常系テスト。
   - `projects/tests.py`：7200 件上限を超える場合にエラーとなるテスト、境界値テスト。
   - 必要に応じてフロントの E2E テスト更新。

## リスク・留意点
- 7,200 件全件を CSV に含めると、レスポンスサイズが数 MB に達する可能性がある → 必要ならストリーミング対応を検討。
- 将来的にクライアント単位の CSV カラム仕様が変更される場合、共通ユーティリティ化を検討。
- 上限制御を他の追加経路（将来のバッチやインポート）にも忘れず適用。

## 未決事項
- CSV カラムの最終確定（必要に応じて関係者に確認）。
- 7,200 件上限の根拠（設定で可変にする必要があるか）。
