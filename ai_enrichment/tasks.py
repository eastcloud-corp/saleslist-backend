
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import BooleanField, Case, Value, When
from django.utils import timezone

from companies.models import Company, CompanyUpdateCandidate
from companies.services.review_ingestion import ingest_rule_based_candidates
from data_collection.tracker import track_data_collection_run
from saleslist_backend.settings.base import get_ai_enrichment_cooldown

from .constants import AI_ENRICH_BATCH_SIZE, AI_ENRICH_API_DELAY_SECONDS
from .enrich_rules import TARGET_FIELDS, apply_rule_based, build_prompt, build_prompt_with_constraints, build_system_prompt, detect_missing_fields
from .normalizers import normalize_candidate_value
from .enrichment_context import EnrichmentContext
from .confidence import calculate_confidence
from .no_data_reasons import (
    NoDataReasonCode,
    RetryStrategy,
    get_reason_message,
    get_retry_strategy,
)
from .no_data_classifier import classify_no_data_reason
from .exceptions import (
    PowerplexyConfigurationError,
    PowerplexyError,
    PowerplexyRateLimitError,
)
from .notify import notify_error, notify_success, notify_warning
from .powerplexy_client import PowerplexyClient
from .redis_usage import UsageTracker

logger = logging.getLogger(__name__)

AI_SOURCE_DETAIL = "powerplexy"
DEFAULT_DAILY_LIMIT = 500


def _unique_int_list(values: Sequence[int]) -> List[int]:
    seen = set()
    unique: List[int] = []
    for value in values:
        iv = int(value)
        if iv in seen:
            continue
        seen.add(iv)
        unique.append(iv)
    return unique


def _metadata_with_processed(base: Dict[str, object], processed_ids: Sequence[int]) -> Dict[str, object]:
    unique_ids = _unique_int_list(processed_ids)
    metadata: Dict[str, object] = {**base, "processed_count": len(unique_ids)}
    if unique_ids:
        metadata["processed_company_ids"] = unique_ids[:100]
        if len(unique_ids) > 100:
            metadata["processed_company_ids_truncated"] = True
    return metadata


def _reverse_field_map() -> Dict[str, str]:
    return {label: field for field, label in TARGET_FIELDS.items()}


def _normalize_candidate_value(field: str, value: object) -> str:
    if value is None:
        return ""
    if field in {"established_year", "employee_count", "capital"}:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return digits
    return str(value).strip()


def should_skip_company(company: Company, now: datetime) -> Tuple[bool, Optional[str]]:
    """
    企業の補完をスキップすべきか判定（Phase 1: 再実行ガード）
    
    Args:
        company: 対象企業
        now: 現在時刻
    
    Returns:
        (should_skip, skip_reason)
    """
    if not company.ai_last_enriched_at:
        return False, None
    
    cooldown_seconds = get_ai_enrichment_cooldown()
    elapsed = (now - company.ai_last_enriched_at).total_seconds()
    
    if elapsed < cooldown_seconds:
        return True, f"cooldown_not_expired (elapsed: {elapsed:.0f}s, required: {cooldown_seconds}s)"
    
    return False, None


