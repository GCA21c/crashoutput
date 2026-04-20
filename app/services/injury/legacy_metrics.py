from app.services.injury.hic_3ms_math import compute_3ms_clip, compute_hic
from app.services.injury.nij_math import compute_nij
from app.services.injury.scalars import convert_accel_to_g


def compute_injury_metrics(viewer, detected_channels):
    results = []
    if viewer.df is None or viewer.time_column is None:
        return results
    time_s = viewer.get_numeric_column(viewer.time_column)

    head_ch = detected_channels.get("Head Acceleration")
    if head_ch:
        unit = viewer.get_y_axis_label(head_ch)
        accel = convert_accel_to_g(viewer.get_numeric_column(head_ch), unit)
        hic15 = compute_hic(time_s, accel, 0.015)
        hic36 = compute_hic(time_s, accel, 0.036)
        clip3 = compute_3ms_clip(time_s, accel)
        if hic15 is not None:
            results.append({"metric": "HIC15", "value": f"{hic15:.3f}", "unit": "-", "source": head_ch})
        if hic36 is not None:
            results.append({"metric": "HIC36", "value": f"{hic36:.3f}", "unit": "-", "source": head_ch})
        if clip3 is not None:
            results.append({"metric": "Head 3ms Clip", "value": f"{clip3:.3f}", "unit": "g", "source": head_ch})

    fx_ch = detected_channels.get("Neck Fx")
    my_ch = detected_channels.get("Neck My")
    if fx_ch and my_ch:
        nij = compute_nij(viewer.get_numeric_column(fx_ch), viewer.get_numeric_column(my_ch))
        if nij is not None:
            results.append({"metric": "Nij", "value": f"{nij:.3f}", "unit": "-", "source": f"{fx_ch} + {my_ch}"})

    return results
