import sys
from pathlib import Path


SUMMARY_TEMPLATE_FILENAME = "FMVSS208 Sumy_temp.xlsx"


def _resolve_summary_template_path():
    candidates = []
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            candidates.append(Path(bundle_root))
        candidates.append(Path(sys.executable).resolve().parent)
    module_path = Path(__file__).resolve()
    candidates.append(module_path.parents[3])
    candidates.append(module_path.parents[2])

    for root in candidates:
        path = root / "resources" / "templates" / SUMMARY_TEMPLATE_FILENAME
        if path.exists():
            return path
    return candidates[0] / "resources" / "templates" / SUMMARY_TEMPLATE_FILENAME


SUMMARY_TEMPLATE_PATH = _resolve_summary_template_path()


SUMMARY_META_FIELDS = (
    {
        "field_key": "manufacturer",
        "template_anchor": "vehicle manufacture",
    },
    {
        "field_key": "vehicle",
        "template_anchor": "vehicle model",
    },
    {
        "field_key": "speed",
        "template_anchor": "test speed",
    },
    {
        "field_key": "test_date",
        "template_anchor": "test date",
    },
    {
        "field_key": "test_id",
        "template_anchor": "test id",
    },
)


SUMMARY_OCCUPANT_LABEL_CELLS = ("C9", "G9")


EXCEL_IARV_EXPORT_RULES = {
    "FMVSS 208": {
        "exclude": {
            ("HEAD", "HIC36ms"),
            ("HEAD", "Resultant Acc. 3ms Clip"),
            ("NECK", "Peak Extension MOCy"),
            ("NECK", "Peak Flexion MOCy"),
        },
    },
}


EXCEL_VALUE_EXPORT_RULES = {
    "FMVSS 208": {
        "abs_result": set(),
    },
}


EXCEL_RESULT_SOURCE_OVERRIDES = {
    "FMVSS 208": {
        ("HEAD", "Resultant Acc. 3ms Clip"): ("Multiple Peak 3ms",),
        ("CHEST", "Chest Acc. 3ms Clip"): ("Multiple Peak 3ms",),
    },
}


SUMMARY_CRITERIA_ALIASES = {
    "CHEST": {
        "One Peak 3ms": ("One Peak 3ms",),
        "Multiple Peak 3ms": ("Multiple Peak 3ms",),
        "Chest Acc. 3ms Clip": ("Chest Acc. 3ms Clip",),
        "Chest Def.": ("Chest Deflection Peak",),
        "Chest V*C - ECE 94": ("V*C ECE94_CFC180",),
        "Chest V*C - SAE J1727": ("V*C SAE J1727_CFC600",),
    },
    "FEMUR": {
        "Left Femur Force": ("Left Peak Axial Force",),
        "Right Femur Force": ("Right Peak Axial Force",),
    },
    "HEAD": {
        "HIC 15ms": ("HIC15ms",),
        "HIC 36ms": ("HIC36ms",),
        "One Peak 3ms": ("One Peak 3ms",),
        "Multiple Peak 3ms": ("Multiple Peak 3ms",),
        "Resultant Acc. 3ms Clip": ("Resultant Acc. 3ms Clip",),
    },
    "KNEE": {
        "Left Knee Disp.": ("Left KNEE Displacement Peak",),
        "Right Knee Disp.": ("Right KNEE Displacement Peak",),
    },
    "NECK": {
        "MOCy - Peak Extension": ("Peak Extension MOCy",),
        "MOCy - Peak Flexion": ("Peak Flexion MOCy",),
        "Nce": ("NCE",),
        "Ncf": ("NCF",),
        "Nte": ("NTE",),
        "Ntf": ("NTF",),
        "Peak Comp. Force(FZ-)": ("Peak Compression Force(FZ-)",),
        "Peak Tension Force(FZ+)": ("Peak Tension Force(FZ+)",),
        "Shear Force(FX)": ("Peak Shear Force(FX)",),
    },
}


FMVSS208_SUMMARY_TEMPLATE = {
    "key": "fmvss208_summary",
    "label": "FMVSS 208 Summary Excel",
    "regulation": "FMVSS 208",
    "template_path": SUMMARY_TEMPLATE_PATH,
    "meta_fields": SUMMARY_META_FIELDS,
    "occupant_label_cells": SUMMARY_OCCUPANT_LABEL_CELLS,
    "iarv_export_rules": EXCEL_IARV_EXPORT_RULES,
    "value_export_rules": EXCEL_VALUE_EXPORT_RULES,
    "result_source_overrides": EXCEL_RESULT_SOURCE_OVERRIDES,
    "criteria_aliases": SUMMARY_CRITERIA_ALIASES,
}
