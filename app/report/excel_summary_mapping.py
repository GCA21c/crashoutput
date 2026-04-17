from pathlib import Path


SUMMARY_TEMPLATE_FILENAME = "FMVSS208 Sumy_temp.xlsx"
SUMMARY_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "resources" / "templates" / SUMMARY_TEMPLATE_FILENAME


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


SUMMARY_CRITERIA_ALIASES = {
    "CHEST": {
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