def _companies_requiring_update(limit: int, company_ids: Optional[Sequence[int]] = None, offset: int = 0) -> List[Company]:
    """
    補完が必要な企業を取得する。
    
    Args:
        limit: 取得件数
        company_ids: 特定の企業IDのみを対象とする場合
        offset: スキップする件数（バッチ分割用）
    """
    queryset = Company.objects.all()
    if company_ids:
        queryset = queryset.filter(id__in=company_ids)
    queryset = queryset.annotate(
        never_enriched=Case(
            When(ai_last_enriched_at__isnull=True, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).order_by("-never_enriched", "ai_last_enriched_at", "id")
    targets: List[Company] = []
    skipped = 0
    for company in queryset.iterator():
        if detect_missing_fields(company):
            if skipped < offset:
                skipped += 1
                continue
            targets.append(company)
            if limit and len(targets) >= limit:
                break
    return targets


@shared_task(bind=True, autoretry_for=(PowerplexyRateLimitError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_ai_enrich_scheduled(self) -> dict:
    """
    Celery Beat 用のスケジュール実行ラッパー。
    必ず enqueue_job 経由で AI 補完を実行する。
    
    200件以上でも安全に流せるよう、バッチ分割して実行する。
    1バッチ = AI_ENRICH_BATCH_SIZE件（デフォルト25件）
    """
    from data_collection.services import enqueue_job

    daily_limit = getattr(settings, "POWERPLEXY_DAILY_RECORD_LIMIT", None)
    if daily_limit is None:
        daily_limit = 3 if settings.DEBUG else DEFAULT_DAILY_LIMIT

    batch_size = AI_ENRICH_BATCH_SIZE
    total_batches = (daily_limit + batch_size - 1) // batch_size  # 切り上げ

    logger.info(
        "[AI_ENRICH][SCHEDULED] enqueue_job start (batch mode)",
        extra={
            "total_limit": daily_limit,
            "batch_size": batch_size,
            "total_batches": total_batches,
        },
    )

    try:
        runs = []
        async_results = []
        execution_uuid = None

        # バッチごとに分割してenqueue_jobを呼び出す
        for batch_index in range(total_batches):
            offset = batch_index * batch_size
            batch_limit = min(batch_size, daily_limit - offset)

            if batch_limit <= 0:
                break

            options = {
                "limit": batch_limit,
                "offset": offset,
            }

            run, async_result = enqueue_job(
                job_name="ai.enrich",
                options=options,
            )

            # 最初のバッチのexecution_uuidを記録（全バッチで同一になる想定だが念のため）
            if execution_uuid is None:
                execution_uuid = str(run.execution_uuid)

            runs.append(run)
            if async_result:
                async_results.append(async_result)

            logger.info(
                "[AI_ENRICH][SCHEDULED] batch enqueued",
                extra={
                    "batch_index": batch_index + 1,
                    "total_batches": total_batches,
                    "batch_limit": batch_limit,
                    "offset": offset,
                    "run_id": str(run.id),
                    "execution_uuid": str(run.execution_uuid),
                    "task_id": async_result.id if async_result else None,
                },
            )

        logger.info(
            "[AI_ENRICH][SCHEDULED] all batches enqueued",
            extra={
                "total_batches": len(runs),
                "execution_uuid": execution_uuid,
                "total_task_ids": len(async_results),
            },
        )

        return {
            "status": "queued",
            "total_batches": len(runs),
            "execution_uuid": execution_uuid,
            "run_ids": [str(run.id) for run in runs],
            "task_ids": [ar.id for ar in async_results if ar],
            "total_limit": daily_limit,
        }
    except Exception as exc:
        logger.error(
            "[AI_ENRICH][SCHEDULED] enqueue_job failed",
            extra={"error": str(exc)},
            exc_info=True,
        )
        notify_error("AI補完タスクのスケジュール実行に失敗しました", extra={"error": str(exc)})
        raise


@shared_task(bind=True, autoretry_for=(PowerplexyRateLimitError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_ai_enrich(self, payload: Optional[dict] = None, execution_uuid: Optional[str] = None) -> dict:
    """
    AI補完タスクのメイン処理。
    
    注意: このタスクは enqueue_job 経由でのみ実行されることを想定しています。
    execution_uuid が None の場合は RuntimeError を発生させます。
    """
    if execution_uuid is None:
        raise RuntimeError(
            "run_ai_enrich must be executed via enqueue_job. "
            "Use run_ai_enrich_scheduled for Celery Beat, or enqueue_job for manual execution."
        )

    payload = payload or {}
    tracker_metadata = {"options": payload}
    processed_company_ids: List[int] = []

    daily_limit = payload.get(
        "limit", getattr(settings, "POWERPLEXY_DAILY_RECORD_LIMIT", DEFAULT_DAILY_LIMIT)
    )
    offset = payload.get("offset", 0)

    raw_company_ids = payload.get("company_ids")
    company_ids: Optional[List[int]] = None
    if raw_company_ids is not None:
        if isinstance(raw_company_ids, (int, str)):
            raw_company_ids = [raw_company_ids]
        cleaned: List[int] = []
        for value in raw_company_ids:
            try:
                cleaned.append(int(str(value).strip()))
            except (TypeError, ValueError):
                logger.warning("Invalid company_id provided to AI enrichment: %s", value)
        if cleaned:
            company_ids = cleaned

    with track_data_collection_run(
        "ai.enrich",
        metadata=tracker_metadata,
        execution_uuid=execution_uuid,
    ) as run_tracker:
        usage_tracker = UsageTracker()
        usage_snapshot = usage_tracker.snapshot()
        usage_snapshot_dict = {"calls": usage_snapshot.calls, "cost": usage_snapshot.cost}
        if not usage_tracker.can_execute():
            notify_warning("PowerPlexy月次上限に達したためAI補完をスキップ", extra={
                "usage_calls": usage_snapshot.calls,
                "usage_cost": usage_snapshot.cost,
            })
            run_tracker.complete_success(metadata=_metadata_with_processed(
                {
                    "result": "skipped",
                    "reason": "usage_limit",
                    "usage": usage_snapshot_dict,
                },
                [],
            ))
            return {
                "status": "skipped",
                "reason": "usage_limit",
                "processed_company_ids": [],
                "usage": usage_snapshot_dict,
            }

        try:
            client = PowerplexyClient()
        except PowerplexyConfigurationError as exc:
            notify_error("PowerPlexyの設定が不完全なためAI補完をスキップ", extra={"error": str(exc)})
            run_tracker.complete_success(metadata=_metadata_with_processed(
                {
                    "result": "skipped",
                    "reason": "missing_api_key",
                },
                [],
            ))
            return {"status": "skipped", "reason": "missing_api_key", "processed_company_ids": []}

        companies = _companies_requiring_update(daily_limit, company_ids, offset=offset)
        processed_company_ids = [company.id for company in companies]
        if not companies:
            logger.info("No companies require AI enrichment")
            run_tracker.complete_success(metadata=_metadata_with_processed(
                {
                    "result": "ok",
                    "processed": 0,
                    "created_candidates": 0,
                },
                [],
            ))
            return {"status": "ok", "processed": 0, "created_candidates": 0, "processed_company_ids": []}

        reverse_map = _reverse_field_map()
        total_candidates = 0
        calls_made = 0
        success_company_ids: List[int] = []
        failed_company_ids: List[int] = []
        error_details: List[Dict[str, Any]] = []
        companies_with_corporate_number = 0  # 法人番号がプロンプトに含まれた企業数
        ai_api_used = False  # AI APIが実際に使用されたか
        corporate_number_api_stats = {"calls": 0, "success": 0, "failed": 0}  # 法人番号API統計
        enrichment_details: List[Dict[str, Any]] = []  # 補完情報の詳細

        for company in companies:
            try:
                # Phase 1: 再実行ガードチェック
                now = timezone.now()
                should_skip, skip_reason = should_skip_company(company, now)
                if should_skip:
                    logger.info(
                        "[AI_ENRICH][SKIP] company_id=%d, skip_reason=%s, last_enriched_at=%s",
                        company.id,
                        skip_reason,
                        company.ai_last_enriched_at.isoformat() if company.ai_last_enriched_at else None,
                    )
                    # スキップ情報を記録
                    company_enrichment_record = {
                        "company_id": company.id,
                        "company_name": company.name,
                        "fields": [],
                        "status": "skipped",
                        "reason": skip_reason,
                    }
                    enrichment_details.append(company_enrichment_record)
                    success_company_ids.append(company.id)  # スキップも成功としてカウント（処理は完了）
                    continue
                
                missing_fields = detect_missing_fields(company)
                # 補完を試みた企業を記録（成功/失敗に関わらず）
                company_enrichment_record = {
                    "company_id": company.id,
                    "company_name": company.name,
                    "fields": [],
                    "status": "skipped" if not missing_fields else "attempted",
                }
                
                if not missing_fields:
                    # 補完不要な企業も記録（補完を試みた企業として表示）
                    enrichment_details.append(company_enrichment_record)
                    # Phase 1: 再実行ガード - スキップステータスを更新
                    Company.objects.filter(id=company.id).update(
                        ai_last_enriched_at=timezone.now(),
                        ai_last_enriched_source="",
                        ai_last_enrichment_status="skipped",
                    )
                    success_company_ids.append(company.id)
                    continue

                # Phase 2: EnrichmentContext初期化
                context = EnrichmentContext(
                    company_id=company.id,
                    company_name=company.name,
                )
                
                rule_result = apply_rule_based(
                    company,
                    missing_fields,
                    corporate_number_api_stats=corporate_number_api_stats,
                    return_best_match=True,  # Phase 2: best_matchを取得
                )
                provisional_values = dict(rule_result.values)
                
                # Phase 2: gBizINFO APIの結果をコンテキストに追加
                # Phase 3-②: 初期gBizINFO検索の成功/失敗を記録
                gbiz_initial_404 = not rule_result.metadata.get("corporate_number_found")
                best_match = rule_result.metadata.get("best_match")
                if best_match:
                    context.add_gbizinfo_result(best_match)
                elif rule_result.metadata.get("corporate_number_found"):
                    # best_matchがない場合でも、corporate_number_foundがあればコンテキストに追加
                    gbizinfo_result = {
                        "corporate_number": rule_result.metadata.get("corporate_number_found"),
                        "name": rule_result.metadata.get("gbizinfo_official_name", ""),
                        "address": rule_result.metadata.get("gbizinfo_address", ""),
                        "prefecture": rule_result.metadata.get("gbizinfo_prefecture", ""),
                    }
                    if gbizinfo_result.get("corporate_number") or gbizinfo_result.get("address"):
                        context.add_gbizinfo_result(gbizinfo_result)
                
                # 補完できなかった理由を記録（簡潔に）
                reasons = []
                # gBizINFO APIの結果を確認
                if "corporate_number" in missing_fields or not company.corporate_number:
                    if not rule_result.metadata.get("corporate_number_found"):
                        # gBizINFO APIの理由を確認
                        gbizinfo_reason = rule_result.metadata.get("gbizinfo_reason")
                        if gbizinfo_reason:
                            # 理由を簡潔に（長いエラーメッセージを短縮）
                            if "gBizINFO APIエラー:" in gbizinfo_reason:
                                reasons.append("gBizINFO APIエラー")
                            else:
                                reasons.append(gbizinfo_reason)
                        elif settings.CORPORATE_NUMBER_API_TOKEN:
                            # APIトークンは設定されているが、理由が記録されていない場合
                            reasons.append("gBizINFOで企業が見つかりませんでした")
                # ルールベースで取得できたフィールドがない場合（法人番号以外のフィールドが不足している場合）
                # ただし、法人番号のみが不足している場合は理由に含めない
                if not provisional_values and len(missing_fields) > 1:
                    # 複数のフィールドが不足しているが、ルールベースで取得できなかった
                    if "corporate_number" not in missing_fields or company.corporate_number:
                        reasons.append("ルールベースで補完不可")
                
                # 法人番号APIで取得した法人番号を一時的に設定（プロンプトに含めるため）
                corporate_number_found = rule_result.metadata.get("corporate_number_found")
                original_corporate_number = company.corporate_number
                if corporate_number_found and not company.corporate_number:
                    company.corporate_number = corporate_number_found
                
                # gBizINFOから取得した情報を一時的に設定（AI補完の精度向上のため）
                gbizinfo_address = rule_result.metadata.get("gbizinfo_address")
                gbizinfo_prefecture = rule_result.metadata.get("gbizinfo_prefecture")
                original_prefecture = company.prefecture
                original_city = company.city
                
                # gBizINFOから取得した住所情報を一時的に設定（プロンプトに含めるため）
                if gbizinfo_prefecture and not company.prefecture:
                    company.prefecture = gbizinfo_prefecture
                if gbizinfo_address:
                    # 住所から都道府県を除いた部分をcityに設定
                    # ただし、既にcityがある場合は上書きしない
                    if not company.city and gbizinfo_address:
                        # 都道府県を除いた住所部分を抽出
                        address_without_pref = gbizinfo_address
                        for pref in ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
                                    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
                                    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
                                    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
                                    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
                                    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
                                    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]:
                            if gbizinfo_address.startswith(pref):
                                address_without_pref = gbizinfo_address[len(pref):].strip()
                                break
                        if address_without_pref:
                            company.city = address_without_pref

                remaining = [field for field in missing_fields if field not in provisional_values]
                ai_values: Dict[str, str] = {}
                ai_attempted = False
                if remaining:
                    # 法人番号がプロンプトに含まれるかチェック
                    if hasattr(company, 'corporate_number') and company.corporate_number:
                        companies_with_corporate_number += 1
                    
                    # Phase 2: 制約注入版のプロンプトを使用
                    prompt = build_prompt_with_constraints(company, remaining, context)
                    system_prompt = build_system_prompt()
                    
                    # Phase 2: 制約条件が含まれているかログに記録
                    has_constraints = context.has_gbizinfo_constraints()
                    logger.info(
                        "[AI_ENRICH][PROMPT_WITH_CONSTRAINTS] company_id=%d, has_constraints=%s, prompt_length=%d",
                        company.id,
                        has_constraints,
                        len(prompt),
                    )
                    if has_constraints:
                        constraints = context.get_constraints_for_prompt()
                        logger.info(
                            "[AI_ENRICH][CONSTRAINTS] company_id=%d, constraints=%s",
                            company.id,
                            constraints,
                        )
                    
                    logger.info(
                        "[AI_ENRICH][SYSTEM_PROMPT]",
                        extra={
                            "company_id": company.id,
                            "system_prompt": system_prompt,
                            "system_prompt_length": len(system_prompt),
                        },
                    )
                    try:
                        logger.info(
                            "[AI_ENRICH][AI_REQUEST] company_id=%d, missing_fields=%s, prompt_length=%d",
                            company.id,
                            remaining,
                            len(prompt),
                        )
                        completion = client.extract_json(prompt=prompt, system_prompt=system_prompt)
                        ai_api_used = True
                        ai_attempted = True
                        logger.info(
                            "[AI_ENRICH][AI_RESPONSE] company_id=%d, completion=%s",
                            company.id,
                            completion if completion else "empty",
                        )
                    except PowerplexyRateLimitError:
                        # Rate Limitは再スローしてCelery retryに任せる
                        raise
                    except PowerplexyError as exc:
                        logger.warning(
                            "[AI_ENRICH][FAILED] PowerPlexy呼び出しに失敗",
                            extra={
                                "company_id": company.id,
                                "error": str(exc),
                                "execution_uuid": execution_uuid,
                            },
                        )
                        failed_company_ids.append(company.id)
                        error_details.append({
                            "company_id": company.id,
                            "error_type": "PowerPlexyError",
                            "error": str(exc),
                        })
                        # エラーが発生した場合も記録
                        company_enrichment_record["status"] = "error"
                        company_enrichment_record["error"] = str(exc)
                        enrichment_details.append(company_enrichment_record)
                        continue
                    
                    # Rate Limit対策: API呼び出し間隔を空ける
                    if calls_made > 0:
                        time.sleep(AI_ENRICH_API_DELAY_SECONDS)

                    mapped: Dict[str, str] = {}
                    if completion:
                        logger.info(
                            "[AI_ENRICH][AI_PARSING] company_id=%d, completion_keys=%s, reverse_map_keys=%s",
                            company.id,
                            list(completion.keys()),
                            list(reverse_map.keys()),
                        )
                        for label, value in completion.items():
                            field = reverse_map.get(label)
                            if not field:
                                logger.debug(
                                    "[AI_ENRICH][AI_MAPPING] label '%s' not found in reverse_map",
                                    label,
                                )
                                continue
                            # 空文字列やNoneの場合はスキップ
                            if not value or (isinstance(value, str) and value.strip() == ""):
                                logger.debug(
                                    "[AI_ENRICH][AI_SKIP_EMPTY] field=%s, value=%s",
                                    field,
                                    value,
                                )
                                continue
                            normalized = normalize_candidate_value(field, value)
                            if normalized:
                                mapped[field] = normalized
                                logger.info(
                                    "[AI_ENRICH][AI_MAPPED] field=%s, value=%s, normalized=%s",
                                    field,
                                    value[:50],
                                    normalized[:50],
                                )
                            else:
                                logger.debug(
                                    "[AI_ENRICH][AI_NORMALIZE_FAILED] field=%s, value=%s",
                                    field,
                                    value,
                                )
                    
                    ai_values = mapped
                    
                    # Phase 2: AI補完の結果をコンテキストに追加
                    if completion:
                        context.add_ai_findings(completion)
                    
                    logger.info(
                        "[AI_ENRICH][AI_RESULT] company_id=%d, completion_keys=%s, mapped_keys=%s, mapped_count=%d",
                        company.id,
                        list(completion.keys()) if completion else [],
                        list(mapped.keys()),
                        len(mapped),
                    )
                    
                    if mapped:
                        usage_tracker.increment()
                        calls_made += 1
                    elif ai_attempted:
                        # AI補完を試みたが結果が空だった
                        reasons.append("AI補完で情報が見つかりませんでした")
                        logger.info(
                            "[AI_ENRICH][AI_NO_RESULT] company_id=%d, completion=%s",
                            company.id,
                            completion if completion else "empty",
                        )
                        # Phase 2: 空の結果でもコンテキストに追加（失敗情報として）
                        if completion:
                            context.add_ai_findings(completion)
                elif remaining:
                    # AI補完を試みるべきフィールドがあったが、試みなかった（エラーなど）
                    # この場合は既にエラーとして記録されているので、ここでは追加しない
                    pass
                else:
                    # AI補完を試みる必要がなかった（すべてルールベースで補完できた、または補完不要）
                    pass
                
                # Phase 2: gBizINFO再探索（AIのヒントを使用）
                # Phase 3-②: 再探索の結果を追跡
                gbiz_retry_attempted = False
                gbiz_retry_404 = False
                if context.has_ai_hints_for_retry():
                    gbiz_retry_attempted = True
                    logger.info(
                        "[AI_ENRICH][GBIZINFO_RETRY] company_id=%d, candidates=%s, english_name=%s",
                        company.id,
                        context.ai_official_name_candidates[:3],  # 最初の3つまで
                        context.ai_english_name or "",
                    )
                    try:
                        from companies.services.corporate_number_client import CorporateNumberAPIClient
                        retry_client = CorporateNumberAPIClient()
                        
                        # 再探索候補リストを構築（正式法人名候補 + 英語名）
                        retry_candidates = list(context.ai_official_name_candidates)
                        if context.ai_english_name and context.ai_english_name not in retry_candidates:
                            retry_candidates.append(context.ai_english_name)
                        
                        # 複数の候補を試す（最大3つまで）
                        retry_success = False
                        for retry_candidate in retry_candidates[:3]:
                            if retry_success:
                                break
                            retry_results = retry_client.search(retry_candidate, prefecture=company.prefecture)
                            if retry_results:
                                from companies.services.corporate_number_client import select_best_match
                                retry_best_match = select_best_match(
                                    retry_results,
                                    retry_candidate,
                                    prefecture=company.prefecture
                                )
                                if retry_best_match and retry_best_match.get("corporate_number"):
                                    # 再探索で成功した場合、コンテキストにマージ
                                    context.add_gbizinfo_result(retry_best_match)
                                    # provisional_valuesにも追加（既に存在しない場合のみ）
                                    if not provisional_values.get("corporate_number"):
                                        provisional_values["corporate_number"] = retry_best_match["corporate_number"]
                                    logger.info(
                                        "[AI_ENRICH][GBIZINFO_RETRY_SUCCESS] company_id=%d, candidate=%s, corporate_number=%s, attempt=%d",
                                        company.id,
                                        retry_candidate,
                                        retry_best_match.get("corporate_number"),
                                        retry_candidates.index(retry_candidate) + 1,
                                    )
                                    retry_success = True
                            else:
                                logger.debug(
                                    "[AI_ENRICH][GBIZINFO_RETRY_NO_RESULT] company_id=%d, candidate=%s",
                                    company.id,
                                    retry_candidate,
                                )
                        
                        if not retry_success:
                            gbiz_retry_404 = True
                            logger.info(
                                "[AI_ENRICH][GBIZINFO_RETRY_ALL_FAILED] company_id=%d, tried_candidates=%s",
                                company.id,
                                retry_candidates[:3],
                            )
                    except Exception as exc:
                        gbiz_retry_404 = True
                        logger.warning(
                            "[AI_ENRICH][GBIZINFO_RETRY_ERROR] company_id=%d, error=%s",
                            company.id,
                            str(exc),
                            exc_info=True,
                        )
                
                # Phase 2: 信頼度計算
                context.confidence = calculate_confidence(context)
                
                # 一時的に設定した情報を元に戻す
                if corporate_number_found and not original_corporate_number:
                    company.corporate_number = original_corporate_number
                if gbizinfo_prefecture and not original_prefecture:
                    company.prefecture = original_prefecture
                if gbizinfo_address and not original_city:
                    company.city = original_city

                combined: Dict[str, str] = {}
                combined.update({field: value for field, value in provisional_values.items() if value})
                combined.update({field: value for field, value in ai_values.items() if value})
                
                logger.info(
                    "[AI_ENRICH][DEBUG] company_id=%d, combined=%s, provisional_values=%s, ai_values=%s",
                    company.id,
                    list(combined.keys()),
                    list(provisional_values.keys()),
                    list(ai_values.keys()),
                )
                
                # 補完情報を記録（combinedがあれば記録、normalized_entriesが空でも記録）
                # 候補が作成されるかどうかに関係なく、補完が試みられた場合は記録
                enriched_fields = []
                for field, raw_value in combined.items():
                    # corporate_numberの場合は特別に処理
                    if field == "corporate_number":
                        field_label = "法人番号"
                    else:
                        field_label = TARGET_FIELDS.get(field, field)
                    # ソース表示を改善
                    if field in ai_values:
                        source = "AI"
                    elif field == "corporate_number":
                        source = "gBizINFO"
                    else:
                        source = "ルール"
                    enriched_fields.append({
                        "field": field_label,
                        "value": str(raw_value),
                        "source": source,
                    })
                
                # 補完情報を企業レコードに追加
                company_enrichment_record["fields"] = enriched_fields
                # ステータス判定: enriched_fieldsがあればsuccess、なければno_data
                company_enrichment_record["status"] = "success" if enriched_fields else "no_data"
                
                if not combined:
                    logger.info(
                        "[AI_ENRICH][DEBUG] combined is empty for company_id=%d",
                        company.id,
                    )
                    # 補完を試みたが結果が空の場合も記録
                    company_enrichment_record["status"] = "no_data"
                    
                    # Phase 3-②: no_data理由の分類と再探索戦略の決定
                    ai_fields_empty = not bool(ai_values)
                    has_official_site = bool(company.website_url or context.ai_website_url)
                    
                    reason_code, reason_message, resolved_strategy = classify_no_data_reason(
                        context,
                        gbiz_initial_404,
                        gbiz_retry_404 if gbiz_retry_attempted else False,
                        ai_attempted,
                        ai_fields_empty,
                        has_official_site,
                    )
                    
                    # no_data_reason_codeとno_data_reason_messageを記録
                    company_enrichment_record["no_data_reason_code"] = reason_code.value
                    company_enrichment_record["no_data_reason_message"] = reason_message
                    
                    logger.info(
                        "[AI_ENRICH][NO_DATA_CLASSIFIED] company_id=%d, reason=%s, next_retry_strategy=%s",
                        company.id,
                        reason_code.value,
                        resolved_strategy.value,
                    )
                    
                    # 理由を記録（簡潔に、複数の理由がある場合は改行で区切る）
                    if reasons:
                        # 理由を簡潔にまとめる（重複を除去し、読みやすく）
                        unique_reasons = []
                        seen = set()
                        for reason in reasons:
                            if reason not in seen:
                                unique_reasons.append(reason)
                                seen.add(reason)
                        company_enrichment_record["reason"] = " / ".join(unique_reasons)
                    else:
                        company_enrichment_record["reason"] = reason_message
                    
                    enrichment_details.append(company_enrichment_record)
                    
                    # Phase 3-③: 次回再探索戦略とクールダウンを保存
                    Company.objects.filter(id=company.id).update(
                        ai_last_enriched_at=timezone.now(),
                        ai_last_enriched_source="",
                        ai_last_enrichment_status="failed",
                        next_retry_strategy=resolved_strategy.value,
                    )
                    success_company_ids.append(company.id)
                    continue
                
                normalized_entries: Dict[str, str] = {}
                for field, raw_value in combined.items():
                    normalized = normalize_candidate_value(field, raw_value)
                    if normalized:
                        normalized_entries[field] = normalized
                    else:
                        logger.debug(
                            "Skipping candidate due to normalization failure",
                            extra={"field": field, "raw_value": raw_value, "company_id": company.id},
                        )

                if not normalized_entries:
                    logger.info(
                        "[AI_ENRICH][DEBUG] normalized_entries is empty for company_id=%d, combined=%s",
                        company.id,
                        combined,
                    )
                    # normalized_entriesが空でも、combinedがあれば補完情報を記録
                    # 既にcompany_enrichment_recordに情報が入っているので、そのまま追加
                    if enriched_fields:
                        enrichment_details.append(company_enrichment_record)
                        logger.info(
                            "[AI_ENRICH][ENRICHMENT_DETAIL] recorded (no normalized) for company_id=%d, fields=%d",
                            company.id,
                            len(enriched_fields),
                        )
                    success_company_ids.append(company.id)
                    continue

                logger.info(
                    "[AI_ENRICH][DEBUG] normalized_entries for company_id=%d: %s",
                    company.id,
                    list(normalized_entries.keys()),
                )
                
                entry_records = []
                for field, value in normalized_entries.items():
                    # Phase 2: 信頼度をコンテキストから取得（なければデフォルト値）
                    field_confidence = context.confidence.get(field, 85 if field in ai_values else 100)
                    entry_records.append(
                        {
                            "company_id": company.id,
                            "field": field,
                            "value": value,
                            "source_type": CompanyUpdateCandidate.SOURCE_AI,
                            "source_detail": AI_SOURCE_DETAIL,
                            "confidence": int(field_confidence * 100),  # 0.0-1.0を0-100に変換
                            "metadata": {
                                "rule_metadata": getattr(rule_result, "metadata", {}),
                                "ai": field in ai_values,
                                "confidence_source": "calculated",  # Phase 2: 信頼度計算済み
                            },
                        }
                    )
                
                if entry_records:
                    ingested = ingest_rule_based_candidates(entry_records)
                    total_candidates += len(ingested)
                    # Phase 1: 再実行ガード - ステータスを更新
                    # Phase 3-③: 成功時はnext_retry_strategyをNONEにリセット
                    enrichment_status = "success" if enriched_fields else "partial"
                    Company.objects.filter(id=company.id).update(
                        ai_last_enriched_at=timezone.now(),
                        ai_last_enriched_source="ai" if ai_values else "rule",
                        ai_last_enrichment_status=enrichment_status,
                        next_retry_strategy=RetryStrategy.NONE.value,
                    )
                    logger.info(
                        "[AI_ENRICH][DEBUG] company_id=%d, ingested=%d, entry_records=%d",
                        company.id,
                        len(ingested),
                        len(entry_records),
                    )
                
                # 補完情報を記録（enriched_fieldsがあれば記録）
                # 候補が作成されなくても（既存値と一致する場合など）、補完が試みられた場合は記録
                # 既にcompany_enrichment_recordに情報が入っているので、そのまま追加
                if enriched_fields:
                    enrichment_details.append(company_enrichment_record)
                    logger.info(
                        "[AI_ENRICH][ENRICHMENT_DETAIL] recorded for company_id=%d, fields=%d",
                        company.id,
                        len(enriched_fields),
                    )
                    # Phase 1: 再実行ガード - 成功/部分成功ステータスを更新（候補が作成されなかった場合でも）
                    # Phase 3-③: 成功時はnext_retry_strategyをNONEにリセット
                    if not entry_records:
                        # 候補は作成されなかったが、補完情報は記録された
                        enrichment_status = "partial" if len(enriched_fields) < len(missing_fields) else "success"
                        Company.objects.filter(id=company.id).update(
                            ai_last_enriched_at=timezone.now(),
                            ai_last_enriched_source="ai" if ai_values else "rule",
                            ai_last_enrichment_status=enrichment_status,
                            next_retry_strategy=RetryStrategy.NONE.value,
                        )
                
                success_company_ids.append(company.id)
            except Exception as exc:
                # 予期しないエラーも記録（部分成功前提）
                logger.warning(
                    "[AI_ENRICH][FAILED] 予期しないエラー",
                    extra={
                        "company_id": company.id,
                        "error": str(exc),
                        "execution_uuid": execution_uuid,
                    },
                    exc_info=True,
                )
                failed_company_ids.append(company.id)
                error_details.append({
                    "company_id": company.id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })

        usage_after = usage_tracker.snapshot()
        usage_after_dict = {"calls": usage_after.calls, "cost": usage_after.cost}
        
        # 失敗した会社IDをmetadataに保存（再実行用）
        metadata_base = {
            "result": "ok",
            "processed": len(companies),
            "success_count": len(success_company_ids),
            "failed_count": len(failed_company_ids),
            "created_candidates": total_candidates,
            "calls": calls_made,
            "usage_before": usage_snapshot_dict,
            "usage_after": usage_after_dict,
            "companies_with_corporate_number": companies_with_corporate_number,
            "ai_api_used": ai_api_used,
            "corporate_number_api": corporate_number_api_stats,
        }
        
        # 補完情報が記録されている場合のみ通知を送信
        if not enrichment_details and total_candidates == 0:
            logger.info(
                "[AI_ENRICH][NOTIFICATION] Skipping notification: no enrichment details and no candidates created"
            )
        else:
            # 通知用の詳細情報を構築（シンプルに）
            # 補完情報のフィールド数を計算（実際に補完された情報の数）
            total_enriched_fields = sum(
                len(detail.get("fields", [])) 
                for detail in enrichment_details 
                if isinstance(detail, dict)
            )
            
            notification_extra = {
                "処理企業数": len(companies),
                "成功": len(success_company_ids),
                "失敗": len(failed_company_ids),
                "作成された候補数": total_candidates,
                "補完されたフィールド数": total_enriched_fields,
            }
            
            # 補完情報を追加（折りたたみ可能な形式で）
            logger.info(
                "[AI_ENRICH][NOTIFICATION] enrichment_details count: %d, total_fields: %d, total_candidates: %d",
                len(enrichment_details),
                total_enriched_fields,
                total_candidates,
                extra={"enrichment_details": enrichment_details},
            )
            if enrichment_details:
                notification_extra["補完情報"] = enrichment_details
            
            if failed_company_ids:
                metadata_base["failed_company_ids"] = failed_company_ids
                metadata_base["error_details"] = error_details[:10]  # 最初の10件のみ保存
                notify_warning(
                    "AI補完バッチが完了しました（一部失敗）",
                    extra=notification_extra,
                )
            else:
                notify_success(
                    "AI補完バッチが完了しました",
                    extra=notification_extra,
                )

        run_tracker.complete_success(
            metadata=_metadata_with_processed(
                metadata_base,
                processed_company_ids,
            ),
            input_count=len(companies),
            inserted_count=total_candidates,
            skipped_count=0,
            error_count=len(failed_company_ids),
        )

        return {
            "status": "ok",
            "processed": len(companies),
            "success_count": len(success_company_ids),
            "failed_count": len(failed_company_ids),
            "failed_company_ids": failed_company_ids,
            "created_candidates": total_candidates,
            "calls": calls_made,
            "processed_company_ids": processed_company_ids,
        }
