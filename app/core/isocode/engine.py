import re

from .constants import (
    AXIS_CODES,
    DATA_TYPES,
    DUMMY_TYPES,
    FILTER_CODE_TO_LABEL,
    FILTER_LABEL_TO_CODE,
    FINE_LOCATION_LEVEL,
    FINE_LOCATION_SIDE,
    MAIN_LOCATION_TOKENS,
    POSITION_ALIASES,
)
from .models import ParsedIsoCode


ISOCODE_TOKEN_RE = re.compile(r'(?<![A-Z0-9])([A-Z0-9]{16})(?![A-Z0-9])')
RAW_TEXT_SPLIT_RE = re.compile(r'[^A-Z0-9]+')


def normalize_dummy_position(value):
    text = str(value or '').strip().upper()
    return POSITION_ALIASES.get(text, '')


def normalize_filter_label_to_code(filter_label):
    label = str(filter_label or '').strip()
    if not label:
        return ''
    direct = FILTER_LABEL_TO_CODE.get(label, '')
    if direct:
        return direct
    upper = label.upper()
    for key, value in FILTER_LABEL_TO_CODE.items():
        if str(key).upper() == upper:
            return value
    return ''


def normalize_filter_code_to_label(filter_code):
    code = str(filter_code or '').strip().upper()
    if not code:
        return ''
    return FILTER_CODE_TO_LABEL.get(code, '')


def rewrite_filter_code(raw_code, filter_label):
    code = str(raw_code or '').strip().upper()
    if len(code) != 16:
        return code
    mapped = normalize_filter_label_to_code(filter_label)
    if not mapped:
        return code
    return f'{code[:-1]}{mapped}'


def rewrite_filter_code_in_text(text, filter_label, raw_code=''):
    source = str(text or '')
    if not source:
        return source

    if raw_code:
        rewritten_raw = rewrite_filter_code(raw_code, filter_label)
        if len(raw_code) == 16 and rewritten_raw and raw_code in source:
            return source.replace(raw_code, rewritten_raw, 1)

    def _replace(match):
        token = match.group(1)
        rewritten = rewrite_filter_code(token, filter_label)
        return rewritten or token

    return ISOCODE_TOKEN_RE.sub(_replace, source, count=1)


def _tokenize_text(*parts):
    items = []
    for part in parts:
        for token in RAW_TEXT_SPLIT_RE.split(str(part or '').upper()):
            token = token.strip()
            if token:
                items.append(token)
    return items


def _sensor_location_from_main(main_code):
    info = MAIN_LOCATION_TOKENS.get(str(main_code or '').upper(), {})
    return str(info.get('sensor_location') or '').strip()


def _build_tokens(parsed):
    tokens = []
    for value in (
        parsed.dummy_position_normalized,
        parsed.mount_type,
        parsed.main_location_code,
        parsed.fine_location_1,
        parsed.fine_location_2,
        parsed.dummy_type_code,
        parsed.dummy_type_label,
        parsed.data_type_code,
        parsed.data_type_label,
        parsed.axis_code,
        parsed.axis_label,
        parsed.sensor_location,
        parsed.side,
        parsed.level,
        parsed.position_detail,
        parsed.filter_label_source,
    ):
        text = str(value or '').strip().lower()
        if text and text not in tokens:
            tokens.append(text)
    return tokens


