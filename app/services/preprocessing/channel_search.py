"""Viewer-based channel search and simple injury auto-detection helpers."""

import re


def make_channel_search_text(viewer, channel_name):
    label = viewer.get_channel_display_name(channel_name)
    return f"{channel_name} {label}".lower()


def infer_channel_group_key(viewer, channel_name):
    label = viewer.get_channel_display_name(channel_name).strip() or str(channel_name)
    text = f"{channel_name} {label}"
    text = re.sub(r"\[[^\]]*\]", " ", text)
    tokens = re.findall(r"[A-Za-z]+", text.upper())
    if not tokens:
        return "ETC"
    filtered = [tok for tok in tokens if tok not in {"X", "Y", "Z", "LEFT", "RIGHT", "RAW", "TIME", "SEC", "MS"}]
    if filtered:
        return filtered[0]
    return tokens[0]


def find_resultant_or_axis(viewer, keywords):
    candidates = []
    for col in viewer.get_numeric_channel_names(exclude_time=True):
        name = str(col).lower()
        label = str(viewer.get_channel_display_name(col)).lower()
        unit = str(viewer.get_y_axis_label(col)).lower()
        text = f"{name} {label} {unit}"
        score = 0
        for kw in keywords:
            if kw in text:
                score += 3
        if "res" in text or "resultant" in text or "mag" in text:
            score += 2
        if score > 0:
            candidates.append((score, col))
    candidates.sort(key=lambda x: (-x[0], str(x[1])))
    return candidates[0][1] if candidates else None


def auto_detect_injury_channels(viewer):
    found = {}
    head = find_resultant_or_axis(viewer, ["head", "cg", "acc"])
    if head:
        found["Head Acceleration"] = head

    for col in viewer.get_numeric_channel_names(exclude_time=True):
        text = f"{col} {viewer.get_channel_display_name(col)} {viewer.get_y_axis_label(col)}".lower()
        if "neck" in text and ("fx" in text or "force x" in text or "axial" in text):
            found.setdefault("Neck Fx", col)
        if "neck" in text and ("my" in text or "moment y" in text or "flex" in text or "ext" in text):
            found.setdefault("Neck My", col)
    return found
