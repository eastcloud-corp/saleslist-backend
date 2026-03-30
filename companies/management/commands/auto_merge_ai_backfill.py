import logging
from typing import Optional, Set, Tuple

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import FieldDoesNotExist
from django.db import connection, transaction
from django.db.utils import DataError
from django.utils import timezone

from companies.models import (
    Company,
    CompanyReviewBatch,
    CompanyReviewItem,
    CompanyUpdateCandidate,
    CompanyUpdateHistory,
    ExternalSourceRecord,
)
from companies.services import review_ingestion

logger = logging.getLogger(__name__)


def _get_company_field_max_length(field: str) -> Optional[int]:
    """
    Company.{field} が CharField の場合に max_length を返す。
    """
    try:
        model_field = Company._meta.get_field(field)
    except FieldDoesNotExist:
        return None

    max_length = getattr(model_field, "max_length", None)
    if isinstance(max_length, int):
        return max_length
    return None


def _effective_confidence(confidence: int) -> int:
    """
    現状の DB では 8500 のような値が混在しているため、
    0-100 スケールへ概算で正規化する。
    - 0-100: そのまま
    - 101以上: 100で割って小数切り捨て（例: 8500 -> 85）
    """
    return confidence if confidence <= 100 else confidence // 100


def _convert_for_company_field(field: str, normalized_value: str) -> Tuple[object, str]:
    """
    review_ingestion.py と同等の変換を利用する。
    """
    return review_ingestion._convert_value_for_company_field(field, normalized_value)  # type: ignore[attr-defined]


