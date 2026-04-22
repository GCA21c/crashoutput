from __future__ import annotations


def read_path(container, path):
    current = container
    parts = [part for part in str(path or "").split(".") if part]
    if isinstance(current, dict):
        flat_key = ".".join(parts)
        if flat_key in current:
            return current.get(flat_key)
    index = 0
    while index < len(parts):
        if not isinstance(current, dict):
            return None
        remaining = ".".join(parts[index:])
        if remaining in current:
            return current.get(remaining)
        matched = False
        for end in range(len(parts), index, -1):
            candidate = ".".join(parts[index:end])
            if candidate in current:
                current = current.get(candidate)
                index = end
                matched = True
                break
        if matched:
            continue
        current = current.get(parts[index])
        if current is None:
            return None
        index += 1
    return current


def canonical_path_value(container, *path):
    current = container
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def canonical_metrics_root(context):
    return dict((context or {}).get("canonical_metrics") or {})


def canonical_graphs_root(context):
    return dict((context or {}).get("canonical_graphs") or {})


def calculation_context_root(context):
    return dict((context or {}).get("calculation_context") or {})


def canonical_metric_detail(context, *path):
    value = canonical_path_value(canonical_metrics_root(context), *path)
    return dict(value or {}) if isinstance(value, dict) else {}


def context_input_channel(context, *path):
    value = canonical_path_value(calculation_context_root(context), "inputs", "channels", *path)
    if isinstance(value, dict):
        return str(value.get("channel") or "").strip()
    return ""


def context_parameter(context, key_name, default=None):
    parameters = dict(calculation_context_root(context).get("parameters") or {})
    return parameters.get(key_name, default)


def context_dummy_profile(context, default="-"):
    value = calculation_context_root(context).get("dummy_profile")
    return str(value or default)
