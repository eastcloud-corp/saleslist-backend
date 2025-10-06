import csv
import io
import re
from collections import defaultdict
from typing import IO, Any, Dict, Tuple, Optional

from .models import Company, Executive


def import_companies_csv(file_obj: IO[bytes]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """CSVデータから企業／担当者情報を取り込む。成功時は結果dictとNoneを返し、
    バリデーションエラー時はNoneとエラーpayloadを返す。"""

    try:
        raw_data = file_obj.read()
        if isinstance(raw_data, bytes):
            csv_text = raw_data.decode('utf-8')
        else:
            csv_text = raw_data
    finally:
        try:
            file_obj.seek(0)
        except Exception:
            pass

    csv_reader = csv.DictReader(io.StringIO(csv_text))

    if not csv_reader.fieldnames:
        return None, {'error': 'CSVのヘッダーが確認できません'}

    def normalize_header(header: str) -> str:
        if not header:
            return ''

        direct_map = {
            '名前': 'contact_person_name',
            '会社名': 'name',
            '企業名': 'name',
            '法人番号': 'corporate_number',
            '業種': 'industry',
            '従業員数': 'employee_count',
            '従業員数(あれば)': 'employee_count',
            '売上規模': 'revenue',
            '売上規模(あれば)': 'revenue',
            '所在地(都道府県)': 'prefecture',
            '所在地': 'location',
            '会社HP': 'website_url',
            'メールアドレス': 'contact_email',
            '電話番号': 'phone',
            '事業内容': 'business_description',
            '担当者名': 'contact_person_name',
            '役職': 'contact_person_position',
            'Facebookリンク': 'facebook_url',
            'toB toC': 'tob_toc_type',
            '資本金': 'capital',
            '設立年': 'established_year',
            'アポ実績': 'notes',
        }

        header_stripped = header.strip()
        if header_stripped in direct_map:
            return direct_map[header_stripped]

        normalized = re.sub(r"[^a-z0-9]", "_", header_stripped.lower())
        header_map = {
            'company_name': 'name',
            'company': 'name',
            'name': 'name',
            'contact_person_name': 'contact_person_name',
            'contact_name': 'contact_person_name',
            'corporate_number': 'corporate_number',
            'industry': 'industry',
            'employee_count': 'employee_count',
            'employees': 'employee_count',
            'revenue': 'revenue',
            'prefecture': 'prefecture',
            'city': 'city',
            'location': 'location',
            'website_url': 'website_url',
            'website': 'website_url',
            'contact_email': 'contact_email',
            'email': 'contact_email',
            'phone': 'phone',
            'telephone': 'phone',
            'business_description': 'business_description',
            'description': 'business_description',
            'contact_person_name': 'contact_person_name',
            'contact_person_position': 'contact_person_position',
            'facebook_url': 'facebook_url',
            'tob_toc_type': 'tob_toc_type',
            'capital': 'capital',
            'established_year': 'established_year',
            'notes': 'notes',
        }
        return header_map.get(normalized, normalized)

    def parse_int(value: str, field_key: str, field_label: str) -> int:
        if value is None:
            return 0
        cleaned = value.strip()
        if cleaned in {'', '-', 'ー', '—'}:
            return 0
        cleaned = cleaned.replace(',', '')
        if not re.fullmatch(r"-?\d+", cleaned):
            raise ValueError(field_key, cleaned, f"{field_label}は数値で入力してください")
        return int(cleaned)

    def parse_optional_int(value: str, field_key: str, field_label: str):
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned in {'', '-', 'ー', '—'}:
            return None
        return parse_int(value, field_key, field_label)

    whitespace_pattern = re.compile(r"\s+")
    hyphen_pattern = re.compile(r"[-‐‑‒–—―ー－]")

    def normalize_token(value: str) -> str:
        if not value:
            return ''
        lowered = value.strip().lower().replace('　', '')
        lowered = whitespace_pattern.sub('', lowered)
        lowered = hyphen_pattern.sub('', lowered)
        return lowered

    def build_name_location_key(name: str, prefecture: str, city: str, location_text: str) -> Optional[str]:
        normalized_name = normalize_token(name)
        location_source = location_text or f"{prefecture or ''}{city or ''}"
        normalized_location = normalize_token(location_source)
        if normalized_name and normalized_location:
            return f"{normalized_name}|{normalized_location}"
        return None

    def apply_company_updates(company: Company, fields: dict) -> list[str]:
        updated = []
        for field, value in fields.items():
            if field == 'corporate_number':
                if value and getattr(company, field) != value:
                    setattr(company, field, value)
                    updated.append(field)
                continue
            if isinstance(value, str):
                if value == '':
                    continue
            elif value is None:
                continue
            if field in {'contact_person_name', 'contact_person_position', 'facebook_url'} and getattr(company, field):
                continue
            if getattr(company, field) != value:
                setattr(company, field, value)
                updated.append(field)
        return updated

    header_map = {header: normalize_header(header) for header in csv_reader.fieldnames}

    if 'name' not in header_map.values():
        return None, {
            'error': '企業名に対応するヘッダーが見つかりません。"name" または "会社名" 列を追加してください。'
        }

    errors = []
    rows_to_import = []

    for index, row in enumerate(csv_reader, start=2):
        normalized_row = {}
        for original_header, value in row.items():
            normalized_key = header_map.get(original_header, original_header)
            if normalized_key:
                normalized_row[normalized_key] = (value or '').strip()

        raw_name = normalized_row.get('name', '')
        name = raw_name.strip() if raw_name else ''
        if not name:
            name = f"インポート企業（行{index}）"

        raw_corporate_number = normalized_row.get('corporate_number', '').strip()
        corporate_number = re.sub(r'[^0-9]', '', raw_corporate_number)

        try:
            employee_count = parse_optional_int(normalized_row.get('employee_count', ''), 'employee_count', '従業員数')
            revenue = parse_optional_int(normalized_row.get('revenue', ''), 'revenue', '売上規模')
            capital = parse_optional_int(normalized_row.get('capital', ''), 'capital', '資本金')
            established_year = parse_optional_int(normalized_row.get('established_year', ''), 'established_year', '設立年')
        except ValueError as exc:
            field_key, value, message = exc.args
            errors.append({
                'row': index,
                'field': field_key,
                'value': value,
                'message': message,
            })
            continue

        prefecture = normalized_row.get('prefecture', '')
        city = normalized_row.get('city', '')
        location_text = normalized_row.get('location', '')

        tob_toc_raw = normalized_row.get('tob_toc_type', '')
        tob_toc_value = tob_toc_raw if tob_toc_raw in {'toB', 'toC', 'Both'} else ''

        prefecture_value = prefecture[:10] if prefecture else ''

        def trim(value: str, max_length: int) -> str:
            if not value:
                return ''
            return value[:max_length]

        company_fields = {
            'name': trim(name, 255),
            'corporate_number': trim(corporate_number, 13),
            'industry': trim(normalized_row.get('industry', ''), 100),
            'contact_person_name': trim(normalized_row.get('contact_person_name', ''), 100),
            'contact_person_position': trim(normalized_row.get('contact_person_position', ''), 100),
            'facebook_url': trim(normalized_row.get('facebook_url', ''), 500),
            'tob_toc_type': tob_toc_value,
            'business_description': normalized_row.get('business_description', ''),
            'prefecture': prefecture_value,
            'city': trim(city, 100),
            'employee_count': employee_count,
            'revenue': revenue,
            'capital': capital,
            'established_year': established_year,
            'website_url': trim(normalized_row.get('website_url', ''), 500),
            'contact_email': trim(normalized_row.get('contact_email', ''), 254),
            'phone': trim(normalized_row.get('phone', ''), 20),
            'notes': normalized_row.get('notes', ''),
        }

        executive_fields = {
            'name': trim(normalized_row.get('contact_person_name', '').strip(), 100),
            'position': trim(normalized_row.get('contact_person_position', ''), 100),
            'facebook_url': trim(normalized_row.get('facebook_url', ''), 500),
        }

        company_key = None
        if corporate_number:
            company_key = ('corporate_number', corporate_number)
        else:
            name_location_key = build_name_location_key(name, prefecture, city, location_text)
            if name_location_key:
                company_key = ('name_location', name_location_key)

        rows_to_import.append({
            'row_number': index,
            'company_fields': company_fields,
            'executive_fields': executive_fields,
            'company_key': company_key,
            'location_token': location_text,
        })

    if errors:
        return None, {
            'error': 'CSV内容にエラーが見つかりました。該当行を修正してください。',
            'errors': errors,
        }

    imported_count = 0
    company_updated_count = 0
    duplicate_entries = []
    missing_corporate_number_count = 0
    executive_created_count = 0
    executive_updated_count = 0

    corporate_numbers_in_csv = {
        entry['company_fields']['corporate_number']
        for entry in rows_to_import
        if entry['company_fields']['corporate_number']
    }

    existing_companies = Company.objects.filter(
        corporate_number__in=corporate_numbers_in_csv
    )
    existing_map = {
        company.corporate_number: company for company in existing_companies
    }

    company_cache: dict[str, Company] = {}
    executive_cache: dict[int, dict[str, Executive]] = defaultdict(dict)
    seen_corporate_numbers = set()

    for entry in rows_to_import:
        company_fields = entry['company_fields']
        exec_fields = entry['executive_fields']
        company_key = entry['company_key']
        location_token = entry['location_token']

        corporate_number = company_fields.get('corporate_number')
        if corporate_number:
            if corporate_number in seen_corporate_numbers:
                duplicate_entries.append({
                    'row': entry['row_number'],
                    'type': 'csv_duplicate',
                    'corporate_number': corporate_number,
                    'name': company_fields['name'],
                    'reason': '同じCSV内で同一の法人番号が複数回指定されています。'
                })
            else:
                seen_corporate_numbers.add(corporate_number)
        else:
            missing_corporate_number_count += 1

        company = None
        cache_key = None
        if company_key:
            cache_key = f"{company_key[0]}:{company_key[1]}"
            company = company_cache.get(cache_key)

        if not company and company_key:
            if company_key[0] == 'corporate_number':
                company = existing_map.get(company_key[1])
            elif company_key[0] == 'name_location':
                filters = {'name': company_fields['name']}
                if company_fields.get('prefecture'):
                    filters['prefecture'] = company_fields['prefecture']
                if company_fields.get('city'):
                    filters['city'] = company_fields['city']
                company = Company.objects.filter(**filters).order_by('-updated_at').first()

        if not company:
            company = Company.objects.create(**company_fields)
            imported_count += 1
        else:
            updated_fields = apply_company_updates(company, company_fields)
            if updated_fields:
                company.save(update_fields=updated_fields)
                company_updated_count += 1

        if company.corporate_number:
            company_cache[f"corporate_number:{company.corporate_number}"] = company

        name_location_cache_key = build_name_location_key(
            company.name,
            company.prefecture,
            company.city,
            location_token,
        )
        if name_location_cache_key:
            company_cache[f"name_location:{name_location_cache_key}"] = company
        if cache_key:
            company_cache[cache_key] = company

        executive_name = exec_fields.get('name')
        if executive_name:
            normalized_exec_name = executive_name.strip()
            exec_cache = executive_cache[company.id]
            exec_obj = exec_cache.get(normalized_exec_name.lower())
            if not exec_obj:
                exec_obj = company.executives.filter(name=normalized_exec_name).first()

            if exec_obj:
                updated_exec_fields = []
                if exec_fields.get('position') and exec_obj.position != exec_fields['position']:
                    exec_obj.position = exec_fields['position']
                    updated_exec_fields.append('position')
                if exec_fields.get('facebook_url') and exec_obj.facebook_url != exec_fields['facebook_url']:
                    exec_obj.facebook_url = exec_fields['facebook_url']
                    updated_exec_fields.append('facebook_url')
                if updated_exec_fields:
                    exec_obj.save(update_fields=updated_exec_fields)
                    executive_updated_count += 1
            else:
                exec_obj = Executive.objects.create(
                    company=company,
                    name=normalized_exec_name,
                    position=exec_fields.get('position', ''),
                    facebook_url=exec_fields.get('facebook_url', ''),
                )
                executive_created_count += 1
            exec_cache[normalized_exec_name.lower()] = exec_obj

    result_payload = {
        'message': f'{imported_count}件の企業を登録しました',
        'imported_count': imported_count,
        'company_updated_count': company_updated_count,
        'total_rows': len(rows_to_import),
        'duplicate_count': len(duplicate_entries),
        'duplicates': duplicate_entries,
        'missing_corporate_number_count': missing_corporate_number_count,
        'executive_created_count': executive_created_count,
        'executive_updated_count': executive_updated_count,
    }

    return result_payload, None
