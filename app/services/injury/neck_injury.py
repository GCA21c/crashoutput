from app.core.utils.formatting import SUMMARY_FORMAT_VERSION, fmt_metric_at, fmt_value
from app.services.preprocessing.service import compute_neck_nij_metrics



def calculate_neck_injury_bundle(
    time,
    selected,
    sign_flags,
    viewer,
    criterion_key,
    unit_getter,
    channel_desc_getter,
    resolve_series_for_calc,
):
    fz_peak, used_fz_peak = resolve_series_for_calc(selected['Fz'], 'fz', 1000, sign_flags['Fz'])
    fz, used_fz_nij = resolve_series_for_calc(selected['Fz'], 'fz', 600, sign_flags['Fz'])
    my, used_my_nij = resolve_series_for_calc(selected['My'], 'my', 600, sign_flags['My'])
    fx = None
    used_fx_nij = None
    if selected['Fx']:
        fx, used_fx_nij = resolve_series_for_calc(selected['Fx'], 'fx', 600, sign_flags['Fx'])
    fz_unit = unit_getter(used_fz_nij or selected['Fz'])
    my_unit = unit_getter(used_my_nij or selected['My'])
    fx_unit = unit_getter(used_fx_nij or selected['Fx']) if selected['Fx'] else None
    my_text = f"{selected['My']} {viewer.get_channel_display_name(selected['My'])} {my_unit}".lower() if selected['My'] else ''
    moment_is_mocy = any(tag in my_text for tag in (
        'mocy',
        'occipital condyle',
        'occipital condyle moment - y',
        'neckup_mocy',
        'neckupoc',
        'moyf',
    ))
    if moment_is_mocy:
        fx = None
        fx_unit = None
    metrics = compute_neck_nij_metrics(
        time, fz, my,
        apply_cfc600=False,
        criterion_key=criterion_key,
        fz_unit=fz_unit,
        my_unit=my_unit,
        fx_n=fx,
        fx_unit=fx_unit,
        moment_is_mocy=moment_is_mocy,
        fz_peak_n=fz_peak,
    )
    if metrics is None:
        raise ValueError('계산 가능한 Neck Injury 데이터가 없습니다.')
    metrics['selected_channels'] = selected
    metrics['sign_flags'] = sign_flags

    labels = {key: channel_desc_getter(ch) if ch else '-' for key, ch in selected.items()}
    calc_used = {
        'Peak Fz': used_fz_peak or selected['Fz'],
        'Nij Fz': used_fz_nij or selected['Fz'],
        'Nij Fx': used_fx_nij or selected['Fx'],
        'Nij My': used_my_nij or selected['My'],
    }

    metrics['calc_used_channels'] = {
        'fz_peak': used_fz_peak or selected['Fz'],
        'fz_nij': used_fz_nij or selected['Fz'],
        'fx_nij': used_fx_nij or selected['Fx'],
        'my_nij': used_my_nij or selected['My'],
    }
    metrics['source_filter_labels'] = {
        key: ((getattr(viewer, 'external_filter_labels', {}) or {}).get(ch) if ch else None)
        for key, ch in selected.items()
    }
    metrics['used_filter_labels'] = {
        'fz_peak': ((getattr(viewer, 'external_filter_labels', {}) or {}).get(used_fz_peak or selected['Fz']) if (used_fz_peak or selected['Fz']) else None),
        'fz_nij': ((getattr(viewer, 'external_filter_labels', {}) or {}).get(used_fz_nij or selected['Fz']) if (used_fz_nij or selected['Fz']) else None),
        'fx_nij': ((getattr(viewer, 'external_filter_labels', {}) or {}).get(used_fx_nij or selected['Fx']) if (used_fx_nij or selected['Fx']) else None),
        'my_nij': ((getattr(viewer, 'external_filter_labels', {}) or {}).get(used_my_nij or selected['My']) if (used_my_nij or selected['My']) else None),
    }

    crit = metrics.get('criteria', {})
    moment_input_label = crit.get('input_moment', 'My')
    moc_line = f"Lever arm D: {crit.get('moc_d', 0.0):.6f} m | MOC 적용: {'Yes' if crit.get('moc_applied') else 'No'} | Load Cell: {crit.get('load_cell_type', 'Preset D')}\n"
    summary = (
        f"Criterion: {crit.get('criterion_label', criterion_key)}\n"
        f"Dummy Family: {crit.get('dummy_family', '-')}\n"
        f"Source: {crit.get('source', '-')}\n"
        f"Fzt/Fzc: {crit.get('f_tension_crit', 0):.3f} / {crit.get('f_compression_crit', 0):.3f} N\n"
        f"MyF/MyE: {crit.get('m_flexion_crit', 0):.3f} / {crit.get('m_extension_crit', 0):.3f} Nm\n"
        f"Peak Limits (Fz+ / Fz-): {crit.get('peak_tension_limit') if crit.get('peak_tension_limit') is not None else '-'} / {crit.get('peak_compression_limit') if crit.get('peak_compression_limit') is not None else '-'} N\n"
        f"Moment Input: {moment_input_label}\n"
        f"{moc_line}\n"
        + fmt_metric_at('Peak Tension Force (FZ+)', metrics['peak_tension_fz'], unit='N', time_s=metrics.get('peak_tension_time')) + '\n'
        + fmt_metric_at('Peak Comp. Force (FZ-)', metrics['peak_compression_fz'], unit='N', time_s=metrics.get('peak_compression_time')) + '\n'
        + fmt_metric_at(f'Peak Flexion {moment_input_label}', metrics['peak_flexion_my'], unit='Nm', time_s=metrics.get('peak_flexion_time')) + '\n'
        + fmt_metric_at(f'Peak Extension {moment_input_label}', abs(metrics['peak_extension_my']), unit='Nm', time_s=metrics.get('peak_extension_time')) + '\n\n'
        + fmt_metric_at('NTF', metrics['peak_ntf'], time_s=metrics.get('peak_ntf_time')) + '\n'
        + fmt_metric_at('NTE', metrics['peak_nte'], time_s=metrics.get('peak_nte_time')) + '\n'
        + fmt_metric_at('NCF', metrics['peak_ncf'], time_s=metrics.get('peak_ncf_time')) + '\n'
        + fmt_metric_at('NCE', metrics['peak_nce'], time_s=metrics.get('peak_nce_time')) + '\n'
        + fmt_metric_at('Overall Nij', metrics['overall_nij'], time_s=metrics.get('overall_nij_time')) + '\n'
        + f"Dominant Mode: {metrics['dominant_mode']}\n\n"
        + f"사용 채널(선택):\n"
        + f"Fx: {labels['Fx']}\nFy: {labels['Fy']}\nFz: {labels['Fz']}\n"
        + f"Mx: {labels['Mx']}\nMy: {labels['My']}\nMz: {labels['Mz']}\n\n"
        + f"계산 규칙: 각 시점마다 Fz와 {moment_input_label} 부호의 AND 조건으로 case를 결정합니다.\n"
        + f"사용 채널(계산): Peak Fz={calc_used['Peak Fz']} | Nij Fz={calc_used['Nij Fz']} | Nij Fx={calc_used['Nij Fx'] or '-'} | Nij My={calc_used['Nij My']}\n"
        + f"권장 전처리: DATA FILTERING에서 Neck 파생 CFC 채널 생성 후 사용"
    )

    return {
        'metrics': metrics,
        'summary_text': summary,
        'summary_format_version': SUMMARY_FORMAT_VERSION,
        'calc_used': calc_used,
    }
