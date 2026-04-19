"""Channel role detection helpers for preprocessing-derived channels."""


def _safe_text(*parts):
    return " ".join(str(part or "") for part in parts).lower()


def detect_head_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if "head" not in text or ("acc" not in text and "acceler" not in text):
        return None
    if any(tag in text for tag in (" x ", " ax", "ax ", "acc x", "accx", " acx", "_x", "xa")):
        return "x"
    if any(tag in text for tag in (" y ", " ay", "ay ", "acc y", "accy", " acy", "_y", "ya")):
        return "y"
    if any(tag in text for tag in (" z ", " az", "az ", "acc z", "accz", " acz", "_z", "za")):
        return "z"
    return None


def detect_chest_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if not any(tag in text for tag in ("chest", "chst", "thor", "stern", "rib")):
        return None
    if any(tag in text for tag in ("disp", "defl", "deflection", " ds", "dsx", "dc0", "distance")):
        return "disp"
    if "acc" in text or "acceler" in text:
        if any(tag in text for tag in (" x ", " ax", "ax ", "acc x", "accx", " acx", "_x", "xa")):
            return "x"
        if any(tag in text for tag in (" y ", " ay", "ay ", "acc y", "accy", " acy", "_y", "ya")):
            return "y"
        if any(tag in text for tag in (" z ", " az", "az ", "acc z", "accz", " acz", "_z", "za")):
            return "z"
    return None


def detect_femur_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if not any(tag in text for tag in ("femur", "femr", "thigh", "upper leg", "leg load", "axial force")):
        return None
    if any(tag in text for tag in (" left ", "_l", " lf", "l fem", "lfem", "feml", "driver")):
        return "left"
    if any(tag in text for tag in (" right ", "_r", " rf", "r fem", "rfem", "femr", "passenger")):
        return "right"
    return None


def detect_neck_channel_role(channel_name, description="", unit=""):
    text = _safe_text(channel_name, description, unit)
    if "neck" not in text:
        return None
    if any(tag in text for tag in (" mocy", "occipital condyle", " moment y", " my ", "_my", "my_", "flex", "ext")):
        return "my"
    if any(tag in text for tag in (" force z", " fz ", "_fz", "fz_", "axial")):
        return "fz"
    if any(tag in text for tag in (" force x", " fx ", "_fx", "fx_", "shear")):
        return "fx"
    return None


def neck_role_required_cfc(role):
    """Return only the additional Neck CFC channels that may be needed later."""
    if role in ("fz", "fx"):
        return (600,)
    if role == "my":
        return tuple()
    return tuple()


def derived_role_required_cfc(purpose, role):
    purpose = str(purpose or "")
    role = str(role or "")
    if purpose == "neck_injury":
        return neck_role_required_cfc(role)
    if purpose == "head_injury":
        return tuple()
    if purpose == "chest_injury":
        if role == "disp":
            return (600,)
        return tuple()
    if purpose == "femur_injury":
        return tuple()
    return tuple()


def detect_injury_channel_purpose_and_role(channel_name, description="", unit=""):
    role = detect_neck_channel_role(channel_name, description, unit)
    if role is not None:
        return "neck_injury", role
    role = detect_head_channel_role(channel_name, description, unit)
    if role is not None:
        return "head_injury", role
    role = detect_chest_channel_role(channel_name, description, unit)
    if role is not None:
        return "chest_injury", role
    role = detect_femur_channel_role(channel_name, description, unit)
    if role is not None:
        return "femur_injury", role
    return None, None


def make_derived_channel_name(source_channel, purpose, role, cfc_value):
    purpose_tag = str(purpose or "derived").replace("_injury", "").upper()
    return f"{source_channel}__{purpose_tag}_{str(role).upper()}_CFC{int(cfc_value)}"


def make_neck_derived_channel_name(source_channel, role, cfc_value):
    return f"{source_channel}__NECK_{str(role).upper()}_CFC{int(cfc_value)}"