def parse_isocode(raw_code):
    code = str(raw_code or '').strip().upper()
    parsed = ParsedIsoCode(raw_code=code, matched_code=code, source='raw', parse_mode='strict')
    if len(code) != 16:
        parsed.notes.append('length_not_16')
        return parsed

    dummy_position = code[0:2]
    main_location = code[2:6]
    fine_1 = code[6:8]
    fine_2 = code[8:10]
    dummy_type = code[10:12]
    data_type = code[12:14]
    axis = code[14:15]
    filter_code = code[15:16]

    parsed.dummy_position_raw = dummy_position
    parsed.dummy_position_normalized = normalize_dummy_position(dummy_position)
    parsed.mount_type = 'vehicle' if parsed.dummy_position_normalized == 'B0' else 'dummy' if parsed.dummy_position_normalized else ''
    parsed.main_location_code = main_location
    parsed.fine_location_1 = fine_1
    parsed.fine_location_2 = fine_2
    parsed.redundant_index = fine_2 if fine_2.isdigit() else ''
    parsed.dummy_type_code = dummy_type
    parsed.dummy_type_label = DUMMY_TYPES.get(dummy_type, '')
    parsed.data_type_code = data_type
    parsed.data_type_label = DATA_TYPES.get(data_type, '')
    parsed.axis_code = axis
    parsed.axis_label = AXIS_CODES.get(axis, '')
    parsed.filter_code_source = filter_code
    parsed.filter_label_source = normalize_filter_code_to_label(filter_code)
    parsed.sensor_location = _sensor_location_from_main(main_location)

    if fine_1 in FINE_LOCATION_SIDE:
        parsed.side = FINE_LOCATION_SIDE[fine_1]
    if fine_1 in FINE_LOCATION_LEVEL:
        parsed.level = FINE_LOCATION_LEVEL[fine_1]
    if fine_2 in FINE_LOCATION_SIDE and not parsed.side:
        parsed.side = FINE_LOCATION_SIDE[fine_2]
    if fine_2 in FINE_LOCATION_LEVEL and not parsed.level:
        parsed.level = FINE_LOCATION_LEVEL[fine_2]

    if main_location == 'CLEV':
        parsed.position_detail = 'clevis'
    elif fine_1 == 'CG':
        parsed.position_detail = 'cg'
    elif fine_1 == 'CL':
        parsed.position_detail = 'clevis'
    elif fine_1 in FINE_LOCATION_SIDE:
        parsed.position_detail = ''
    elif fine_1:
        parsed.position_detail = fine_1.lower()

    # Preserve inner/outer detail when the primary side token already consumes LE/RI.
    if fine_2 in ('IN', 'OU'):
        parsed.position_detail = FINE_LOCATION_SIDE[fine_2]
    elif not parsed.position_detail and fine_2 == 'CL':
        parsed.position_detail = 'clevis'

    if not parsed.sensor_location and main_location:
        parsed.sensor_location = main_location.lower()

    parsed.parse_confidence = 1.0 if parsed.dummy_position_normalized and parsed.data_type_label else 0.8
    parsed.tokens = _build_tokens(parsed)
    return parsed


def infer_channel_identity(channel_name, description='', unit=''):
    candidates = []
    seen = set()
    for text in (str(channel_name or '').upper(), str(description or '').upper()):
        for match in ISOCODE_TOKEN_RE.finditer(text):
            code = match.group(1)
            if code not in seen:
                seen.add(code)
                candidates.append(code)
        compact = ''.join(ch for ch in text if ch.isalnum())
        if len(compact) == 16 and compact not in seen:
            seen.add(compact)
            candidates.append(compact)

    for code in candidates:
        parsed = parse_isocode(code)
        if parsed.parse_confidence >= 0.8:
            parsed.source = 'isocode'
            return parsed

    text_tokens = _tokenize_text(channel_name, description, unit)
    parsed = ParsedIsoCode(
        raw_code='',
        matched_code='',
        source='description',
        parse_mode='fallback',
        parse_confidence=0.35,
    )

    for token in text_tokens:
        norm_pos = normalize_dummy_position(token)
        if norm_pos and not parsed.dummy_position_normalized:
            parsed.dummy_position_raw = token
            parsed.dummy_position_normalized = norm_pos
            parsed.mount_type = 'vehicle' if norm_pos == 'B0' else 'dummy'
        if token in DUMMY_TYPES and not parsed.dummy_type_code:
            parsed.dummy_type_code = token
            parsed.dummy_type_label = DUMMY_TYPES.get(token, '')
        if token in DATA_TYPES and not parsed.data_type_code:
            parsed.data_type_code = token
            parsed.data_type_label = DATA_TYPES.get(token, '')
        if token in AXIS_CODES and not parsed.axis_code:
            parsed.axis_code = token
            parsed.axis_label = AXIS_CODES.get(token, '')
        if token in MAIN_LOCATION_TOKENS and not parsed.main_location_code:
            parsed.main_location_code = token
            parsed.sensor_location = _sensor_location_from_main(token)
        if token in FINE_LOCATION_SIDE and not parsed.side:
            parsed.side = FINE_LOCATION_SIDE[token]
        if token in FINE_LOCATION_LEVEL and not parsed.level:
            parsed.level = FINE_LOCATION_LEVEL[token]

    low_text = ' '.join(text_tokens).lower()
    for keyword, value in (
        ('head', 'head'),
        ('neck', 'neck'),
        ('chest', 'chest'),
        ('thor', 'chest'),
        ('pelvis', 'pelvis'),
        ('iliac', 'iliac'),
        ('femur', 'femur'),
        ('knee', 'knee'),
        ('tibia', 'tibia'),
    ):
        if keyword in low_text and not parsed.sensor_location:
            parsed.sensor_location = value
            break
    if 'left' in low_text and not parsed.side:
        parsed.side = 'left'
    if 'right' in low_text and not parsed.side:
        parsed.side = 'right'
    if 'upper' in low_text and not parsed.level:
        parsed.level = 'upper'
    if 'lower' in low_text and not parsed.level:
        parsed.level = 'lower'
    if 'inner' in low_text and not parsed.position_detail:
        parsed.position_detail = 'inner'
    if 'outer' in low_text and not parsed.position_detail:
        parsed.position_detail = 'outer'
    if 'clevis' in low_text and not parsed.position_detail:
        parsed.position_detail = 'clevis'

    parsed.tokens = _build_tokens(parsed)
    return parsed


