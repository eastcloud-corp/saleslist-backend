"""
DM作成補助: ChatGPT (OpenAI) と Gemini によるメッセージ生成サービス。

4つの生成を並列実行:
- GPT プロンプトA
- GPT プロンプトB
- Gemini プロンプトA
- Gemini プロンプトB
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

from dm_assistant.prompts import (
    PROMPT_GPT_A,
    PROMPT_GPT_B,
    PROMPT_GEMINI_A,
    PROMPT_GEMINI_B,
)

logger = logging.getLogger(__name__)

# 出力が長い（戦略要約＋3パターンDM等）ため多めに確保
DEFAULT_MAX_TOKENS = 4000


@dataclass
class GenerationResult:
    """1件の生成結果"""
    provider: str  # "gpt" or "gemini"
    prompt_type: str  # "a" or "b"
    message: str
    error: Optional[str] = None


def _get_prompt(provider: str, prompt_type: str) -> str:
    """
    プロバイダー・プロンプト種別に応じたプロンプトを返す。
    環境変数で上書き可能（DM_ASSISTANT_PROMPT_GPT_A 等）。
    """
    key = f"DM_ASSISTANT_PROMPT_{provider.upper()}_{prompt_type.upper()}"
    default = {
        ("gpt", "a"): PROMPT_GPT_A,
        ("gpt", "b"): PROMPT_GPT_B,
        ("gemini", "a"): PROMPT_GEMINI_A,
        ("gemini", "b"): PROMPT_GEMINI_B,
    }.get((provider, prompt_type), "")
    return getattr(settings, key, None) or default


def _call_gpt(client_info: str, prompt_template: str, prompt_type: str) -> GenerationResult:
    """OpenAI (ChatGPT) API を呼び出し"""
    try:
        from openai import OpenAI
    except ImportError:
        return GenerationResult(
            provider="gpt",
            prompt_type=prompt_type,
            message="",
            error="openai パッケージがインストールされていません。",
        )

    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key:
        return GenerationResult(
            provider="gpt",
            prompt_type=prompt_type,
            message="",
            error="OPENAI_API_KEY が設定されていません。",
        )

    model = getattr(settings, "OPENAI_DM_MODEL", "gpt-4o-mini")
    max_tokens = getattr(settings, "OPENAI_DM_MAX_TOKENS", DEFAULT_MAX_TOKENS)
    user_content = f"以下のクライアント情報を元に、上記のルールに従ってDMを生成してください。\n\n---\nクライアント情報:\n{client_info}"

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return GenerationResult(
            provider="gpt",
            prompt_type=prompt_type,
            message=(content or "").strip(),
        )
    except Exception as e:
        logger.exception("OpenAI API error for prompt %s", prompt_type)
        err_str = str(e)
        if "429" in err_str or "quota" in err_str.lower() or "insufficient_quota" in err_str.lower():
            error_msg = (
                "API利用上限に達しました。OpenAIのプラン・請求設定を確認してください。"
                " https://platform.openai.com/account/billing"
            )
        else:
            error_msg = err_str
        return GenerationResult(
            provider="gpt",
            prompt_type=prompt_type,
            message="",
            error=error_msg,
        )


def _call_gemini(client_info: str, prompt_template: str, prompt_type: str) -> GenerationResult:
    """Google Gemini API を呼び出し"""
    import warnings

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            import google.generativeai as genai
    except ImportError:
        return GenerationResult(
            provider="gemini",
            prompt_type=prompt_type,
            message="",
            error="google-generativeai パッケージがインストールされていません。",
        )

    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not api_key:
        return GenerationResult(
            provider="gemini",
            prompt_type=prompt_type,
            message="",
            error="GEMINI_API_KEY が設定されていません。",
        )

    model_name = getattr(settings, "GEMINI_DM_MODEL", "gemini-2.0-flash")
    max_tokens = getattr(settings, "GEMINI_DM_MAX_TOKENS", DEFAULT_MAX_TOKENS)
    user_content = f"""{prompt_template}

---

以下のクライアント情報を元に、上記のルールに従ってDMを生成してください。

クライアント情報:
{client_info}"""

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            user_content,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=max_tokens,
            ),
        )
        text = response.text if response.text else ""
        return GenerationResult(
            provider="gemini",
            prompt_type=prompt_type,
            message=text.strip(),
        )
    except Exception as e:
        logger.exception("Gemini API error for prompt %s", prompt_type)
        err_str = str(e)
        if "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in err_str:
            error_msg = (
                "API利用上限に達しました。Geminiの無料枠制限または請求設定を確認してください。"
                " https://ai.google.dev/gemini-api/docs/rate-limits"
            )
        else:
            error_msg = err_str
        return GenerationResult(
            provider="gemini",
            prompt_type=prompt_type,
            message="",
            error=error_msg,
        )


def generate_dm_messages(client_info: str) -> list[GenerationResult]:
    """
    クライアント情報をもとに、4つのDM文面を並列で生成する。

    Returns:
        [GPT-A, GPT-B, Gemini-A, Gemini-B] の順の結果リスト
    """
    client_info = (client_info or "").strip()
    if not client_info:
        return [
            GenerationResult(provider="gpt", prompt_type="a", message="", error="クライアント情報を入力してください。"),
            GenerationResult(provider="gpt", prompt_type="b", message="", error="クライアント情報を入力してください。"),
            GenerationResult(provider="gemini", prompt_type="a", message="", error="クライアント情報を入力してください。"),
            GenerationResult(provider="gemini", prompt_type="b", message="", error="クライアント情報を入力してください。"),
        ]

    tasks = [
        ("gpt", "a"),
        ("gpt", "b"),
        ("gemini", "a"),
        ("gemini", "b"),
    ]

    def run_one(task: tuple[str, str]) -> GenerationResult:
        provider, prompt_type = task
        prompt_template = _get_prompt(provider, prompt_type)
        if provider == "gpt":
            return _call_gpt(client_info, prompt_template, prompt_type)
        return _call_gemini(client_info, prompt_template, prompt_type)

    results: dict[tuple[str, str], GenerationResult] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_task = {executor.submit(run_one, t): t for t in tasks}
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results[(result.provider, result.prompt_type)] = result
            except Exception as e:
                provider, prompt_type = task
                results[(provider, prompt_type)] = GenerationResult(
                    provider=provider,
                    prompt_type=prompt_type,
                    message="",
                    error=str(e),
                )

    # 固定順: GPT-A, GPT-B, Gemini-A, Gemini-B
    order = [("gpt", "a"), ("gpt", "b"), ("gemini", "a"), ("gemini", "b")]
    return [results.get(k, GenerationResult(provider=k[0], prompt_type=k[1], message="", error="未取得")) for k in order]
