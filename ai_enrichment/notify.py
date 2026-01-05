
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _send_slack_notification(
    message: str,
    *,
    level: str = "info",
    extra: Optional[dict] = None,
) -> None:
    """
    Slack Webhookに通知を送信する
    
    Args:
        message: 通知メッセージ
        level: 通知レベル (info, warning, error, success)
        extra: 追加情報の辞書
    """
    webhook_url = getattr(settings, "SLACK_WEBHOOK_URL", None)
    if not webhook_url:
        logger.info("SLACK_WEBHOOK_URL is not set. Skipping Slack notification.")
        return

    # レベルに応じた色と絵文字を設定
    color_map = {
        "success": "good",
        "info": "#36a64f",
        "warning": "warning",
        "error": "danger",
    }
    emoji_map = {
        "success": "✅",
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
    }

    color = color_map.get(level, color_map["info"])
    emoji = emoji_map.get(level, emoji_map["info"])

    # シンプルなフィールドを構築（基本情報のみ）
    fields = []

    # extraから基本情報のみを追加（補完情報は別処理）
    enrichment_details = None
    if extra:
        logger.info("[SLACK_NOTIFY] extra keys: %s", list(extra.keys()))
        for key, value in extra.items():
            if key == "補完情報":
                enrichment_details = value
                logger.info("[SLACK_NOTIFY] enrichment_details found: %d items", len(value) if isinstance(value, list) else 0)
                continue
            
            # 基本情報のみ表示（運用判断に必要な最小項目）
            if key in ("AI利用(推定)", "処理企業数", "成功", "失敗", "作成された候補数", "補完されたフィールド数"):
                fields.append({
                    "title": key,
                    "value": str(value),
                    "short": True,
                })

    # Slack Block Kitを使用して折りたたみ可能なセクションを作成
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} AI補完バッチ通知",
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message,
            }
        }
    ]

    # 基本情報を表示
    if fields:
        # 2列で表示するため、フィールドを分割
        field_texts = []
        for i in range(0, len(fields), 2):
            row_fields = fields[i:i+2]
            row_text = " | ".join([f"*{f['title']}*: {f['value']}" for f in row_fields])
            field_texts.append(row_text)
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(field_texts),
            }
        })

    # 補完情報を折りたたみ可能なセクションとして追加
    if enrichment_details and isinstance(enrichment_details, list) and len(enrichment_details) > 0:
        logger.info("[SLACK_NOTIFY] Processing enrichment_details: %d items", len(enrichment_details))
        logger.info("[SLACK_NOTIFY] enrichment_details raw data: %s", json.dumps(enrichment_details, ensure_ascii=False, indent=2))
        enrichment_texts = []
        for detail in enrichment_details[:15]:  # 最初の15件のみ表示
            company_name = detail.get("company_name", f"ID: {detail.get('company_id', 'N/A')}")
            status = detail.get("status", "unknown")
            fields_info = []
            
            # 補完が成功した場合のみフィールド情報を表示
            if status == "success" and detail.get("fields"):
                for field_info in detail.get("fields", []):
                    field_name = field_info.get("field", "")
                    field_value = str(field_info.get("value", ""))[:50]  # 50文字まで
                    source = field_info.get("source", "")
                    fields_info.append(f"  • {field_name}: {field_value} ({source})")
            
            # 企業名を表示（補完成功/失敗に関わらず）
            enrichment_texts.append(f"*{company_name}*")
            
            if fields_info:
                # 補完が成功した場合
                enrichment_texts.extend(fields_info)
            elif status == "no_data":
                # 補完を試みたがデータが取得できなかった場合
                # Phase 3-②: no_data_reason_codeを表示
                reason_code = detail.get("no_data_reason_code")
                reason_message = detail.get("no_data_reason_message")
                
                if reason_code:
                    # reason_codeがある場合: "no_data（理由: xxx）"の形式で表示
                    enrichment_texts.append(f"  • no_data（理由: {reason_code}）")
                    if reason_message and reason_message != detail.get("reason", ""):
                        enrichment_texts.append(f"    - {reason_message}")
                else:
                    # reason_codeがない場合（旧形式）: reasonを表示
                    reason = detail.get("reason", "補完できませんでした")
                    # 理由が長い場合は改行して表示
                    if len(reason) > 80:
                        # 長い理由を複数行に分割
                        reason_lines = reason.split(" / ")
                        for i, line in enumerate(reason_lines):
                            if i == 0:
                                enrichment_texts.append(f"  • {line}")
                            else:
                                enrichment_texts.append(f"    {line}")
                    else:
                        enrichment_texts.append(f"  • {reason}")
            elif status == "skipped":
                # 補完不要な企業の場合
                enrichment_texts.append("  • 補完不要（すべてのフィールドが既に存在）")
            elif status == "error":
                # エラーが発生した場合
                error_msg = detail.get("error", "エラーが発生しました")
                enrichment_texts.append(f"  • エラー: {error_msg[:50]}")
            
            enrichment_texts.append("")  # 空行
        
        if len(enrichment_details) > 15:
            enrichment_texts.append(f"... (他{len(enrichment_details) - 15}件)")
        
        if enrichment_texts:
            logger.info("[SLACK_NOTIFY] Adding enrichment section with %d lines", len(enrichment_texts))
            # 補完情報を折りたたみ可能なセクションとして追加
            blocks.append({
                "type": "divider"
            })
            
            # 長いテキストは分割して送信
            enrichment_text = "\n".join(enrichment_texts)
            # Slackの制限（3000文字）を考慮して分割
            if len(enrichment_text) > 2800:
                enrichment_text = enrichment_text[:2800] + "\n... (表示を省略)"
            
            # 補完情報を1つのセクションにまとめる（トグル風に表示）
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📝 補完情報*\n```\n{enrichment_text}\n```",
                }
            })
            logger.info("[SLACK_NOTIFY] Enrichment text preview (first 500 chars): %s", enrichment_text[:500])
    else:
        logger.info("[SLACK_NOTIFY] No enrichment_details to display (type=%s, len=%s)", 
                   type(enrichment_details).__name__ if enrichment_details else "None",
                   len(enrichment_details) if isinstance(enrichment_details, list) else "N/A")

    # blocksのみを使用（attachmentsは削除して重複を防ぐ）
    payload = {
        "blocks": blocks,
    }

    # Slackに通知を送信
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Slack notification sent successfully")
    except requests.RequestException as exc:
        logger.warning("Failed to send Slack notification: %s", exc, exc_info=True)


def notify_success(message: str, *, extra: Optional[dict] = None) -> None:
    logger.info("ai_enrich.success: %s", message, extra=extra or {})
    _send_slack_notification(message, level="success", extra=extra)


def notify_warning(message: str, *, extra: Optional[dict] = None) -> None:
    logger.warning("ai_enrich.warning: %s", message, extra=extra or {})
    _send_slack_notification(message, level="warning", extra=extra)


def notify_error(message: str, *, extra: Optional[dict] = None) -> None:
    logger.error("ai_enrich.error: %s", message, extra=extra or {})
    _send_slack_notification(message, level="error", extra=extra)