def infer_managed_isocode(channel_name, description='', unit='', filter_label='Raw', raw_code='', source_channel_code=''):
    candidate = str(raw_code or '').strip().upper()
    if not candidate and source_channel_code:
        candidate = str(source_channel_code).strip().upper()
    if not candidate:
        parsed = infer_channel_identity(channel_name, description=description, unit=unit)
        candidate = parsed.matched_code or parsed.raw_code
    return rewrite_filter_code(candidate, filter_label) if candidate else ''


def resolve_root_source_channel(channel_name, derived_channels=None):
    derived_channels = dict(derived_channels or {})
    current = str(channel_name or '').strip()
    seen = set()
    while current and current not in seen:
        seen.add(current)
        info = dict(derived_channels.get(current) or {})
        source = str(info.get('source_channel') or '').strip()
        if not source:
            break
        current = source
    return current


def _build_filter_history(channel_name, filter_label, derived_info, derived_channels):
    history = []
    source = str((derived_info or {}).get('source_channel') or '').strip()
    if source:
        source_info = dict((derived_channels or {}).get(source) or {})
        history.append({
            'from_channel': source,
            'from_filter_label': str(source_info.get('required_cfc') or source_info.get('display_filter_label') or source_info.get('filter_label') or '').strip() or 'Raw',
            'to_filter_label': str(filter_label or '').strip() or 'Raw',
            'raw_based': bool((derived_info or {}).get('created_from_raw')),
            'purpose': str((derived_info or {}).get('purpose') or '').strip(),
            'role': str((derived_info or {}).get('role') or '').strip(),
        })
    return history


def build_isocode_metadata(columns, descriptions=None, units=None, filter_labels=None, existing_raw_map=None, derived_channels=None):
    descriptions = dict(descriptions or {})
    units = dict(units or {})
    filter_labels = dict(filter_labels or {})
    existing_raw_map = dict(existing_raw_map or {})
    derived_channels = dict(derived_channels or {})

    raw_map = {}
    managed_map = {}
    parsed_map = {}
    display_tokens = {}

    for channel in columns:
        raw_code = str(existing_raw_map.get(channel) or '').strip().upper()
        source_channel = str((derived_channels.get(channel) or {}).get('source_channel') or '').strip()
        source_raw = str(existing_raw_map.get(source_channel) or '').strip().upper() if source_channel else ''
        parsed = infer_channel_identity(channel, descriptions.get(channel, ''), units.get(channel, ''))
        if raw_code:
            parsed = parse_isocode(raw_code)
            parsed.source = 'metadata'
        elif parsed.matched_code and len(parsed.matched_code) == 16:
            raw_code = parsed.matched_code
        raw_map[channel] = raw_code

        derived_info = dict(derived_channels.get(channel) or {})
        effective_filter_label = (
            str(derived_info.get('required_cfc') or '').strip()
            or str(derived_info.get('display_filter_label') or '').strip()
            or str(derived_info.get('filter_label') or '').strip()
            or str(filter_labels.get(channel) or '').strip()
            or 'Raw'
        )
        if effective_filter_label == 'CALC':
            effective_filter_label = str(filter_labels.get(channel) or 'Raw').strip() or 'Raw'

        managed_code = infer_managed_isocode(
            channel,
            description=descriptions.get(channel, ''),
            unit=units.get(channel, ''),
            filter_label=effective_filter_label,
            raw_code=raw_code,
            source_channel_code=source_raw,
        )
        managed_map[channel] = managed_code
        current_parsed = parse_isocode(managed_code) if managed_code and len(managed_code) == 16 else parsed
        if managed_code and len(managed_code) == 16:
            current_parsed.source = 'managed'
            current_parsed.matched_code = managed_code
            current_parsed.raw_code = raw_code or managed_code
        parsed_map[channel] = current_parsed.to_dict()
        display_tokens[channel] = list(current_parsed.tokens)

    return {
        'isocode_raw_map': raw_map,
        'isocode_managed_map': managed_map,
        'isocode_parsed_map': parsed_map,
        'isocode_display_tokens': display_tokens,
    }


