from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SearchContextSize = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float
    request_fee_by_context: dict[SearchContextSize, float]


# NOTE:
# この価格は Perplexity の公開ドキュメントに基づく「推定」。
# 実際の請求は端数処理・内部計算等により完全一致しない可能性がある。
_PRICING: dict[str, ModelPricing] = {
    # https://docs.perplexity.ai/getting-started/models/models/sonar
    "sonar": ModelPricing(
        input_per_million=1.0,
        output_per_million=1.0,
        request_fee_by_context={"low": 0.005, "medium": 0.008, "high": 0.012},
    ),
    # https://docs.perplexity.ai/getting-started/models/models/sonar-pro
    "sonar-pro": ModelPricing(
        input_per_million=3.0,
        output_per_million=15.0,
        request_fee_by_context={"low": 0.006, "medium": 0.010, "high": 0.014},
    ),
}


def estimate_powerplexy_cost_usd(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    search_context_size: SearchContextSize = "low",
) -> float | None:
    """
    Perplexity API の usage を元に、1リクエストあたりの推定コスト(USD)を算出する。
    - token単価（入力/出力）
    - リクエスト課金（search_context_size）

    返り値は「推定」。取得できない場合は None。
    """
    pricing = _PRICING.get(model)
    if pricing is None:
        return None

    if prompt_tokens < 0 or completion_tokens < 0:
        return None

    input_cost = (prompt_tokens / 1_000_000.0) * pricing.input_per_million
    output_cost = (completion_tokens / 1_000_000.0) * pricing.output_per_million
    request_fee = pricing.request_fee_by_context.get(search_context_size)
    if request_fee is None:
        return None
    return float(input_cost + output_cost + request_fee)

