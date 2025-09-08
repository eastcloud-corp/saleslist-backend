# API変数名統一表

## 基本方針
- **API（JSON）**: snake_case（Django標準）
- **フロントエンド（TypeScript）**: camelCase（JavaScript標準）
- **Database（Model）**: snake_case（Django標準）

## 案件管理新機能の統一変数名

### 一覧画面 vs 詳細画面
- **一覧画面**: 編集可能な重要項目のみ（チェックボックス、ステータス、数値4項目、状況）
- **詳細画面**: 全項目（リンク、担当者情報、契約情報、メモ欄等すべて）

### 基本情報
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| クライアント名 | client_name | clientName | クライアント名 |
| 所在地(都道府県) | location_prefecture | locationPrefecture | 所在地(都道府県) |
| 業種 | industry | industry | 業種 |
| サービス | service_type | serviceType | サービス |

### リンク情報
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| 運用シートリンク | operation_sheet_link | operationSheetLink | 運用シートリンク |
| レポートリンク | report_link | reportLink | レポートリンク |
| アカウントリンク | account_link | accountLink | アカウントリンク |

### 媒体・制限情報
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| 媒体 | media_type | mediaType | 媒体 |
| 制限 | restrictions | restrictions | 制限 |
| 連絡先 | contact_info | contactInfo | 連絡先 |

### 数値データ（一覧画面表示項目）
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| アポ数 | appointment_count | appointmentCount | アポ数 |
| 承認数 | approval_count | approvalCount | 承認数 |
| 返信数 | reply_count | replyCount | 返信数 |
| 友達数 | friends_count | friendsCount | 友達数 |

### 状況・進行管理
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| 状況 | situation | situation | 状況 |
| 進行状況 | progress_status | progressStatus | 進行状況 |

### チェックボックス項目（一覧画面表示項目）
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| Dがログインできるアカウント | director_login_available | directorLoginAvailable | Dがログインできるアカウント |
| 運用者グループ招待 | operator_group_invited | operatorGroupInvited | 運用者グループ招待 |

### 担当者情報
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| ディレクター | director | director | ディレクター |
| 運用者 | operator | operator | 運用者 |
| 営業マン | sales_person | salesPerson | 営業マン |
| アサイン可否 | assignment_available | assignmentAvailable | アサイン可否 |

### 編集ロック関連
| 項目名 | API/DB (snake_case) | Frontend (camelCase) | 日本語名 |
|--------|---------------------|---------------------|----------|
| ロック状態 | is_locked | isLocked | ロック状態 |
| ロック中ユーザー | locked_by | lockedBy | ロック中ユーザー |
| ロック中ユーザー名 | locked_by_name | lockedByName | ロック中ユーザー名 |
| ロック期限 | locked_until | lockedUntil | ロック期限 |

## TypeScript型定義

### Project型（一覧画面用）
```typescript
interface ProjectListItem {
  id: number;
  clientName: string;
  progressStatus: string;
  directorLoginAvailable: boolean;
  operatorGroupInvited: boolean;
  appointmentCount: number;
  approvalCount: number;
  replyCount: number;
  friendsCount: number;
  situation: string;
  isLocked: boolean;
  lockedBy?: number;
  lockedByName?: string;
}
```

### EditLock型
```typescript
interface ProjectEditLock {
  projectId: number;
  userId: number;
  userName: string;
  lockedAt: string;
  lockedUntil: string;
}
```

### ProjectDetailItem型（詳細画面用）
```typescript
interface ProjectDetailItem {
  id: number;
  clientName: string;
  locationPrefecture: string;
  industry: string;
  serviceType: string;
  
  // リンク情報
  operationSheetLink: string;
  reportLink: string;
  accountLink: string;
  
  // 媒体・制限情報
  mediaType: string;
  restrictions: string;
  contactInfo: string;
  
  // 数値データ
  appointmentCount: number;
  approvalCount: number;
  replyCount: number;
  friendsCount: number;
  
  // 状況・進行管理
  situation: string;
  progressStatus: string;
  
  // チェック・タスク管理
  replyCheckNotes: string;
  dailyTasks: string;
  progressTasks: string;
  remarks: string;
  complaintsRequests: string;
  
  // NG・課題管理
  clientNgOperationalBarriers: string;
  issuesImprovements: string;
  
  // 担当者情報
  director: string;
  operator: string;
  salesPerson: string;
  assignmentAvailable: boolean;
  
  // チェックボックス項目
  directorLoginAvailable: boolean;
  operatorGroupInvited: boolean;
  
  // 契約・期間情報
  contractPeriod: string;
  entryDateSales: string;
  operationStartDate: string;
  expectedEndDate: string;
  periodExtension: string;
  
  // 定例会情報
  regularMeetingStatus: string;
  regularMeetingDate: string;
  
  // リスト情報
  listAvailability: string;
  listImportSource: string;
  listCount: number;
  
  // システム管理
  createdAt: string;
  updatedAt: string;
}
```

### ProjectUpdateRequest型（一覧画面用）
```typescript
interface ProjectUpdateRequest {
  directorLoginAvailable?: boolean;
  operatorGroupInvited?: boolean;
  progressStatus?: string;
  appointmentCount?: number;
  approvalCount?: number;
  replyCount?: number;
  friendsCount?: number;
  situation?: string;
}
```

### ProjectDetailUpdateRequest型（詳細画面用）
```typescript
interface ProjectDetailUpdateRequest {
  // 基本情報
  clientName?: string;
  locationPrefecture?: string;
  industry?: string;
  serviceType?: string;
  
  // リンク情報
  operationSheetLink?: string;
  reportLink?: string;
  accountLink?: string;
  
  // 媒体・制限情報
  mediaType?: string;
  restrictions?: string;
  contactInfo?: string;
  
  // 数値データ
  appointmentCount?: number;
  approvalCount?: number;
  replyCount?: number;
  friendsCount?: number;
  
  // 状況・進行管理
  situation?: string;
  progressStatus?: string;
  
  // チェック・タスク管理
  replyCheckNotes?: string;
  dailyTasks?: string;
  progressTasks?: string;
  remarks?: string;
  complaintsRequests?: string;
  
  // NG・課題管理
  clientNgOperationalBarriers?: string;
  issuesImprovements?: string;
  
  // 担当者情報
  director?: string;
  operator?: string;
  salesPerson?: string;
  assignmentAvailable?: boolean;
  
  // チェックボックス項目
  directorLoginAvailable?: boolean;
  operatorGroupInvited?: boolean;
  
  // 契約・期間情報
  contractPeriod?: string;
  entryDateSales?: string;
  operationStartDate?: string;
  expectedEndDate?: string;
  periodExtension?: string;
  
  // 定例会情報
  regularMeetingStatus?: string;
  regularMeetingDate?: string;
  
  // リスト情報
  listAvailability?: string;
  listImportSource?: string;
  listCount?: number;
}
```