def build_channel_metadata_map(columns, descriptions=None, units=None, filter_labels=None, existing_raw_map=None, derived_channels=None):
    descriptions = dict(descriptions or {})
    units = dict(units or {})
    filter_labels = dict(filter_labels or {})
    existing_raw_map = dict(existing_raw_map or {})
    derived_channels = dict(derived_channels or {})

    iso_meta = build_isocode_metadata(
        columns,
        descriptions=descriptions,
        units=units,
        filter_labels=filter_labels,
        existing_raw_map=existing_raw_map,
        derived_channels=derived_channels,
    )
    parsed_map = dict(iso_meta.get('isocode_parsed_map') or {})
    raw_map = dict(iso_meta.get('isocode_raw_map') or {})
    managed_map = dict(iso_meta.get('isocode_managed_map') or {})

    channel_metadata = {}
    for channel in columns:
        derived_info = dict(derived_channels.get(channel) or {})
        current_filter_label = (
            str(derived_info.get('required_cfc') or '').strip()
            or str(derived_info.get('display_filter_label') or '').strip()
            or str(derived_info.get('filter_label') or '').strip()
            or str(filter_labels.get(channel) or '').strip()
            or 'Raw'
        )
        if current_filter_label == 'CALC':
            current_filter_label = str(filter_labels.get(channel) or 'CALC').strip() or 'CALC'

        parsed = dict(parsed_map.get(channel) or {})
        root_source = (
            str(derived_info.get('root_source_channel') or '').strip()
            or resolve_root_source_channel(channel, derived_channels=derived_channels)
            or str(channel)
        )
        source_channel = str(derived_info.get('source_channel') or '').strip()
        raw_isocode = str(raw_map.get(channel) or '').strip().upper()
        managed_isocode = str(managed_map.get(channel) or '').strip().upper()
        current_filter_code = str(parsed.get('filter_code_source') or normalize_filter_label_to_code(current_filter_label) or '').strip().upper()
        filter_history = list(derived_info.get('filter_history') or _build_filter_history(channel, current_filter_label, derived_info, derived_channels))
        source_info = dict(derived_channels.get(source_channel) or {}) if source_channel else {}
        source_filter_label = (
            str(source_info.get('required_cfc') or '').strip()
            or str(source_info.get('display_filter_label') or '').strip()
            or str(source_info.get('filter_label') or '').strip()
            or str(filter_labels.get(source_channel) or '').strip()
            or ('Raw' if source_channel else '')
        )
        sensor_family = str(parsed.get('sensor_location') or '').strip().lower()
        validation = {
            'filter_match': bool(current_filter_code == str(normalize_filter_label_to_code(current_filter_label) or '').strip().upper()) if current_filter_label not in ('', 'CALC') else True,
            'lineage_ok': bool(root_source),
            'raw_alignment_ok': bool(derived_info.get('created_from_raw')) if str(derived_info.get('rebuild_policy') or '').strip() == 'raw_aligned_only' else True,
            'sampling_rate_ok': True,
        }
        channel_metadata[channel] = {
            'channel_name': str(channel),
            'description': str(descriptions.get(channel) or '').strip(),
            'unit': str(units.get(channel) or '').strip(),
            'source_channel': source_channel or None,
            'root_source_channel': root_source or None,
            'lineage_type': 'derived' if derived_info else 'raw',
            'purpose': str(derived_info.get('purpose') or '').strip() or None,
            'role': str(derived_info.get('role') or '').strip() or None,
            'current_filter_label': current_filter_label,
            'current_filter_code': current_filter_code,
            'source_filter_label': source_filter_label or None,
            'required_cfc': str(derived_info.get('required_cfc') or '').strip() or None,
            'display_filter_label': str(derived_info.get('display_filter_label') or '').strip() or None,
            'created_from_raw': bool(derived_info.get('created_from_raw')),
            'rebuild_policy': str(derived_info.get('rebuild_policy') or '').strip() or None,
            'double_filter_safe': not bool(derived_info) or bool(derived_info.get('created_from_raw')),
            'filter_history': filter_history,
            'raw_isocode': raw_isocode,
            'managed_isocode': managed_isocode,
            'isocode_parsed': parsed,
            'dummy_position': str(parsed.get('dummy_position_normalized') or '').strip().upper() or None,
            'sensor_family': sensor_family or None,
            'validation': validation,
        }
    return channel_metadata
