from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

_NON_NUMERIC_TOKENS = {"未公開", "不明", "不詳", "なし", "N/A", "n/a", "-", "―"}
_ROLE_PREFIXES = {"代表取締役", "代表取締役社長", "取締役", "社長", "CEO", "COO", "CTO"}


def _normalize_established_year(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return None

    # 和暦対応
    era_match = re.search(r"(令和|平成)(\d{1,2})年?", text)
    if era_match:
        era, num_str = era_match.groups()
        try:
            era_year = int(num_str)
        except ValueError:
            era_year = None
        if era_year:
            base_year = 2018 if era == "令和" else 1988  # 令和1=2019, 平成1=1989
            western_year = base_year + era_year
            return str(western_year)

    year_match = re.search(r"(19|20)\d{2}", text)
    if year_match:
        return year_match.group(0)

    digits = re.findall(r"\d+", text)
    if digits:
        combined = "".join(digits)
        if len(combined) >= 4:
            return combined[:4]

    return None


def _normalize_capital(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return None

    lowered = text.lower()
    if any(token.lower() in lowered for token in _NON_NUMERIC_TOKENS):
        return None

    cleaned = re.sub(r"[,\s]", "", text)
    cleaned = cleaned.replace("円", "")

    total = Decimal(0)
    matched = False

    pattern = re.compile(r"(?P<number>\d+(?:\.\d+)?)(?P<unit>億|万)?")
    for match in pattern.finditer(cleaned):
        number = match.group("number")
        unit = match.group("unit")
        if not number:
            continue
        try:
            num = Decimal(number)
        except InvalidOperation:
            continue

        if unit == "億":
            multiplier = Decimal(100_000_000)
        elif unit == "万":
            multiplier = Decimal(10_000)
        else:
            multiplier = Decimal(1)

        total += num * multiplier
        matched = True

    if not matched:
        digits = re.findall(r"\d+", cleaned)
        if digits:
            try:
                total = Decimal("".join(digits))
                matched = True
            except InvalidOperation:
                matched = False

    if not matched:
        return None

    if total < 0:
        return None

    return str(int(total))


def _normalize_contact_person_name(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return None

    text = re.sub(r"[（(].*?[）)]", "", text)
    for prefix in _ROLE_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
            break

    text = re.sub(r"\s+", " ", text)
    text = text.replace("　", " ").strip()
    return text or None


def _normalize_contact_person_position(value: str) -> Optional[str]:
    text = re.sub(r"[（(].*?[）)]", "", value).strip()
    if not text:
        return None

    for sep in ("／", "/", "・", "，", ","):
        if sep in text:
            text = text.split(sep, 1)[0].strip()

    for space in ("　", " "):
        if space in text:
            text = text.split(space, 1)[0].strip()

    return text or None


_NORMALIZER_MAP: dict[str, Callable[[str], Optional[str]]] = {
    "established_year": _normalize_established_year,
    "capital": _normalize_capital,
    "contact_person_name": _normalize_contact_person_name,
    "contact_person_position": _normalize_contact_person_position,
}


def normalize_candidate_value(field: str, value: object) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    normalizer = _NORMALIZER_MAP.get(field)
    if normalizer:
        try:
            normalized = normalizer(text)
        except Exception:  # pragma: no cover - フォールバック
            normalized = None
        if normalized:
            return normalized.strip()
        return None

    # default: collapse whitespace
    text = re.sub(r"\s+", " ", text.replace("　", " ")).strip()
    return text or None
