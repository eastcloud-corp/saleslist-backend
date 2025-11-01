from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Set, Tuple

import requests
import yaml
from django.conf import settings
from .review_ingestion import ingest_rule_based_candidates

logger = logging.getLogger(__name__)


PREFECTURES = [
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
]

@dataclass
class OpenDataSourceConfig:
    key: str
    label: str
    url: str
    file_format: str
    encoding: str
    delimiter: str = ","
    source_detail: str = ""
    mappings: Mapping[str, str] = None

    @classmethod
    def from_dict(cls, key: str, data: Mapping[str, object]) -> "OpenDataSourceConfig":
        return cls(
            key=key,
            label=str(data.get("label", key)),
            url=str(data.get("url")),
            file_format=str(data.get("format", "csv")),
            encoding=str(data.get("encoding", "utf-8")),
            delimiter=str(data.get("delimiter", ",")),
            source_detail=str(data.get("source_detail", key)),
            mappings=data.get("mappings", {}) or {},
        )


def _normalize_string(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_corporate_number(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _normalize_phone(value: Optional[str]) -> str:
    if not value:
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits


def _normalize_integer(value: Optional[str]) -> str:
    if value is None:
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits


def _split_address(value: str) -> Tuple[str, str]:
    if not value:
        return "", ""
    text = value.strip()
    for pref in PREFECTURES:
        if text.startswith(pref):
            return pref, text[len(pref) :].strip()
    return "", text


@lru_cache
def load_opendata_configs() -> Mapping[str, OpenDataSourceConfig]:
    path = settings.BASE_DIR / "config" / "opendata_sources.yaml"
    try:
        with path.open("r", encoding="utf-8") as fp:
            raw = yaml.safe_load(fp) or {}
    except FileNotFoundError:
        logger.warning("Open data config not found: %s", path)
        return {}

    sources = raw.get("sources", {}) or {}
    configs = {}
    for key, value in sources.items():
        try:
            configs[key] = OpenDataSourceConfig.from_dict(key, value)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Invalid open data config for key=%s: %s", key, exc)
    return configs


def _iter_csv_rows(content: bytes, config: OpenDataSourceConfig) -> Iterator[Mapping[str, str]]:
    text_stream = io.StringIO(content.decode(config.encoding, errors="replace"))
    reader = csv.DictReader(text_stream, delimiter=config.delimiter)
    for row in reader:
        yield {key: (value.strip() if isinstance(value, str) else value) for key, value in row.items()}


def _iter_zip_csv_rows(content: bytes, config: OpenDataSourceConfig) -> Iterator[Mapping[str, str]]:
    from zipfile import ZipFile

    with ZipFile(io.BytesIO(content)) as zip_file:
        csv_name = None
        for name in zip_file.namelist():
            if name.lower().endswith(".csv"):
                csv_name = name
                break
        if not csv_name:
            raise ValueError("ZIP 内に CSV ファイルが見つかりません。")
        with zip_file.open(csv_name) as member:
            reader = csv.DictReader(
                io.TextIOWrapper(member, encoding=config.encoding, newline=""),
                delimiter=config.delimiter,
            )
            for row in reader:
                yield {key: (value.strip() if isinstance(value, str) else value) for key, value in row.items()}


def fetch_source_rows(config: OpenDataSourceConfig) -> Iterable[Mapping[str, str]]:
    response = requests.get(config.url, timeout=60)
    response.raise_for_status()

    if config.file_format == "zip_csv":
        return _iter_zip_csv_rows(response.content, config)
    if config.file_format == "csv":
        return _iter_csv_rows(response.content, config)
    raise ValueError(f"Unsupported format: {config.file_format}")


def build_rule_entries_from_row(
    *,
    config: OpenDataSourceConfig,
    row: Mapping[str, str],
) -> Tuple[Optional[str], List[dict]]:
    corporate_number_col = config.mappings.get("corporate_number")
    name_col = config.mappings.get("name")
    corporate_number = _normalize_corporate_number(row.get(corporate_number_col)) if corporate_number_col else ""
    company_name = _normalize_string(row.get(name_col)) if name_col else ""

    entries: List[dict] = []
    metadata = {
        "source": config.source_detail,
        "label": config.label,
        "row": row,
    }

    def push(field_key: str, value: Optional[str]) -> None:
        normalized = _normalize_string(value)
        if not normalized:
            return
        entries.append(
            {
                "field": field_key,
                "value": normalized,
                "source": config.source_detail,
                "source_detail": config.source_detail,
                "source_type": "RULE",
                "confidence": 100,
                "metadata": metadata,
            }
        )

    address_col = config.mappings.get("address")
    prefecture_col = config.mappings.get("prefecture")
    city_col = config.mappings.get("city")

    if address_col and not prefecture_col:
        prefecture, city = _split_address(_normalize_string(row.get(address_col)))
        if prefecture:
            push("prefecture", prefecture)
        if city:
            push("city", city)
    else:
        if prefecture_col:
            push("prefecture", row.get(prefecture_col))
        address_value = row.get(city_col) if city_col else row.get(address_col)
        if address_value:
            push("city", address_value)

    capital_col = config.mappings.get("capital_stock")
    if capital_col:
        push("capital", _normalize_integer(row.get(capital_col)))

    employee_col = config.mappings.get("employee_size")
    if employee_col:
        push("employee_count", _normalize_integer(row.get(employee_col)))

    industry_col = config.mappings.get("industry")
    if industry_col:
        push("industry", row.get(industry_col))

    phone_col = config.mappings.get("phone_number")
    if phone_col:
        push("phone", _normalize_phone(row.get(phone_col)))

    website_col = config.mappings.get("website_url")
    if website_col:
        website = _normalize_string(row.get(website_col))
        if website and not website.lower().startswith(("http://", "https://")):
            website = f"https://{website}"
        push("website_url", website)

    return (corporate_number or (company_name if company_name else None), entries)


def ingest_opendata_sources(
    *,
    source_keys: Optional[Sequence[str]] = None,
    company_ids: Optional[Sequence[int]] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    config_map: Optional[Mapping[str, OpenDataSourceConfig]] = None,
) -> Dict[str, object]:
    configs = config_map or load_opendata_configs()
    if not configs:
        return {
            "processed_sources": 0,
            "rows": 0,
            "matched": 0,
            "created": 0,
            "skipped_no_config": True,
        }

    from companies.models import Company

    targets: List[OpenDataSourceConfig] = []
    if source_keys:
        for key in source_keys:
            cfg = configs.get(key)
            if not cfg:
                logger.warning("指定されたオープンデータソースが見つかりません: %s", key)
                continue
            targets.append(cfg)
    else:
        targets = list(configs.values())

    if not targets:
        return {
            "processed_sources": 0,
            "rows": 0,
            "matched": 0,
            "created": 0,
            "dry_run": dry_run,
            "skipped_no_source": True,
        }

    allowed_company_ids: Optional[Set[int]] = None
    if company_ids:
        allowed_company_ids = {int(company_id) for company_id in company_ids}

    rows_processed = 0
    companies_matched = 0
    created_items_total: List = []
    entries_buffer: List[dict] = []

    for source_config in targets:
        try:
            rows_iter = fetch_source_rows(source_config)
        except Exception as exc:
            logger.warning("Failed to fetch source=%s: %s", source_config.key, exc)
            continue

        for row in rows_iter:
            if limit and rows_processed >= limit:
                break
            rows_processed += 1

            corporate_key, entries = build_rule_entries_from_row(config=source_config, row=row)
            if not entries:
                continue

            company: Optional[Company] = None
            queryset_filters = {}
            if allowed_company_ids is not None:
                queryset_filters["id__in"] = allowed_company_ids

            if corporate_key:
                normalized_key = _normalize_corporate_number(corporate_key)
                if normalized_key:
                    query = Company.objects.filter(corporate_number=normalized_key)
                    if queryset_filters:
                        query = query.filter(**queryset_filters)
                    company = query.first()

            if company is None and corporate_key and not corporate_key.isdigit():
                query = Company.objects.filter(name=corporate_key)
                if queryset_filters:
                    query = query.filter(**queryset_filters)
                company = query.first()

            if not company:
                continue

            companies_matched += 1

            for entry in entries:
                entry["company_id"] = company.id
                entries_buffer.append(entry)

        if limit and rows_processed >= limit:
            break

    created_items = []
    if entries_buffer and not dry_run:
        created_items = ingest_rule_based_candidates(entries_buffer)
        created_items_total.extend(created_items)

    return {
        "processed_sources": len(targets),
        "rows": rows_processed,
        "matched": companies_matched,
        "created": len(created_items_total),
        "dry_run": dry_run,
    }
