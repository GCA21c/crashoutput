import math

VALUE_DECIMALS = 4
TIME_DECIMALS = 1
TIME_UNIT = "ms"
SUMMARY_FORMAT_VERSION = 2


def _to_finite_float(value):
    if value is None:
        return None
    try:
        value = float(value)
    except Exception:
        return None
    return value if math.isfinite(value) else None


def fmt_time_ms(value, decimals=TIME_DECIMALS):
    value = _to_finite_float(value)
    if value is None:
        return "-"
    return f"{value * 1000.0:.{decimals}f}{TIME_UNIT}"


def fmt_range_ms(start_value, end_value, decimals=TIME_DECIMALS):
    start_text = fmt_time_ms(start_value, decimals)
    end_text = fmt_time_ms(end_value, decimals)
    if start_text == "-" or end_text == "-":
        return "-"
    return f"{start_text} ~ {end_text}"


def fmt_at_ms(value, decimals=TIME_DECIMALS):
    text = fmt_time_ms(value, decimals)
    return "-" if text == "-" else f"at {text}"


def fmt_value(value, unit='', decimals=VALUE_DECIMALS, unit_style='suffix'):  # suffix => 값단위
    value = _to_finite_float(value)
    if value is None:
        return '-'
    text = f"{value:.{decimals}f}"
    if not unit:
        return text
    if unit_style == 'paren':
        return f"{text}({unit})"
    if unit_style == 'suffix_space':
        return f"{text} {unit}"
    return f"{text}{unit}"


def fmt_metric_at(label, value, unit='', time_s=None, value_decimals=VALUE_DECIMALS, time_decimals=TIME_DECIMALS):
    value_text = fmt_value(value, unit, decimals=value_decimals, unit_style='suffix')
    time_text = fmt_at_ms(time_s, decimals=time_decimals)
    return f"{label}: {value_text} {time_text}" if time_text != '-' else f"{label}: {value_text}"


def fmt_metric_range(label, value, unit='', start_s=None, end_s=None, value_decimals=VALUE_DECIMALS, time_decimals=TIME_DECIMALS):
    value_text = fmt_value(value, unit, decimals=value_decimals, unit_style='suffix')
    range_text = fmt_range_ms(start_s, end_s, decimals=time_decimals)
    return f"{label}: {value_text} ({range_text})" if range_text != '-' else f"{label}: {value_text}"


def fmt_peak_line(prefix, kind, value, unit='', time_s=None, value_decimals=VALUE_DECIMALS, time_decimals=TIME_DECIMALS):
    return fmt_metric_at(f"{prefix} {kind}", value, unit=unit, time_s=time_s, value_decimals=value_decimals, time_decimals=time_decimals)