class Command(BaseCommand):
    help = "AI補完候補のバックフィル（confidence閾値以上をレビュー無しで自動反映し、reviewもapproved化）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confidence-threshold",
            type=int,
            default=75,
            help="0-100スケール換算で、この値以上の AI pending 候補を対象にします。",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="処理対象候補数の上限（デバッグ/検証用）。",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="書き換えを行わず、対象件数とスキップ理由だけ表示します。",
        )
        parser.add_argument(
            "--no-normalize-confidence",
            action="store_true",
            default=False,
            help="8500等の confidence を正規化せず、そのまま閾値判定します。",
        )
        parser.add_argument(
            "--decided-by-user-id",
            type=int,
            default=None,
            help="company_review_items の decided_by に設定するユーザーID（省略時は null）。",
        )

    def handle(self, *args, **options):
        threshold: int = int(options["confidence_threshold"])
        limit: Optional[int] = options["limit"]
        dry_run: bool = bool(options["dry_run"])
        normalize_confidence: bool = not bool(options["no_normalize_confidence"])
        decided_by_user_id: Optional[int] = options["decided_by_user_id"]

        if threshold < 0 or threshold > 10000:
            raise CommandError("--confidence-threshold の値が不正です")

        now = timezone.now()

        decided_by = None
        if decided_by_user_id is not None:
            User = get_user_model()
            decided_by = User.objects.filter(pk=decided_by_user_id).first()
            if not decided_by:
                raise CommandError(f"--decided-by-user-id={decided_by_user_id} のユーザーが見つかりません")

        # 先に 0-100 スケールへ正規化する（confidence が 8500 等のデータが混在しているため）
        if normalize_confidence and not dry_run:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE company_update_candidates
                    SET confidence = confidence / 100
                    WHERE source_type = 'AI'
                      AND status = 'pending'
                      AND confidence > 100;
                    """
                )
                cursor.execute(
                    """
                    UPDATE company_review_items
                    SET confidence = confidence / 100
                    WHERE confidence > 100
                      AND candidate_id IN (
                        SELECT id FROM company_update_candidates
                        WHERE source_type = 'AI' AND status = 'pending'
                      );
                    """
                )

        base_qs = (
            CompanyUpdateCandidate.objects.select_related("company")
            .filter(source_type=CompanyUpdateCandidate.SOURCE_AI, status=CompanyUpdateCandidate.STATUS_PENDING)
            .order_by("id")
        )
        if limit:
            base_qs = base_qs[:limit]

        batch_ids: Set[int] = set()
        applied = 0
        skipped = 0
        skipped_reason_counts: dict[str, int] = {}
        truncated = 0
        truncated_reason_counts: dict[str, int] = {}
        total_scanned = 0

        # まずは対象 candidates を走査（ここでは書き込みしない）
        candidates = list(base_qs.iterator())
        total_scanned = len(candidates)

        self.stdout.write(f"scanned={total_scanned}, threshold={threshold}, dry_run={dry_run}, normalize_confidence={normalize_confidence}")

        for candidate in candidates:
            total_conf = int(candidate.confidence)
            effective_conf = _effective_confidence(total_conf) if normalize_confidence else total_conf

            if effective_conf < threshold:
                skipped += 1
                skipped_reason_counts["below_threshold"] = skipped_reason_counts.get("below_threshold", 0) + 1
                continue

            field = candidate.field
            company = candidate.company
            if not hasattr(company, field):
                skipped += 1
                skipped_reason_counts["company_has_no_field"] = skipped_reason_counts.get("company_has_no_field", 0) + 1
                continue

            normalized_value = candidate.candidate_value or ""
            try:
                converted, display_value = _convert_for_company_field(field, normalized_value)
            except ValueError:
                skipped += 1
                skipped_reason_counts["convert_value_error"] = skipped_reason_counts.get("convert_value_error", 0) + 1
                continue
            except Exception:
                logger.exception("convert_for_company_field failed: candidate_id=%s field=%s", candidate.id, field)
                skipped += 1
                skipped_reason_counts["convert_unknown_error"] = skipped_reason_counts.get("convert_unknown_error", 0) + 1
                continue

            # review_ingestion.py の条件に合わせる（変換できない/空は通常レビューへ）
            if converted is None and display_value == "":
                skipped += 1
                skipped_reason_counts["converted_empty"] = skipped_reason_counts.get("converted_empty", 0) + 1
                continue

            # DBカラム長制約を超える文字列は落とさずスキップ
            max_len = _get_company_field_max_length(field)
            if max_len is not None and isinstance(converted, str) and len(converted) > max_len:
                converted = converted[:max_len]
                display_value = display_value[:max_len]
                truncated += 1
                truncated_reason_counts["truncated_for_column"] = truncated_reason_counts.get("truncated_for_column", 0) + 1

            batch_ids.update(
                list(
                    candidate.review_items.values_list("batch_id", flat=True)  # type: ignore[attr-defined]
                )
            )

            if dry_run:
                applied += 1
                continue

            with transaction.atomic():
                # ロックして再チェック（dry-runでは不要）
                locked_candidate = (
                    CompanyUpdateCandidate.objects.select_for_update()
                    .select_related("company")
                    .get(pk=candidate.pk)
                )
                if locked_candidate.status != CompanyUpdateCandidate.STATUS_PENDING:
                    skipped += 1
                    skipped_reason_counts["already_not_pending"] = skipped_reason_counts.get("already_not_pending", 0) + 1
                    continue

                # 候補の変換
                locked_company = Company.objects.select_for_update().get(pk=locked_candidate.company_id)
                normalized_value = locked_candidate.candidate_value or ""
                effective_conf = _effective_confidence(int(locked_candidate.confidence)) if normalize_confidence else int(locked_candidate.confidence)

                if effective_conf < threshold:
                    skipped += 1
                    skipped_reason_counts["below_threshold_after_lock"] = skipped_reason_counts.get("below_threshold_after_lock", 0) + 1
                    continue

                try:
                    converted, display_value = _convert_for_company_field(field, normalized_value)
                except ValueError:
                    skipped += 1
                    skipped_reason_counts["convert_value_error_after_lock"] = skipped_reason_counts.get("convert_value_error_after_lock", 0) + 1
                    continue
                except Exception:
                    logger.exception("convert_for_company_field failed after lock: candidate_id=%s field=%s", locked_candidate.id, field)
                    skipped += 1
                    skipped_reason_counts["convert_unknown_error_after_lock"] = skipped_reason_counts.get("convert_unknown_error_after_lock", 0) + 1
                    continue
                if converted is None and display_value == "":
                    skipped += 1
                    skipped_reason_counts["converted_empty_after_lock"] = skipped_reason_counts.get("converted_empty_after_lock", 0) + 1
                    continue

                max_len = _get_company_field_max_length(field)
                if max_len is not None and isinstance(converted, str) and len(converted) > max_len:
                    converted = converted[:max_len]
                    display_value = display_value[:max_len]
                    truncated += 1
                    truncated_reason_counts["truncated_for_column_after_lock"] = truncated_reason_counts.get(
                        "truncated_for_column_after_lock",
                        0,
                    ) + 1

                old_value = getattr(locked_company, field, None)
                setattr(locked_company, field, converted)
                try:
                    locked_company.save(update_fields=[field, "updated_at"])
                except DataError:
                    max_len = _get_company_field_max_length(field)
                    skipped += 1
                    skipped_reason_counts["data_error_on_company_save"] = skipped_reason_counts.get(
                        "data_error_on_company_save",
                        0,
                    ) + 1
                    logger.warning(
                        "skip due to DataError: candidate_id=%s company_id=%s field=%s effective_conf=%s len(converted)=%s max_len=%s",
                        locked_candidate.id,
                        locked_company.id,
                        field,
                        effective_conf,
                        len(str(converted)) if converted is not None else 0,
                        max_len,
                        exc_info=True,
                    )
                    continue

                new_value_hash = CompanyUpdateCandidate.make_value_hash(field, display_value)

                locked_candidate.candidate_value = display_value
                locked_candidate.value_hash = new_value_hash
                locked_candidate.confidence = effective_conf
                locked_candidate.status = CompanyUpdateCandidate.STATUS_MERGED
                locked_candidate.merged_at = now
                locked_candidate.block_reproposal = False
                locked_candidate.rejection_reason_code = CompanyUpdateCandidate.REJECTION_REASON_NONE
                locked_candidate.rejection_reason_detail = ""
                locked_candidate.save(
                    update_fields=[
                        "candidate_value",
                        "value_hash",
                        "confidence",
                        "status",
                        "merged_at",
                        "block_reproposal",
                        "rejection_reason_code",
                        "rejection_reason_detail",
                        "updated_at",
                    ]
                )

                CompanyUpdateHistory.objects.create(
                    company=locked_company,
                    field=field,
                    old_value="" if old_value is None else str(old_value),
                    new_value=str(display_value),
                    source_type=locked_candidate.source_type,
                    approved_by=decided_by,
                    approved_at=now,
                    comment=f"auto-merged (confidence={effective_conf})",
                )

                # 取得履歴（ExternalSourceRecord）更新（metadata は保持できないため data_hash / last_fetched_at のみ更新）
                source_id = locked_candidate.source_detail or locked_candidate.source_type
                record, _created = ExternalSourceRecord.objects.get_or_create(
                    company=locked_company,
                    field=field,
                    source=source_id,
                    defaults={
                        "last_fetched_at": now,
                        "data_hash": new_value_hash,
                    },
                )
                record.last_fetched_at = now
                record.data_hash = new_value_hash
                record.save(update_fields=["last_fetched_at", "data_hash", "updated_at"])

                # review_items を approved 化（決裁情報は optional）
                review_items_qs = CompanyReviewItem.objects.filter(candidate_id=locked_candidate.id)
                review_items_qs.update(
                    decision=CompanyReviewItem.DECISION_APPROVED,
                    confidence=effective_conf,
                    decided_by=decided_by,
                    decided_at=now,
                )

                applied += 1

        # バッチステータス更新
        if dry_run or not batch_ids:
            self.stdout.write(f"done (dry-run or no batches). applied={applied}, skipped={skipped}")
            return

        updated_batches = 0
        for batch_id in sorted(batch_ids):
            with transaction.atomic():
                batch = CompanyReviewBatch.objects.select_for_update().get(pk=batch_id)
                items_qs = batch.items.all()

                pending_exists = items_qs.filter(decision=CompanyReviewItem.DECISION_PENDING).exists()
                approved_exists = items_qs.filter(decision__in=[CompanyReviewItem.DECISION_APPROVED, CompanyReviewItem.DECISION_UPDATED]).exists()
                rejected_exists = items_qs.filter(decision=CompanyReviewItem.DECISION_REJECTED).exists()

                if pending_exists:
                    new_status = CompanyReviewBatch.STATUS_IN_REVIEW
                else:
                    if approved_exists and rejected_exists:
                        new_status = CompanyReviewBatch.STATUS_PARTIAL
                    elif approved_exists:
                        new_status = CompanyReviewBatch.STATUS_APPROVED
                    elif rejected_exists:
                        new_status = CompanyReviewBatch.STATUS_REJECTED
                    else:
                        new_status = CompanyReviewBatch.STATUS_IN_REVIEW

                if batch.status != new_status:
                    batch.status = new_status
                    batch.save(update_fields=["status", "updated_at"])
                    updated_batches += 1

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"done. applied={applied}, skipped={skipped}, truncated={truncated}, "
                    f"batches_updated={updated_batches}, skipped_reasons={skipped_reason_counts}, truncated_reasons={truncated_reason_counts}"
                )
            )
        )

