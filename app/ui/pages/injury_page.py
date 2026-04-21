import os
import re
import uuid
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.services.preprocessing.service import (
    compute_resultant_xyz,
    build_neck_injury_channels,
    build_neck_injury_channel_metadata,
    apply_cfc_filter_to_series,
    parse_cfc_filter_label,
    detect_chest_channel_role,
    detect_femur_channel_role,
)
from app.core.dummy import (
    NECK_DUMMY_PROFILES, CHEST_DUMMY_PROFILES, FEMUR_DUMMY_PROFILES, TIBIA_DUMMY_PROFILES,
    FRONTAL_UNIFIED_PROFILES, get_available_dummy_profile_names, infer_dummy_profile_from_codes,
)
from app.core.io.dataset_store import DATASET_EXT, save_dataset_pickle
from app.services.injury import (
    build_head_injury_bundle,
    calculate_neck_injury_bundle,
    calculate_chest_injury_bundle,
    calculate_pelvis_injury_bundle,
    calculate_femur_injury_bundle,
    calculate_knee_injury_bundle,
    calculate_iliac_injury_bundle,
    calculate_tibia_injury_bundle,
)
from app.services.injury.input_resolver import find_derived_channel
from app.core.utils.formatting import SUMMARY_FORMAT_VERSION, fmt_time_ms, fmt_value
from app.ui.components.multi_dummy_panel import MultiDummyPanel
from app.ui.components.scrollable_frame import VerticalScrolledFrame
from app.core.isocode import normalize_filter_label_to_code, rewrite_filter_code_in_text



HEAD_PROFILE_OPTIONS = tuple(get_available_dummy_profile_names('head', 'FRONTAL'))
FEMUR_PROFILE_OPTIONS = tuple(get_available_dummy_profile_names('femur', 'FRONTAL'))
KNEE_PROFILE_OPTIONS = FRONTAL_UNIFIED_PROFILES
ILIAC_PROFILE_OPTIONS = ('Thor_50%M',)


CHANNEL_INPUT_ROLE_SPECS = {
    'hic': {
        'x': {'sensor_location': 'head', 'data_type_code': 'AC', 'axis_code': 'X'},
        'y': {'sensor_location': 'head', 'data_type_code': 'AC', 'axis_code': 'Y'},
        'z': {'sensor_location': 'head', 'data_type_code': 'AC', 'axis_code': 'Z'},
    },
    'nij': {
        'Fx': {'sensor_location': 'neck', 'data_type_code': 'FO', 'axis_code': 'X'},
        'Fy': {'sensor_location': 'neck', 'data_type_code': 'FO', 'axis_code': 'Y'},
        'Fz': {'sensor_location': 'neck', 'data_type_code': 'FO', 'axis_code': 'Z'},
        'Mx': {'sensor_location': 'neck', 'data_type_code': 'MO', 'axis_code': 'X'},
        'My': {'sensor_location': 'neck', 'data_type_code': 'MO', 'axis_code': 'Y'},
        'Mz': {'sensor_location': 'neck', 'data_type_code': 'MO', 'axis_code': 'Z'},
    },
    'chest': {
        'x': {'sensor_location': 'chest', 'data_type_code': 'AC', 'axis_code': 'X'},
        'y': {'sensor_location': 'chest', 'data_type_code': 'AC', 'axis_code': 'Y'},
        'z': {'sensor_location': 'chest', 'data_type_code': 'AC', 'axis_code': 'Z'},
        'disp': {'sensor_location': 'chest', 'data_type_code': 'DS'},
    },
    'pelvis': {
        'x': {'sensor_location': 'pelvis', 'data_type_code': 'AC', 'axis_code': 'X'},
        'y': {'sensor_location': 'pelvis', 'data_type_code': 'AC', 'axis_code': 'Y'},
        'z': {'sensor_location': 'pelvis', 'data_type_code': 'AC', 'axis_code': 'Z'},
    },
    'femur': {
        'left': {'sensor_location': 'femur', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'left'},
        'right': {'sensor_location': 'femur', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'right'},
    },
    'knee': {
        'left': {'sensor_location': 'knee', 'data_type_code': 'DS', 'side': 'left', 'main_location_code': 'KNSL'},
        'right': {'sensor_location': 'knee', 'data_type_code': 'DS', 'side': 'right', 'main_location_code': 'KNSL'},
    },
    'iliac': {
        'left_fx': {'sensor_location': 'iliac', 'data_type_code': 'FO', 'axis_code': 'X', 'side': 'left'},
        'left_my': {'sensor_location': 'iliac', 'data_type_code': 'MO', 'axis_code': 'Y', 'side': 'left'},
        'right_fx': {'sensor_location': 'iliac', 'data_type_code': 'FO', 'axis_code': 'X', 'side': 'right'},
        'right_my': {'sensor_location': 'iliac', 'data_type_code': 'MO', 'axis_code': 'Y', 'side': 'right'},
    },
    'tibia': {
        'left_knee_clevis_inner_fz': {'sensor_location': 'knee', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'left', 'position_detail': 'inner', 'main_location_code': 'CLEV'},
        'left_knee_clevis_outer_fz': {'sensor_location': 'knee', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'left', 'position_detail': 'outer', 'main_location_code': 'CLEV'},
        'right_knee_clevis_inner_fz': {'sensor_location': 'knee', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'right', 'position_detail': 'inner', 'main_location_code': 'CLEV'},
        'right_knee_clevis_outer_fz': {'sensor_location': 'knee', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'right', 'position_detail': 'outer', 'main_location_code': 'CLEV'},
        'left_upper_fx': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'X', 'side': 'left', 'level': 'upper'},
        'left_upper_fz': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'left', 'level': 'upper'},
        'left_upper_mx': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'X', 'side': 'left', 'level': 'upper'},
        'left_upper_my': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'Y', 'side': 'left', 'level': 'upper'},
        'left_lower_fx': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'X', 'side': 'left', 'level': 'lower'},
        'left_lower_fz': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'left', 'level': 'lower'},
        'left_lower_mx': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'X', 'side': 'left', 'level': 'lower'},
        'left_lower_my': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'Y', 'side': 'left', 'level': 'lower'},
        'right_upper_fx': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'X', 'side': 'right', 'level': 'upper'},
        'right_upper_fz': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'right', 'level': 'upper'},
        'right_upper_mx': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'X', 'side': 'right', 'level': 'upper'},
        'right_upper_my': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'Y', 'side': 'right', 'level': 'upper'},
        'right_lower_fx': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'X', 'side': 'right', 'level': 'lower'},
        'right_lower_fz': {'sensor_location': 'tibia', 'data_type_code': 'FO', 'axis_code': 'Z', 'side': 'right', 'level': 'lower'},
        'right_lower_mx': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'X', 'side': 'right', 'level': 'lower'},
        'right_lower_my': {'sensor_location': 'tibia', 'data_type_code': 'MO', 'axis_code': 'Y', 'side': 'right', 'level': 'lower'},
    },
}

STRICT_BLANK_ROLE_KEYS = {
    ('iliac', 'left_fx'), ('iliac', 'left_my'), ('iliac', 'right_fx'), ('iliac', 'right_my'),
    ('tibia', 'left_knee_clevis_inner_fz'), ('tibia', 'left_knee_clevis_outer_fz'),
    ('tibia', 'right_knee_clevis_inner_fz'), ('tibia', 'right_knee_clevis_outer_fz'),
}
TIBIA_PROFILE_OPTIONS = tuple(get_available_dummy_profile_names('tibia', 'FRONTAL'))
DUMMY_POSITION_OPTIONS = tuple(f"B{i}" for i in range(1, 7))
DUMMY_SLOT_PREFIX_RE = re.compile(r'^\s*(B[1-6])(?=\b|[_\-\s]|[A-Z0-9])', re.IGNORECASE)

FILTERED_ISOCODE_CODES = ('A', 'B', 'C', 'D')
BLANK_DISPLAY_VALUE = '-'
FILTER_PREFERENCE_MAP = {
    'hic': {'x': ('A',), 'y': ('A',), 'z': ('A',)},
    'nij': {'Fx': ('A',), 'Fy': ('A',), 'Fz': ('A',), 'Mx': ('B',), 'My': ('B',), 'Mz': ('B',)},
    'chest': {'x': ('C',), 'y': ('C',), 'z': ('C',), 'disp': ('B',)},
    'pelvis': {'x': ('A',), 'y': ('A',), 'z': ('A',)},
    'femur': {'left': ('B',), 'right': ('B',)},
    'knee': {'left': ('C',), 'right': ('C',)},
    'iliac': {'left_fx': ('B',), 'left_my': ('B',), 'right_fx': ('B',), 'right_my': ('B',)},
    'tibia': {
        'left_knee_clevis_inner_fz': ('B',), 'left_knee_clevis_outer_fz': ('B',),
        'left_upper_fx': ('B',), 'left_upper_fz': ('B',), 'left_upper_mx': ('B',), 'left_upper_my': ('B',),
        'left_lower_fx': ('B',), 'left_lower_fz': ('B',), 'left_lower_mx': ('B',), 'left_lower_my': ('B',),
        'right_knee_clevis_inner_fz': ('B',), 'right_knee_clevis_outer_fz': ('B',),
        'right_upper_fx': ('B',), 'right_upper_fz': ('B',), 'right_upper_mx': ('B',), 'right_upper_my': ('B',),
        'right_lower_fx': ('B',), 'right_lower_fz': ('B',), 'right_lower_mx': ('B',), 'right_lower_my': ('B',),
    },
}


class InjuryPage(tk.Frame):
    def __init__(self, parent, workbench, initial_mode="hic", show_internal_menu=False):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        self.initial_mode = initial_mode
        self.show_internal_menu = show_internal_menu
        self.mode_var = tk.StringVar(value=initial_mode)
        self.status_var = tk.StringVar(value="DAT를 로드한 뒤 채널을 선택하세요.")

        self.dummy_count_var = tk.StringVar(value="1")
        self.active_dummy_var = tk.StringVar(value="B1")
        self.detected_groups = {}
        self.active_positions = ['B1']
        self.requested_row_positions = ['B1']
        self.current_available_channels = []
        self._display_to_channel = {}
        self._channel_to_display = {}

        self.hic_x_var = tk.StringVar()
        self.hic_y_var = tk.StringVar()
        self.hic_z_var = tk.StringVar()
        self.hic15_var = tk.StringVar(value="HIC15")
        self.hic36_var = tk.StringVar(value="HIC36")
        self.clip3_var = tk.StringVar(value="3ms Clip")
        self.use_high_res_cumulative_3ms_var = tk.BooleanVar(value=False)
        self.head_dummy_profile_var = tk.StringVar(value=HEAD_PROFILE_OPTIONS[0] if HEAD_PROFILE_OPTIONS else "")

        self.nij_fx_var = tk.StringVar()
        self.nij_fy_var = tk.StringVar()
        self.nij_fz_var = tk.StringVar()
        self.nij_mx_var = tk.StringVar()
        self.nij_my_var = tk.StringVar()
        self.nij_mz_var = tk.StringVar()
        self.nij_fx_neg_var = tk.BooleanVar(value=False)
        self.nij_fy_neg_var = tk.BooleanVar(value=False)
        self.nij_fz_neg_var = tk.BooleanVar(value=False)
        self.nij_mx_neg_var = tk.BooleanVar(value=False)
        self.nij_my_neg_var = tk.BooleanVar(value=False)
        self.nij_mz_neg_var = tk.BooleanVar(value=False)
        self.nij_dummy_var = tk.StringVar(value="H3_50%M")
        self.nij_guidance_var = tk.StringVar(value="Fx/Fy/Fz 원채널은 CFC1000 권장 | Mx/My/Mz 원채널은 CFC600 권장")

        self.chest_x_var = tk.StringVar()
        self.chest_y_var = tk.StringVar()
        self.chest_z_var = tk.StringVar()
        self.chest_disp_var = tk.StringVar()
        self.chest_dummy_var = tk.StringVar(value="H3_50%M")
        self.pelvis_x_var = tk.StringVar()
        self.pelvis_y_var = tk.StringVar()
        self.pelvis_z_var = tk.StringVar()
        self.pelvis_dummy_var = tk.StringVar(value=HEAD_PROFILE_OPTIONS[0] if HEAD_PROFILE_OPTIONS else "H3_50%M")
        self.pelvis_guidance_var = tk.StringVar(value="골반 XYZ 가속도로 Resultant 및 3ms 지표를 계산합니다.")
        self.chest_guidance_var = tk.StringVar(value="원데이터 채널을 그대로 사용해 CHEST/V*C를 계산합니다.")
        self.femur_left_var = tk.StringVar()
        self.femur_right_var = tk.StringVar()
        self.femur_dummy_var = tk.StringVar(value=FEMUR_PROFILE_OPTIONS[0] if FEMUR_PROFILE_OPTIONS else "H3_50%M")
        self.femur_guidance_var = tk.StringVar(value="대퇴부 축력은 CFC600 경로를 기준으로 계산합니다.")
        self.knee_left_var = tk.StringVar()
        self.knee_right_var = tk.StringVar()
        self.knee_guidance_var = tk.StringVar(value="Hybrid III knee slider 채널의 좌/우 peak displacement와 발생 시점을 계산합니다.")
        self.iliac_left_fx_var = tk.StringVar()
        self.iliac_left_my_var = tk.StringVar()
        self.iliac_right_fx_var = tk.StringVar()
        self.iliac_right_my_var = tk.StringVar()
        self.iliac_dummy_var = tk.StringVar(value=ILIAC_PROFILE_OPTIONS[0] if ILIAC_PROFILE_OPTIONS else "Thor_50%M")
        self.iliac_guidance_var = tk.StringVar(value="THOR 계열 iliac wing(ASIS) Fx/My 좌우 채널로 side별 peak 하중/모멘트와 Fx-My 응답을 계산합니다.")
        self.tibia_left_knee_clevis_inner_fz_var = tk.StringVar()
        self.tibia_left_knee_clevis_outer_fz_var = tk.StringVar()
        self.tibia_left_upper_fx_var = tk.StringVar()
        self.tibia_left_upper_fz_var = tk.StringVar()
        self.tibia_left_upper_mx_var = tk.StringVar()
        self.tibia_left_upper_my_var = tk.StringVar()
        self.tibia_left_lower_fx_var = tk.StringVar()
        self.tibia_left_lower_fz_var = tk.StringVar()
        self.tibia_left_lower_mx_var = tk.StringVar()
        self.tibia_left_lower_my_var = tk.StringVar()
        self.tibia_right_knee_clevis_inner_fz_var = tk.StringVar()
        self.tibia_right_knee_clevis_outer_fz_var = tk.StringVar()
        self.tibia_right_upper_fx_var = tk.StringVar()
        self.tibia_right_upper_fz_var = tk.StringVar()
        self.tibia_right_upper_mx_var = tk.StringVar()
        self.tibia_right_upper_my_var = tk.StringVar()
        self.tibia_right_lower_fx_var = tk.StringVar()
        self.tibia_right_lower_fz_var = tk.StringVar()
        self.tibia_right_lower_mx_var = tk.StringVar()
        self.tibia_right_lower_my_var = tk.StringVar()
        self.tibia_dummy_var = tk.StringVar(value=TIBIA_PROFILE_OPTIONS[0] if TIBIA_PROFILE_OPTIONS else "H3_50%M")
        self.tibia_guidance_var = tk.StringVar(value="좌/우 knee clevis, upper/lower tibia의 Fx/Fz/Mx/My 채널을 모두 저장하고, 현재 계산은 upper/lower Fz, Mx, My 기반 Tibia Index와 compression, bending resultant를 사용합니다.")

        self.figure = Figure(figsize=(8.8, 5.8), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.last_plot_title = "injury_graph"
        self._graph_tab_notebook = None
        self._graph_tab_to_key = {}
        self._graph_key_to_tab = {}
        self._updating_graph_tabs = False

        self.slot_states = {slot: self._new_slot_state() for slot in DUMMY_POSITION_OPTIONS}
        self._result_widget = None
        self.active_plot_key = {}
        self._last_ui_slot = 'B1'

        self._build_ui()
        self._bind_multi_dummy_vars()
        self._sync_active_positions()
        self.active_dummy_var.trace_add('write', lambda *_: self._on_active_dummy_changed())
        self.dummy_count_var.trace_add('write', lambda *_: self._on_dummy_count_changed())
        for var in (self.nij_fx_var, self.nij_fy_var, self.nij_fz_var, self.nij_mx_var, self.nij_my_var, self.nij_mz_var):
            var.trace_add('write', lambda *_: self._refresh_neck_guidance_text())

    def _new_slot_state(self):
        return {
            'result_uid': '',
            'dummy_name': '',
            'dummy_profile': '',
            'channels': {},
            'neg_flags': {},
            'summary_text': '-',
            'head_bundle': None,
            'neck_metrics': None,
            'chest_metrics': None,
            'pelvis_metrics': None,
            'femur_metrics': None,
            'knee_metrics': None,
            'iliac_metrics': None,
            'tibia_metrics': None,
            'head_metadata': {},
            'neck_saved_payload': {},
            'chest_saved_payload': {},
            'pelvis_saved_payload': {},
            'femur_saved_payload': {},
            'knee_saved_payload': {},
            'iliac_saved_payload': {},
            'tibia_saved_payload': {},
            'graph_key': None,
            'graph_uid': '',
            'filtered_channels': {},
        }

    def _result_metrics_for_state(self, state):
        if self.initial_mode == 'hic':
            merged = dict(state.get('head_metadata') or {})
            bundle = dict(state.get('head_bundle') or {})
            for key, value in bundle.items():
                merged.setdefault(key, value)
            return merged
        if self.initial_mode == 'nij':
            return dict(state.get('neck_metrics') or {})
        if self.initial_mode == 'chest':
            return dict(state.get('chest_metrics') or {})
        if self.initial_mode == 'pelvis':
            return dict(state.get('pelvis_metrics') or {})
        if self.initial_mode == 'femur':
            return dict(state.get('femur_metrics') or {})
        if self.initial_mode == 'knee':
            return dict(state.get('knee_metrics') or {})
        if self.initial_mode == 'iliac':
            return dict(state.get('iliac_metrics') or {})
        if self.initial_mode == 'tibia':
            return dict(state.get('tibia_metrics') or {})
        return {}

    def _to_storable_metric_value(self, value):
        if isinstance(value, dict):
            return {str(key): self._to_storable_metric_value(val) for key, val in value.items()}
        if isinstance(value, np.ndarray):
            return self._to_storable_metric_value(value.tolist())
        if isinstance(value, (list, tuple)):
            return [self._to_storable_metric_value(item) for item in value]
        if isinstance(value, (np.floating, np.integer, np.bool_)):
            value = value.item()
        if isinstance(value, float):
            return value if np.isfinite(value) else None
        if isinstance(value, (int, bool)) or value is None:
            return value
        if isinstance(value, str):
            return value
        return str(value)

    def _series_extrema_detail(self, time_values, series_values):
        try:
            arr_t = np.asarray(time_values, dtype=float)
            arr_v = np.asarray(series_values, dtype=float)
        except Exception:
            return None
        if arr_t.ndim != 1 or arr_v.ndim != 1 or arr_t.size == 0 or arr_v.size == 0:
            return None
        n = min(arr_t.size, arr_v.size)
        arr_t = arr_t[:n]
        arr_v = arr_v[:n]
        valid = np.isfinite(arr_t) & np.isfinite(arr_v)
        if not np.any(valid):
            return None
        idx = np.flatnonzero(valid)
        values = arr_v[idx]
        max_local = int(np.nanargmax(values))
        min_local = int(np.nanargmin(values))
        abs_local = int(np.nanargmax(np.abs(values)))
        max_idx = int(idx[max_local])
        min_idx = int(idx[min_local])
        abs_idx = int(idx[abs_local])
        return {
            'max_value': float(arr_v[max_idx]),
            'max_time_s': float(arr_t[max_idx]),
            'min_value': float(arr_v[min_idx]),
            'min_time_s': float(arr_t[min_idx]),
            'abs_peak_value': float(abs(arr_v[abs_idx])),
            'abs_peak_time_s': float(arr_t[abs_idx]),
        }

    def _collect_metric_extrema(self, node, time_values, prefix=''):
        extrema = {}
        if isinstance(node, dict):
            for key, value in node.items():
                child_prefix = f'{prefix}.{key}' if prefix else str(key)
                extrema.update(self._collect_metric_extrema(value, time_values, child_prefix))
            return extrema
        if not prefix:
            return extrema
        detail = self._series_extrema_detail(time_values, node)
        if detail:
            extrema[prefix] = detail
        return extrema

    def _safe_metric_float(self, value):
        try:
            result = float(value)
        except Exception:
            return None
        return result if np.isfinite(result) else None

    def _detail_value(self, detail):
        return self._safe_metric_float((detail or {}).get('value'))

    def _detail_time(self, detail):
        return self._safe_metric_float((detail or {}).get('time_s'))

    def _build_report_values(self, metrics):
        metrics = dict(metrics or {})
        if self.initial_mode == 'hic':
            return {
                'hic15': self._safe_metric_float(metrics.get('hic15_value')),
                'hic36': self._safe_metric_float(metrics.get('hic36_value')),
                'head_one_peak_3ms': self._safe_metric_float(metrics.get('one_peak_3ms_value') or metrics.get('clip3_value')),
                'head_multiple_3ms_clip': self._safe_metric_float(metrics.get('multiple_peak_3ms_value')),
                'head_3ms_clip': self._safe_metric_float(metrics.get('one_peak_3ms_value') or metrics.get('clip3_value')),
                'resultant_peak_g': self._safe_metric_float(metrics.get('resultant_peak_value')),
                'head_x_max': self._safe_metric_float(metrics.get('head_x_max_value')),
                'head_x_min': self._safe_metric_float(metrics.get('head_x_min_value')),
                'head_y_max': self._safe_metric_float(metrics.get('head_y_max_value')),
                'head_y_min': self._safe_metric_float(metrics.get('head_y_min_value')),
                'head_z_max': self._safe_metric_float(metrics.get('head_z_max_value')),
                'head_z_min': self._safe_metric_float(metrics.get('head_z_min_value')),
                'head_resultant_max': self._safe_metric_float(metrics.get('head_resultant_max_value')),
                'head_resultant_min': self._safe_metric_float(metrics.get('head_resultant_min_value')),
            }
        if self.initial_mode == 'nij':
            return {
                'overall_nij': self._safe_metric_float(metrics.get('overall_nij')),
                'peak_tension_fz': self._safe_metric_float(metrics.get('peak_tension_fz')),
                'peak_compression_fz': self._safe_metric_float(metrics.get('peak_compression_fz')),
                'peak_flexion_my': self._safe_metric_float(metrics.get('peak_flexion_my')),
                'peak_extension_my': self._safe_metric_float(metrics.get('peak_extension_my')),
                'peak_nte': self._safe_metric_float(metrics.get('peak_nte')),
                'peak_ntf': self._safe_metric_float(metrics.get('peak_ntf')),
                'peak_nce': self._safe_metric_float(metrics.get('peak_nce')),
                'peak_ncf': self._safe_metric_float(metrics.get('peak_ncf')),
            }
        if self.initial_mode == 'chest':
            return {
                'chest_one_peak_3ms': self._safe_metric_float(metrics.get('one_peak_3ms_g')),
                'chest_3ms_clip': self._safe_metric_float(metrics.get('one_peak_3ms_g')),
                'chest_multiple_3ms_clip': self._safe_metric_float(metrics.get('multiple_peak_3ms_g')),
                'resultant_peak_g': self._detail_value(metrics.get('resultant_peak')),
                'displacement_peak_mm': self._detail_value(metrics.get('displacement_peak')),
                'vc_sae_max_mps': self._detail_value(metrics.get('vc_sae_max')),
                'vc_ece_max_mps': self._detail_value(metrics.get('vc_ece_max')),
            }
        if self.initial_mode == 'pelvis':
            return {
                'pelvis_3ms_clip': self._detail_value(metrics.get('one_peak_3ms')),
                'pelvis_multiple_3ms_clip': self._detail_value(metrics.get('multiple_peak_3ms')),
                'pelvis_resultant_peak': self._detail_value(metrics.get('resultant_peak')),
            }
        if self.initial_mode == 'femur':
            return {
                'left_peak_axial_force_n': self._detail_value(metrics.get('left_peak_abs')),
                'right_peak_axial_force_n': self._detail_value(metrics.get('right_peak_abs')),
                'overall_peak_n': self._detail_value(metrics.get('overall_peak')),
            }
        if self.initial_mode == 'knee':
            return {
                'left_peak_slider': self._detail_value(metrics.get('left_peak')),
                'left_peak_slider_time_s': self._detail_time(metrics.get('left_peak')),
                'right_peak_slider': self._detail_value(metrics.get('right_peak')),
                'right_peak_slider_time_s': self._detail_time(metrics.get('right_peak')),
            }
        if self.initial_mode == 'iliac':
            left = dict(metrics.get('left_summary') or {})
            right = dict(metrics.get('right_summary') or {})
            return {
                'left_compression_force_n': self._safe_metric_float(left.get('compression_force_n')),
                'left_tension_force_n': self._safe_metric_float(left.get('tension_force_n')),
                'left_peak_moment_nm': self._safe_metric_float(left.get('peak_moment_nm')),
                'right_compression_force_n': self._safe_metric_float(right.get('compression_force_n')),
                'right_tension_force_n': self._safe_metric_float(right.get('tension_force_n')),
                'right_peak_moment_nm': self._safe_metric_float(right.get('peak_moment_nm')),
            }
        if self.initial_mode == 'tibia':
            return {
                'overall_peak_tibia_index': self._detail_value(metrics.get('overall_peak_tibia_index')),
                'left_upper_peak_tibia_index': self._detail_value((metrics.get('left_upper') or {}).get('peak_tibia_index')),
                'left_lower_peak_tibia_index': self._detail_value((metrics.get('left_lower') or {}).get('peak_tibia_index')),
                'right_upper_peak_tibia_index': self._detail_value((metrics.get('right_upper') or {}).get('peak_tibia_index')),
                'right_lower_peak_tibia_index': self._detail_value((metrics.get('right_lower') or {}).get('peak_tibia_index')),
            }
        return {}

    def _enrich_payload_with_structured_results(self, payload, state):
        enriched = dict(payload or {})
        metrics = self._result_metrics_for_state(state)
        time_values = dict(metrics or {}).get('time')
        report_values = self._build_report_values(metrics)
        enriched['result_schema_version'] = 1
        enriched['report_values'] = report_values
        for key, value in report_values.items():
            enriched[key] = value
        enriched['structured_metrics'] = self._to_storable_metric_value(metrics)
        enriched['metric_extrema'] = self._collect_metric_extrema(metrics, time_values)
        return enriched

    def _section_key(self):
        return {'hic': 'head', 'nij': 'neck', 'chest': 'chest', 'pelvis': 'pelvis', 'femur': 'femur', 'knee': 'knee', 'iliac': 'iliac', 'tibia': 'tibia'}[self.initial_mode]

    def _profile_options(self):
        if self.initial_mode == 'nij':
            return tuple(NECK_DUMMY_PROFILES.keys())
        if self.initial_mode == 'chest':
            return tuple(CHEST_DUMMY_PROFILES.keys())
        if self.initial_mode == 'pelvis':
            return HEAD_PROFILE_OPTIONS
        if self.initial_mode == 'femur':
            return FEMUR_PROFILE_OPTIONS
        if self.initial_mode == 'knee':
            return KNEE_PROFILE_OPTIONS
        if self.initial_mode == 'iliac':
            return ILIAC_PROFILE_OPTIONS
        if self.initial_mode == 'tibia':
            return TIBIA_PROFILE_OPTIONS
        return HEAD_PROFILE_OPTIONS

    def _title_text(self):
        return {
            'hic': 'INJURY - HEAD',
            'nij': 'INJURY - NECK',
            'chest': 'INJURY - CHEST',
            'pelvis': 'INJURY - PELVIS',
            'femur': 'INJURY - FEMUR',
            'knee': 'INJURY - KNEE',
            'iliac': 'INJURY - ILIAC',
            'tibia': 'INJURY - TIBIA',
        }[self.initial_mode]

    def _dummy_profile_var(self):
        if self.initial_mode == 'nij':
            return self.nij_dummy_var
        if self.initial_mode == 'chest':
            return self.chest_dummy_var
        if self.initial_mode == 'pelvis':
            return self.pelvis_dummy_var
        if self.initial_mode == 'femur':
            return self.femur_dummy_var
        if self.initial_mode == 'iliac':
            return self.iliac_dummy_var
        if self.initial_mode == 'tibia':
            return self.tibia_dummy_var
        if self.initial_mode == 'knee':
            return self.head_dummy_profile_var
        return self.head_dummy_profile_var

    def _build_ui(self):
        header = tk.Frame(self, bg="#ffffff")
        header.pack(fill=tk.X, padx=16, pady=(16, 8))
        tk.Label(header, text=self._title_text(), font=("Arial", 15, "bold"), bg="#ffffff").pack(side=tk.LEFT)
        tk.Button(header, text="그래프 저장", command=self.save_current_graph).pack(side=tk.RIGHT, padx=6)
        tk.Button(header, text="채널 새로고침", command=self.refresh_channel_lists).pack(side=tk.RIGHT, padx=6)

        body = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#ffffff", bd=0)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        left = tk.Frame(body, bg="#ffffff", width=520)
        left.pack_propagate(False)
        body.add(left, minsize=420)

        self._configure_notebook_style()

        self.left_scroll = VerticalScrolledFrame(left, bg="#ffffff", scrollbar_width=20)
        self.left_scroll.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        left_content = self.left_scroll.content

        self.multi_dummy_panel = MultiDummyPanel(
            left_content,
            dummy_count_var=self.dummy_count_var,
            active_dummy_var=self.active_dummy_var,
            profile_options_getter=self._profile_options,
            on_count_changed=self._on_dummy_count_changed,
            on_active_changed=self._on_active_dummy_changed,
            on_positions_changed=self._on_dummy_positions_changed,
            show_count_row=False,
            show_rows=False,
            show_tabs=True,
            title="더미 위치 탭",
        )
        self.multi_dummy_panel.pack(fill=tk.X, pady=(0, 10))
        self.multi_dummy_panel.notebook.configure(style='InjuryTabs.TNotebook')

        self.control_host = tk.Frame(left_content, bg="#ffffff")
        self.control_host.pack(fill=tk.BOTH, expand=True)

        if self.initial_mode == 'hic':
            self.control_panel = self._build_hic_panel(self.control_host)
        elif self.initial_mode == 'nij':
            self.control_panel = self._build_nij_panel(self.control_host)
        elif self.initial_mode == 'chest':
            self.control_panel = self._build_chest_panel(self.control_host)
        elif self.initial_mode == 'pelvis':
            self.control_panel = self._build_pelvis_panel(self.control_host)
        elif self.initial_mode == 'femur':
            self.control_panel = self._build_femur_panel(self.control_host)
        elif self.initial_mode == 'knee':
            self.control_panel = self._build_knee_panel(self.control_host)
        elif self.initial_mode == 'iliac':
            self.control_panel = self._build_iliac_panel(self.control_host)
        else:
            self.control_panel = self._build_tibia_panel(self.control_host)
        self.control_panel.pack(fill=tk.BOTH, expand=True)

        self.summary_frame = tk.LabelFrame(left, text="결과 요약", bg="#ffffff")
        self.summary_frame.pack(fill=tk.BOTH, padx=0, pady=(0, 0), ipady=0)
        self.summary_text = self._make_result_text(self.summary_frame, height=9)
        self._result_widget = self.summary_text

        right = tk.Frame(body, bg="#ffffff")
        body.add(right, stretch="always", minsize=460)

        self._build_graph_area(right)


    def _configure_notebook_style(self):
        style = ttk.Style()
        try:
            style.theme_use(style.theme_use())
        except Exception:
            pass
        style.configure(
            'InjuryTabs.TNotebook.Tab',
            padding=(10, 2),
            font=('Arial', 9, 'bold'),
            background='#dbeafe',
            foreground='#111111',
        )
        style.map(
            'InjuryTabs.TNotebook.Tab',
            background=[('selected', '#2563eb'), ('active', '#93c5fd'), ('!selected', '#dbeafe')],
            foreground=[('selected', '#111111'), ('active', '#111111'), ('!selected', '#111111')],
        )
        style.configure('InjuryTabs.TNotebook', background='#ffffff', borderwidth=0)

        style.configure(
            'GraphTabs.TNotebook',
            background='#ffffff',
            borderwidth=0,
        )
        style.configure(
            'GraphTabs.TNotebook.Tab',
            padding=(14, 4),
            font=('Arial', 9, 'bold'),
            background='#e5e7eb',
            foreground='#111111',
        )
        style.map(
            'GraphTabs.TNotebook.Tab',
            background=[('selected', '#cbd5e1'), ('active', '#dbeafe'), ('!selected', '#e5e7eb')],
            foreground=[('selected', '#111111'), ('active', '#111111'), ('!selected', '#111111')],
        )
        if hasattr(self, 'multi_dummy_panel') and hasattr(self.multi_dummy_panel, 'notebook'):
            self.multi_dummy_panel.notebook.configure(style='InjuryTabs.TNotebook')

    def _active_positions(self):
        return list(self.active_positions or ['B1'])

    def _detected_position_list(self):
        return [slot for slot in DUMMY_POSITION_OPTIONS if self.detected_groups.get(slot)]

    def _sync_active_positions(self):
        detected = self._detected_position_list()
        valid_requested = []
        used = set()
        for slot in self.requested_row_positions[:self._active_count()]:
            if slot in DUMMY_POSITION_OPTIONS and slot not in used:
                valid_requested.append(slot)
                used.add(slot)
        if not valid_requested and detected:
            valid_requested = detected[:1]
        elif not valid_requested:
            valid_requested = ['B1']
        self.multi_dummy_panel.set_detected_positions(detected)
        self.multi_dummy_panel.set_active_positions(valid_requested[:self._active_count()], explicit_positions=self.requested_row_positions[:self._active_count()])
        self.active_positions = self.multi_dummy_panel.get_selected_positions() or ['B1']
        self.requested_row_positions = self.multi_dummy_panel.get_row_positions()
        self.multi_dummy_panel.refresh_profile_options()
        self.multi_dummy_panel.refresh_tab_labels(self.active_positions)
        self._apply_detected_dummy_profiles()
        self._update_group_info_label()

    def _slot_label(self, slot):
        st = self.slot_states.get(slot) or {}
        name = (st.get('dummy_name') or '').strip()
        base = self.multi_dummy_panel.display_label_for_slot(slot) if hasattr(self, 'multi_dummy_panel') else slot
        return f"{slot}({name})" if name and not base.startswith('empty') and base != name else base
    def _graph_subject_label(self, slot):
        st = self.slot_states.get(slot) or {}
        name = (st.get('dummy_name') or '').strip()
        if name:
            return name
        base = self.multi_dummy_panel.display_label_for_slot(slot) if hasattr(self, 'multi_dummy_panel') else slot
        return base or slot

    def _head_graph_title(self, slot, graph_key='head_xyz'):
        subject = self._graph_subject_label(slot)
        if str(graph_key or '').strip().lower() == 'head_resultant':
            return f"INJURY - HEAD RESULTANT ({subject})"
        return f"INJURY - HEAD ({subject})"

    def _history_message_label(self):
        return {
            'hic': 'Head injury calculated',
            'nij': 'Neck injury calculated',
            'chest': 'Chest injury calculated',
            'pelvis': 'Pelvis injury calculated',
            'femur': 'Femur injury calculated',
            'knee': 'Knee injury calculated',
            'iliac': 'Iliac injury calculated',
            'tibia': 'Tibia injury calculated',
        }.get(self.initial_mode, 'Injury calculation completed')

    def _log_history(self, message, *, event_type='general', slot=None, result_uid=None, graph_uid=None, persist=False):
        if not hasattr(self.workbench, 'add_history_entry'):
            return
        slot = slot or self._active_slot()
        entry = {
            'type': event_type,
            'section': self._section_key().upper(),
            'slot': slot,
            'dummy_position': slot,
            'message': message,
        }
        if result_uid:
            entry['result_uid'] = result_uid
        if graph_uid:
            entry['graph_uid'] = graph_uid
        self.workbench.add_history_entry(entry, persist=persist)

    def _bind_multi_dummy_vars(self):
        for slot in DUMMY_POSITION_OPTIONS:
            name_var = self.multi_dummy_panel.name_var(slot)
            profile_var = self.multi_dummy_panel.profile_var(slot)
            name_var.trace_add('write', lambda *_args, s=slot, v=name_var: self._on_slot_name_changed(s, v.get()))
            profile_var.trace_add('write', lambda *_args, s=slot, v=profile_var: self._on_slot_profile_changed(s, v.get()))

    def _on_slot_name_changed(self, slot, value):
        self.slot_states[slot]['dummy_name'] = (value or '').strip()
        self.multi_dummy_panel.refresh_tab_labels(self._active_positions())
        self._update_combined_summary()

    def _on_slot_profile_changed(self, slot, value):
        self.slot_states[slot]['dummy_profile'] = (value or '').strip()
        if slot == self._active_slot():
            self._dummy_profile_var().set((value or '').strip())

    def _update_combined_summary(self):
        lines = []
        for slot in self._active_positions():
            st = self.slot_states.get(slot) or {}
            summary = (st.get('summary_text') or '-').strip()
            lines.append(f"[{self._slot_label(slot)}]\n{summary}")
        if self._result_widget is not None:
            self._set_result_text(self._result_widget, "\n\n".join(lines) if lines else '-')

    def _apply_slot_meta_to_ui(self, slot):
        state = self.slot_states[slot]
        profile = state.get('dummy_profile') or ''
        self._dummy_profile_var().set(profile)
        self.multi_dummy_panel.profile_var(slot).set(profile)
        self.multi_dummy_panel.name_var(slot).set(state.get('dummy_name') or '')

    def _current_slot_result_text(self):
        return (self.slot_states.get(self._active_slot()) or {}).get('summary_text') or '-'

    def _disable_combobox_mousewheel(self, combo):
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>', '<Shift-MouseWheel>', '<Shift-Button-4>', '<Shift-Button-5>'):
            combo.bind(sequence, lambda _e: 'break')

    def _combo_row(self, parent, label, var, neg_var=None, label_width=18):
        row = tk.Frame(parent, bg="#ffffff")
        row.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(row, text=label, bg="#ffffff", width=label_width, anchor="w").pack(side=tk.LEFT)
        if neg_var is not None:
            tk.Checkbutton(row, text='-', variable=neg_var, onvalue=True, offvalue=False, bg='#ffffff').pack(side=tk.LEFT, padx=(0, 6))
        combo = ttk.Combobox(row, textvariable=var, state="readonly")
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._disable_combobox_mousewheel(combo)
        return combo

    def _make_result_text(self, parent, height=10):
        frame = tk.Frame(parent, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        result_font = tkfont.nametofont("TkDefaultFont").copy()
        result_font.configure(size=10)
        scrollbar = tk.Scrollbar(
            frame,
            orient=tk.VERTICAL,
            width=18,
            relief=tk.GROOVE,
            activebackground="#b8c4d6",
            troughcolor="#eef2f7",
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        widget = tk.Text(
            frame,
            wrap=tk.WORD,
            height=height,
            font=result_font,
            bg="#f8fafc",
            fg="#111827",
            relief=tk.SOLID,
            borderwidth=1,
            padx=10,
            pady=8,
            insertwidth=0,
            takefocus=0,
            cursor="arrow",
            yscrollcommand=scrollbar.set,
        )
        widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=widget.yview)
        widget.configure(state=tk.DISABLED)
        return widget

    def _set_result_text(self, widget, text):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text if text else '-')
        widget.see("1.0")
        widget.configure(state=tk.DISABLED)

    def _build_hic_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="HEAD - HIC / 3ms 계산", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(box, text="선택된 더미 탭의 HEAD 채널을 ISO 코드 앞 2자리(B1~B6) 기준으로 자동 배치합니다.", bg="#ffffff", justify="left", anchor="w", wraplength=420).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="입력 채널 선택", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.hic_x_combo = self._combo_row(inputs, "Head Acc X", self.hic_x_var)
        self.hic_y_combo = self._combo_row(inputs, "Head Acc Y", self.hic_y_var)
        self.hic_z_combo = self._combo_row(inputs, "Head Acc Z", self.hic_z_var)
        row = tk.Frame(box, bg="#ffffff")
        row.pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Checkbutton(
            row,
            text="High-Resolution 3ms Search",
            variable=self.use_high_res_cumulative_3ms_var,
            onvalue=True,
            offvalue=False,
            bg="#ffffff",
        ).pack(side=tk.LEFT)
        tk.Button(row, text="전체 계산", command=self.calculate_hic_bundle_all).pack(side=tk.RIGHT)
        return panel

    def _build_nij_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="NECK - Nij / Neck Injury", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        inputs = tk.LabelFrame(box, text="입력 채널 선택", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.nij_fx_combo = self._combo_row(inputs, "Force Fx", self.nij_fx_var, self.nij_fx_neg_var)
        self.nij_fy_combo = self._combo_row(inputs, "Force Fy", self.nij_fy_var, self.nij_fy_neg_var)
        self.nij_fz_combo = self._combo_row(inputs, "Force Fz *", self.nij_fz_var, self.nij_fz_neg_var)
        self.nij_mx_combo = self._combo_row(inputs, "Moment Mx", self.nij_mx_var, self.nij_mx_neg_var)
        self.nij_my_combo = self._combo_row(inputs, "Moment My *", self.nij_my_var, self.nij_my_neg_var)
        self.nij_mz_combo = self._combo_row(inputs, "Moment Mz", self.nij_mz_var, self.nij_mz_neg_var)
        tk.Label(box, textvariable=self.nij_guidance_var, bg="#ffffff", fg="#555555", justify="left", anchor="w", wraplength=420).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Button(opt, text="전체 계산", command=self.calculate_nij_all).pack(side=tk.RIGHT)
        return panel

    def _build_chest_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="CHEST - FMVSS / V*C", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(box, text="선택된 더미 탭 기준으로 CHEST 가속도 XYZ와 변위 채널을 자동 배치합니다.", bg="#ffffff", justify="left", anchor="w", wraplength=420).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="입력 채널 선택", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.chest_x_combo = self._combo_row(inputs, "Chest Acc X", self.chest_x_var)
        self.chest_y_combo = self._combo_row(inputs, "Chest Acc Y", self.chest_y_var)
        self.chest_z_combo = self._combo_row(inputs, "Chest Acc Z", self.chest_z_var)
        self.chest_disp_combo = self._combo_row(inputs, "Displacement *", self.chest_disp_var)
        tk.Label(box, textvariable=self.chest_guidance_var, bg="#ffffff", fg="#555555", justify="left", anchor="w", wraplength=420).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Checkbutton(
            opt,
            text="High-Resolution 3ms Search",
            variable=self.use_high_res_cumulative_3ms_var,
            onvalue=True,
            offvalue=False,
            bg="#ffffff",
        ).pack(side=tk.LEFT)
        tk.Button(opt, text="전체 계산", command=self.calculate_chest_all).pack(side=tk.RIGHT)
        return panel



    def _legacy_build_pelvis_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="PELVIS - Resultant / 3ms", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            box,
            text="골반 XYZ 가속도 채널로 Resultant와 3ms 지표를 계산합니다.",
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="입력 채널 선택", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.pelvis_x_combo = self._combo_row(inputs, "Pelvis Acc X", self.pelvis_x_var)
        self.pelvis_y_combo = self._combo_row(inputs, "Pelvis Acc Y", self.pelvis_y_var)
        self.pelvis_z_combo = self._combo_row(inputs, "Pelvis Acc Z", self.pelvis_z_var)
        tk.Label(box, textvariable=self.pelvis_guidance_var, bg="#ffffff", fg="#555555", justify="left", anchor="w", wraplength=420).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Checkbutton(
            opt,
            text="High-Resolution 3ms Search",
            variable=self.use_high_res_cumulative_3ms_var,
            onvalue=True,
            offvalue=False,
            bg="#ffffff",
        ).pack(side=tk.LEFT)
        tk.Button(opt, text="전체 계산", command=self.calculate_pelvis_all).pack(side=tk.RIGHT)
        return panel

    def _legacy_build_femur_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="FEMUR - Axial Force", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            box,
            text="좌/우 FEMUR 축력을 입력하면 peak axial force를 계산합니다. 축력 방향이 반대인 데이터는 '-' 옵션으로 보정해 사용할 수 있습니다.",
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="?낅젰 梨꾨꼸 ?좏깮", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.femur_left_combo = self._combo_row(inputs, "Left Femur *", self.femur_left_var)
        self.femur_right_combo = self._combo_row(inputs, "Right Femur *", self.femur_right_var)
        tk.Label(box, textvariable=self.femur_guidance_var, bg="#ffffff", fg="#555555", justify="left", anchor="w", wraplength=420).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Button(opt, text="?꾩껜 怨꾩궛", command=self.calculate_femur_all).pack(side=tk.RIGHT)
        return panel

    def _legacy_graph_tab_specs(self):
        if self.initial_mode == 'hic':
            return [
                ('head_xyz', 'HEAD X/Y/Z'),
                ('head_resultant', 'HEAD RESULTANT'),
            ]
        if self.initial_mode == 'nij':
            return [
                ('fo', 'NECK FO'),
                ('mo', 'NECK MO'),
                ('mocy', 'MOCy'),
                ('nij_components', 'Nij - Components'),
                ('nij_overall', 'Nij - Overall'),
            ]
        if self.initial_mode == 'chest':
            return [
                ('accel', 'Acceleration'),
                ('disp', 'Displacement'),
                ('vc', 'V*C'),
            ]
        return [
            ('left', 'Left'),
            ('right', 'Right'),
            ('combined', 'Combined'),
        ]

    def _build_graph_area(self, parent):
        graph_box = tk.LabelFrame(parent, text='그래프 보기', bg='#ffffff', bd=1, relief=tk.GROOVE)
        graph_box.pack(fill=tk.BOTH, expand=True, padx=(14, 0))

        canvas_host = tk.Frame(graph_box, bg='#ffffff')
        canvas_host.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 8))

        self.ax.set_title('INJURY GRAPH')
        self.ax.set_xlabel('Time (ms)')
        self.ax.set_ylabel('Value')
        self.ax.grid(True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=canvas_host)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tabs_host = tk.Frame(graph_box, bg='#ffffff')
        tabs_host.pack(fill=tk.X, padx=10, pady=(0, 10))
        self._graph_tab_notebook = ttk.Notebook(tabs_host, style='GraphTabs.TNotebook')
        self._graph_tab_notebook.pack(fill=tk.X)
        self._graph_tab_to_key = {}
        self._graph_key_to_tab = {}
        for key, label in self._graph_tab_specs():
            tab = tk.Frame(self._graph_tab_notebook, bg='#ffffff', height=1)
            self._graph_tab_notebook.add(tab, text=label)
            self._graph_tab_to_key[str(tab)] = key
            self._graph_key_to_tab[key] = str(tab)
        self._graph_tab_notebook.bind('<<NotebookTabChanged>>', self._on_graph_tab_changed)
        first_key = self._graph_tab_specs()[0][0] if self._graph_tab_specs() else None
        if first_key:
            self._select_graph_tab(first_key)

    def _select_graph_tab(self, key):
        if not self._graph_tab_notebook:
            return
        tab_id = self._graph_key_to_tab.get(key)
        if not tab_id:
            return
        try:
            current = self._graph_tab_notebook.select()
        except Exception:
            current = None
        if current == tab_id:
            return
        self._updating_graph_tabs = True
        try:
            self._graph_tab_notebook.select(tab_id)
        finally:
            self._updating_graph_tabs = False

    def _on_graph_tab_changed(self, _event=None):
        if self._updating_graph_tabs or not self._graph_tab_notebook:
            return
        key = self._graph_tab_to_key.get(self._graph_tab_notebook.select())
        if not key:
            return
        slot = self._active_slot()
        if self.initial_mode == 'hic':
            self.show_hic_bundle_graph(key, slot=slot, silent=True)
        elif self.initial_mode == 'nij':
            self.show_neck_graph(key, slot=slot, silent=True)
        elif self.initial_mode == 'chest':
            self.show_chest_graph(key, slot=slot, silent=True)
        elif self.initial_mode == 'pelvis':
            self.show_pelvis_graph(key, slot=slot, silent=True)
        elif self.initial_mode == 'femur':
            self.show_femur_graph(key, slot=slot, silent=True)
        elif self.initial_mode == 'knee':
            self.show_knee_graph(key, slot=slot, silent=True)
        elif self.initial_mode == 'iliac':
            self.show_iliac_graph(key, slot=slot, silent=True)
        elif self.initial_mode == 'tibia':
            self.show_tibia_graph(key, slot=slot, silent=True)
        else:
            return
        self._record_graph_selection(slot, key)

    def _legacy_reset_session_state(self):
        self.detected_groups = {}
        self.active_positions = ['B1']
        self.requested_row_positions = ['B1']
        self.current_available_channels = []
        self._display_to_channel = {}
        self._channel_to_display = {}
        self._last_ui_slot = 'B1'
        self.active_plot_key = {}
        self.slot_states = {slot: self._new_slot_state() for slot in DUMMY_POSITION_OPTIONS}

        self.dummy_count_var.set('1')
        self.active_dummy_var.set('B1')
        self.head_dummy_profile_var.set(HEAD_PROFILE_OPTIONS[0] if HEAD_PROFILE_OPTIONS else '')
        self.nij_dummy_var.set('H3_50M_FMVSS208')
        self.chest_dummy_var.set('H3_50M_FMVSS208')
        self.femur_dummy_var.set(FEMUR_PROFILE_OPTIONS[0] if FEMUR_PROFILE_OPTIONS else 'H3_50M_FMVSS208')

        for var in (self.hic_x_var, self.hic_y_var, self.hic_z_var, self.nij_fx_var, self.nij_fy_var, self.nij_fz_var, self.nij_mx_var, self.nij_my_var, self.nij_mz_var, self.chest_x_var, self.chest_y_var, self.chest_z_var, self.chest_disp_var, self.femur_left_var, self.femur_right_var):
            var.set('')
        for var in (self.nij_fx_neg_var, self.nij_fy_neg_var, self.nij_fz_neg_var, self.nij_mx_neg_var, self.nij_my_neg_var, self.nij_mz_neg_var):
            var.set(False)

        self.hic15_var.set('HIC15')
        self.hic36_var.set('HIC36')
        self.clip3_var.set('3ms Clip')
        self.femur_guidance_var.set('Femur axial force는 CFC600 기준으로 계산합니다.')
        self.nij_guidance_var.set('Fx/Fy/Fz 원채널은 CFC1000 권장 | Mx/My/Mz 원채널은 CFC600 권장')

        if hasattr(self, 'multi_dummy_panel'):
            for slot in DUMMY_POSITION_OPTIONS:
                self.multi_dummy_panel.name_var(slot).set('')
                self.multi_dummy_panel.profile_var(slot).set('')
            self.multi_dummy_panel.set_detected_positions([])
            self.multi_dummy_panel.set_active_positions(['B1'], explicit_positions=['B1'])
            self.multi_dummy_panel.set_group_info('검출 위치: 미검출')
            self.multi_dummy_panel.refresh_tab_labels(['B1'])
            self.multi_dummy_panel.refresh_profile_options()

        self._clear_channel_selections()
        if self._result_widget is not None:
            self._set_result_text(self._result_widget, '-')
        self.ax.clear()
        self.ax.set_title('INJURY GRAPH')
        self.ax.set_xlabel('Time (ms)')
        self.ax.set_ylabel('Value')
        self.ax.grid(True)
        self.canvas.draw_idle()
        specs = self._graph_tab_specs()
        if specs:
            self._select_graph_tab(specs[0][0])

    def on_show(self):
        self.apply_shared_dummy_config()
        self.detected_groups = self._detect_dummy_groups()
        self._restore_saved_injury_results()
        self._sync_active_positions()
        self.refresh_channel_lists(keep_existing=True)
        self._sync_all_slot_meta_to_panel()
        self._load_active_slot_state()
        self._refresh_neck_guidance_text()
        self._update_combined_summary()

    def apply_shared_dummy_config(self, config=None):
        config = dict(config or getattr(self.workbench, "get_shared_dummy_config", lambda: {})() or {})
        count = int(config.get('dummy_count') or 1)
        self.dummy_count_var.set(str(min(max(count, 1), 6)))
        row_positions = list(config.get('row_positions') or ['B1'])
        active_positions = list(config.get('active_positions') or ['B1'])
        self.requested_row_positions = row_positions
        self.active_positions = active_positions
        slot_meta = dict(config.get('slot_meta') or {})
        for slot in DUMMY_POSITION_OPTIONS:
            meta = slot_meta.get(slot) or {}
            if 'dummy_name' in meta:
                self.slot_states[slot]['dummy_name'] = str(meta.get('dummy_name') or '').strip()
            if 'dummy_profile' in meta and str(meta.get('dummy_profile') or '').strip():
                self.slot_states[slot]['dummy_profile'] = str(meta.get('dummy_profile') or '').strip()
            try:
                self.multi_dummy_panel.name_var(slot).set(self.slot_states[slot].get('dummy_name') or '')
                self.multi_dummy_panel.profile_var(slot).set(self.slot_states[slot].get('dummy_profile') or '')
            except Exception:
                pass

    def _active_slot(self):
        slot = self.active_dummy_var.get().strip() or 'B1'
        if slot not in self.slot_states:
            slot = 'B1'
        return slot

    def _active_slot_state(self):
        return self.slot_states[self._active_slot()]

    def _first_active_position(self):
        positions = self._active_positions()
        return positions[0] if positions else 'B1'

    def _active_count(self):
        try:
            value = int(self.dummy_count_var.get())
        except Exception:
            value = 1
        return min(max(value, 1), 6)

    def _on_dummy_count_changed(self, *_args):
        self._save_active_slot_state()
        self.requested_row_positions = self.multi_dummy_panel.get_row_positions()
        self.detected_groups = self._detect_dummy_groups()
        self._sync_active_positions()
        current = self._active_slot()
        if current not in self._active_positions():
            self.active_dummy_var.set(self._first_active_position())
        self.refresh_channel_lists(keep_existing=True)
        self._update_combined_summary()

    def _on_dummy_positions_changed(self, *_args):
        self._save_active_slot_state()
        self.requested_row_positions = self.multi_dummy_panel.get_row_positions()
        self.active_positions = self.multi_dummy_panel.get_selected_positions() or ['B1']
        current = self._active_slot()
        if current not in self._active_positions():
            self.active_dummy_var.set(self._first_active_position())
        self.multi_dummy_panel.refresh_tab_labels(self._active_positions())
        self.refresh_channel_lists(keep_existing=True)
        self._update_combined_summary()

    def _on_active_dummy_changed(self, *_args):
        previous_slot = self._last_ui_slot
        if previous_slot in self.slot_states:
            self._save_slot_state(previous_slot)
        self.requested_row_positions = self.multi_dummy_panel.get_row_positions()
        self.active_positions = self.multi_dummy_panel.get_selected_positions() or self.active_positions
        self._load_active_slot_state()
        self._persist_active_slot_selection()
        self.refresh_channel_lists(keep_existing=True)

    def _legacy_save_slot_state(self, slot):
        state = self.slot_states[slot]
        state['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
        state['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
        if self.initial_mode == 'hic':
            state['channels'] = {
                'x': self._selected_channel(self.hic_x_var),
                'y': self._selected_channel(self.hic_y_var),
                'z': self._selected_channel(self.hic_z_var),
            }
        elif self.initial_mode == 'nij':
            state['channels'] = {
                'Fx': self._selected_channel(self.nij_fx_var),
                'Fy': self._selected_channel(self.nij_fy_var),
                'Fz': self._selected_channel(self.nij_fz_var),
                'Mx': self._selected_channel(self.nij_mx_var),
                'My': self._selected_channel(self.nij_my_var),
                'Mz': self._selected_channel(self.nij_mz_var),
            }
            state['neg_flags'] = {
                'Fx': bool(self.nij_fx_neg_var.get()),
                'Fy': bool(self.nij_fy_neg_var.get()),
                'Fz': bool(self.nij_fz_neg_var.get()),
                'Mx': bool(self.nij_mx_neg_var.get()),
                'My': bool(self.nij_my_neg_var.get()),
                'Mz': bool(self.nij_mz_neg_var.get()),
            }
        elif self.initial_mode == 'chest':
            state['channels'] = {
                'x': self._selected_channel(self.chest_x_var),
                'y': self._selected_channel(self.chest_y_var),
                'z': self._selected_channel(self.chest_z_var),
                'disp': self._selected_channel(self.chest_disp_var),
            }
            state['neg_flags'] = {}
        else:
            state['channels'] = {
                'left': self._selected_channel(self.femur_left_var),
                'right': self._selected_channel(self.femur_right_var),
            }
            state['neg_flags'] = {}

    def _save_active_slot_state(self):
        slot = self._active_slot()
        self._save_slot_state(slot)

    def _legacy_load_active_slot_state(self):
        slot = self._active_slot()
        self._last_ui_slot = slot
        state = self.slot_states[slot]
        profile_var = self._dummy_profile_var()
        if state.get('dummy_profile'):
            profile_var.set(state['dummy_profile'])
        elif not profile_var.get() and self._profile_options():
            profile_var.set(self._profile_options()[0])
        self._apply_slot_meta_to_ui(slot)
        self._apply_slot_channels_to_ui(state.get('channels') or {})
        if self.initial_mode == 'nij':
            neg = state.get('neg_flags') or {}
            self.nij_fx_neg_var.set(bool(neg.get('Fx', False)))
            self.nij_fy_neg_var.set(bool(neg.get('Fy', False)))
            self.nij_fz_neg_var.set(bool(neg.get('Fz', False)))
            self.nij_mx_neg_var.set(bool(neg.get('Mx', False)))
            self.nij_my_neg_var.set(bool(neg.get('My', False)))
            self.nij_mz_neg_var.set(bool(neg.get('Mz', False)))
        self._update_combined_summary()
        graph_key = state.get('graph_key')
        if graph_key:
            self._show_saved_graph_for_slot(slot, graph_key)

    def _legacy_apply_slot_channels_to_ui(self, channels):
        if self.initial_mode == 'hic':
            self._set_var_from_channel(self.hic_x_var, channels.get('x'))
            self._set_var_from_channel(self.hic_y_var, channels.get('y'))
            self._set_var_from_channel(self.hic_z_var, channels.get('z'))
        elif self.initial_mode == 'nij':
            self._set_var_from_channel(self.nij_fx_var, channels.get('Fx'))
            self._set_var_from_channel(self.nij_fy_var, channels.get('Fy'))
            self._set_var_from_channel(self.nij_fz_var, channels.get('Fz'))
            self._set_var_from_channel(self.nij_mx_var, channels.get('Mx'))
            self._set_var_from_channel(self.nij_my_var, channels.get('My'))
            self._set_var_from_channel(self.nij_mz_var, channels.get('Mz'))
        elif self.initial_mode == 'chest':
            self._set_var_from_channel(self.chest_x_var, channels.get('x'))
            self._set_var_from_channel(self.chest_y_var, channels.get('y'))
            self._set_var_from_channel(self.chest_z_var, channels.get('z'))
            self._set_var_from_channel(self.chest_disp_var, channels.get('disp'))
        else:
            self._set_var_from_channel(self.femur_left_var, channels.get('left'))
            self._set_var_from_channel(self.femur_right_var, channels.get('right'))

    def _apply_summary_text(self, text):
        if self.initial_mode == 'hic':
            self.hic15_var.set('HIC15')
            self.hic36_var.set('HIC36')
            self.clip3_var.set('3ms Clip')
        self._update_combined_summary()

    def _normalize_channel_reference(self, value):
        raw = str(value or '').strip()
        if not raw or raw == BLANK_DISPLAY_VALUE:
            return ''
        viewer = self.workbench.viewer
        df = getattr(viewer, 'df', None)
        columns = set(getattr(df, 'columns', []) if df is not None else [])
        if raw in columns:
            return raw
        mapped = self._display_to_channel.get(raw)
        if mapped:
            return mapped
        candidate = raw
        while True:
            stripped = re.sub(r'\s*\[[^\]]*\]\s*$', '', candidate).strip()
            if stripped == candidate:
                break
            candidate = stripped
            mapped = self._display_to_channel.get(candidate)
            if mapped:
                return mapped
            if candidate in columns:
                return candidate
        return candidate if candidate in columns else raw

    def _selected_channel(self, var):
        return self._normalize_channel_reference(var.get())

    def _set_var_from_channel(self, var, channel):
        channel = self._normalize_channel_reference(channel)
        if not channel:
            var.set(BLANK_DISPLAY_VALUE)
            return
        display = self._channel_to_display.get(channel)
        if not display:
            viewer = self.workbench.viewer
            filter_label = viewer.get_current_filter_title_label(channel) if getattr(viewer, 'df', None) is not None and channel in getattr(viewer.df, 'columns', []) else 'Raw'
            display = f"{channel} [{filter_label}]"
        var.set(display)

    def _get_time(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            return None
        return viewer.get_numeric_column(viewer.time_column)

    def _time_to_display_ms(self, values):
        return np.asarray(values, dtype=float) * 1000.0

    def _time_value_valid_mask(self, time_arr, values):
        t = np.asarray(time_arr, dtype=float)
        v = np.asarray(values, dtype=float)
        n = min(len(t), len(v))
        if n <= 0:
            return np.array([], dtype=bool), t[:0], v[:0]
        t2 = t[:n]
        v2 = v[:n]
        return np.isfinite(t2) & np.isfinite(v2), t2, v2

    def _time_value_valid_mask_ms(self, time_arr, values):
        mask, arr_t, arr_v = self._time_value_valid_mask(time_arr, values)
        return mask, self._time_to_display_ms(arr_t), arr_v

    def _fmt_time_ms(self, value, decimals=1):
        return fmt_time_ms(value, decimals)

    def _x_axis_label(self):
        return 'Time (ms)'

    def _injury_metadata_bundle(self):
        metadata = dict(getattr(self.workbench, 'dataset_metadata', {}) or {})
        return dict(metadata.get('injury_saved_results') or {})

    def _dataset_identity_text(self):
        metadata = dict(getattr(self.workbench, 'dataset_metadata', {}) or {})
        return str(metadata.get('source_file_path') or getattr(self.workbench, 'original_source_path', None) or getattr(self.workbench, 'source_file_label', None) or '')

    def _injury_result_uid(self, slot):
        seed = f"{self._dataset_identity_text()}|{self._section_key()}|{slot}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    def _sync_all_slot_meta_to_panel(self):
        if not hasattr(self, 'multi_dummy_panel'):
            return
        for slot in DUMMY_POSITION_OPTIONS:
            state = self.slot_states.get(slot) or {}
            self.multi_dummy_panel.name_var(slot).set(state.get('dummy_name') or '')
            self.multi_dummy_panel.profile_var(slot).set(state.get('dummy_profile') or '')

    def _persist_graph_metadata_to_current_pickle(self):
        current_file = getattr(self.workbench, 'current_file_path', None)
        if not current_file or not str(current_file).lower().endswith(DATASET_EXT):
            return
        dataframe = getattr(self.workbench, 'working_df', None)
        if dataframe is None:
            dataframe = getattr(self.workbench.viewer, 'df', None)
        if dataframe is None:
            return
        save_dataset_pickle(
            current_file,
            dataframe,
            metadata=dict(getattr(self.workbench, 'dataset_metadata', {}) or {}),
            history=list(getattr(self.workbench, 'history', []) or []),
            source_file_path=getattr(self.workbench, 'original_source_path', None) or getattr(self.workbench, 'source_file_label', None),
            source_label=getattr(self.workbench, 'source_file_label', None),
        )

    def _injury_graph_uid(self, slot, graph_key):
        seed = f"{self._dataset_identity_text()}|{self._section_key()}|{slot}|{graph_key}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    def _slot_saved_payload_key(self):
        return {
            'hic': 'head_metadata',
            'nij': 'neck_saved_payload',
            'chest': 'chest_saved_payload',
            'pelvis': 'pelvis_saved_payload',
            'femur': 'femur_saved_payload',
            'knee': 'knee_saved_payload',
            'iliac': 'iliac_saved_payload',
            'tibia': 'tibia_saved_payload',
        }.get(self.initial_mode)

    def _preferred_graph_key(self, slot, default_key):
        key = (self.slot_states.get(slot) or {}).get('graph_key') or default_key
        if self.initial_mode == 'hic':
            key = self._normalize_head_graph_key(key)
        elif self.initial_mode == 'nij':
            key = self._normalize_neck_graph_key(key)
        valid_keys = {spec_key for spec_key, _label in self._graph_tab_specs()}
        return key if key in valid_keys else default_key

    def _default_graph_key(self, fallback_key=''):
        specs = self._graph_tab_specs()
        if specs:
            return specs[0][0]
        return fallback_key

    def _record_graph_selection(self, slot, graph_key):
        if slot not in self.slot_states:
            return
        state = self.slot_states[slot]
        graph_uid = self._injury_graph_uid(slot, graph_key)
        state['graph_key'] = graph_key
        state['graph_uid'] = graph_uid
        payload_key = self._slot_saved_payload_key()
        if payload_key:
            payload = dict(state.get(payload_key) or {})
            payload['graph_key'] = graph_key
            payload['graph_uid'] = graph_uid
            state[payload_key] = payload

        metadata = dict(getattr(self.workbench, 'dataset_metadata', {}) or {})
        injury_saved = dict(metadata.get('injury_saved_results') or {})
        section_payload = dict(injury_saved.get(self._section_key()) or {})
        slots_payload = dict(section_payload.get('slots') or {})
        slot_payload = dict(slots_payload.get(slot) or {})
        slot_payload['graph_key'] = graph_key
        slot_payload['graph_uid'] = graph_uid
        slots_payload[slot] = slot_payload
        section_payload['slots'] = slots_payload
        injury_saved[self._section_key()] = section_payload

        graph_registry = dict(metadata.get('injury_graph_registry') or {})
        graph_registry[graph_uid] = {
            'section_key': self._section_key(),
            'slot': slot,
            'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
            'graph_key': graph_key,
            'dummy_name': state.get('dummy_name') or '',
            'dummy_profile': state.get('dummy_profile') or '',
            'source_file_path': self._dataset_identity_text(),
            'storage': 'rebuild_from_dataset',
        }

        metadata['injury_saved_results'] = injury_saved
        metadata['injury_graph_registry'] = graph_registry
        self.workbench.dataset_metadata = metadata
        self._persist_graph_metadata_to_current_pickle()

    def _persist_active_slot_selection(self, slot=None):
        slot = slot or self._active_slot()
        metadata = dict(getattr(self.workbench, 'dataset_metadata', {}) or {})
        injury_saved = dict(metadata.get('injury_saved_results') or {})
        section_payload = dict(injury_saved.get(self._section_key()) or {})
        if not section_payload:
            return
        section_payload['active_slot'] = slot
        injury_saved[self._section_key()] = section_payload
        metadata['injury_saved_results'] = injury_saved
        self.workbench.dataset_metadata = metadata
        self._persist_graph_metadata_to_current_pickle()

    def _legacy_build_section_payload(self):
        slots_payload = {}
        for slot in self._active_positions():
            st = self.slot_states[slot]
            payload = {}
            if self.initial_mode == 'hic':
                payload.update(dict(st.get('head_metadata') or {}))
            elif self.initial_mode == 'nij':
                payload.update(dict(st.get('neck_saved_payload') or {}))
            elif self.initial_mode == 'chest':
                payload.update(dict(st.get('chest_saved_payload') or {}))
            else:
                payload.update(dict(st.get('femur_saved_payload') or {}))
            payload.update({
                'result_uid': st.get('result_uid') or self._injury_result_uid(slot),
                'section_key': self._section_key(),
                'slot': slot,
                'dummy_name': st.get('dummy_name') or '',
                'dummy_profile': st.get('dummy_profile') or '',
                'channels': dict(st.get('channels') or {}),
                'neg_flags': dict(st.get('neg_flags') or {}),
                'summary_text': st.get('summary_text') or '-',
                'graph_key': st.get('graph_key'),
                'graph_uid': st.get('graph_uid') or (self._injury_graph_uid(slot, st.get('graph_key')) if st.get('graph_key') else ''),
            })
            payload = self._enrich_payload_with_structured_results(payload, st)
            payload_key = self._slot_saved_payload_key()
            if payload_key:
                st[payload_key] = dict(payload)
            slots_payload[slot] = payload
        return {
            'dummy_count': self._active_count(),
            'active_slot': self._active_slot(),
            'active_positions': list(self._active_positions()),
            'row_positions': list(self.requested_row_positions[:self._active_count()]),
            'detected_groups': {k: list(v) for k, v in self.detected_groups.items()},
            'slots': slots_payload,
            'result_registry': {slot: (payload.get('result_uid') or self._injury_result_uid(slot)) for slot, payload in slots_payload.items()},
        }

    def _save_section_payload(self, history_text, dataframe=None, metadata_extra=None, op_suffix='_I'):
        viewer = self.workbench.viewer
        base_df = dataframe.copy(deep=True) if dataframe is not None else viewer.df.copy(deep=True)
        injury_saved = self._injury_metadata_bundle()
        injury_saved[self._section_key()] = self._build_section_payload()
        metadata = dict(getattr(self.workbench, 'dataset_metadata', {}) or {})
        result_registry = dict(metadata.get('injury_result_registry') or {})
        graph_registry = dict(metadata.get('injury_graph_registry') or {})
        section_payload = injury_saved.get(self._section_key()) or {}
        for slot, payload in dict(section_payload.get('slots') or {}).items():
            uid = payload.get('result_uid') or self._injury_result_uid(slot)
            result_registry[uid] = {
                'section_key': self._section_key(),
                'slot': slot,
                'dummy_name': payload.get('dummy_name') or '',
                'dummy_profile': payload.get('dummy_profile') or '',
                'channels': dict(payload.get('channels') or {}),
                'source_file_path': self._dataset_identity_text(),
            }
            graph_key = payload.get('graph_key')
            if graph_key:
                graph_uid = payload.get('graph_uid') or self._injury_graph_uid(slot, graph_key)
                graph_registry[graph_uid] = {
                    'section_key': self._section_key(),
                    'slot': slot,
                    'result_uid': uid,
                    'graph_key': graph_key,
                    'dummy_name': payload.get('dummy_name') or '',
                    'dummy_profile': payload.get('dummy_profile') or '',
                    'source_file_path': self._dataset_identity_text(),
                    'storage': 'rebuild_from_dataset',
                }
        metadata_override = {'injury_saved_results': injury_saved, 'injury_result_registry': result_registry, 'injury_graph_registry': graph_registry}
        if metadata_extra:
            metadata_override.update(metadata_extra)
        return self.workbench.apply_processed_dataframe(base_df, history_text, op_suffix=op_suffix, metadata_override=metadata_override)

    def _legacy_restore_saved_injury_results(self):
        saved = self._injury_metadata_bundle().get(self._section_key()) or {}
        if not saved:
            return
        count = int(saved.get('dummy_count') or 1)
        self.dummy_count_var.set(str(min(max(count, 1), 6)))
        self.detected_groups = {k: list(v) for k, v in dict(saved.get('detected_groups') or {}).items()}
        if not self.detected_groups:
            self.detected_groups = self._detect_dummy_groups()
        for slot in DUMMY_POSITION_OPTIONS:
            payload = dict((saved.get('slots') or {}).get(slot) or {})
            st = self.slot_states[slot]
            st['result_uid'] = payload.get('result_uid') or st.get('result_uid') or self._injury_result_uid(slot)
            st['dummy_name'] = payload.get('dummy_name') or st.get('dummy_name') or ''
            st['dummy_profile'] = payload.get('dummy_profile') or st.get('dummy_profile') or ''
            st['channels'] = dict(payload.get('channels') or {})
            st['neg_flags'] = dict(payload.get('neg_flags') or {})
            payload_version = int(payload.get('summary_format_version') or 0)
            st['summary_text'] = payload.get('summary_text') or '-'
            if payload_version and payload_version < SUMMARY_FORMAT_VERSION:
                st['summary_text'] = '-'
            if 'use_high_res_cumulative_3ms' in payload:
                st['use_high_res_cumulative_3ms'] = bool(payload.get('use_high_res_cumulative_3ms'))
            elif 'high_res_3ms_sliding_window' in payload:
                st['use_high_res_cumulative_3ms'] = bool(payload.get('high_res_3ms_sliding_window'))
            restored_graph_key = payload.get('graph_key')
            if self.initial_mode == 'nij':
                restored_graph_key = self._normalize_neck_graph_key(restored_graph_key)
            st['graph_key'] = restored_graph_key
            st['graph_uid'] = payload.get('graph_uid') or (self._injury_graph_uid(slot, restored_graph_key) if restored_graph_key else '')
            if self.initial_mode == 'hic':
                st['head_metadata'] = payload
            elif self.initial_mode == 'nij':
                st['neck_saved_payload'] = payload
            elif self.initial_mode == 'chest':
                st['chest_saved_payload'] = payload
            else:
                st['femur_saved_payload'] = payload
        restored_positions = [slot for slot in (saved.get('active_positions') or []) if slot in DUMMY_POSITION_OPTIONS]
        if restored_positions:
            self.active_positions = restored_positions[:self._active_count()]
        saved_row_positions = list(saved.get('row_positions') or [])
        if saved_row_positions:
            self.requested_row_positions = saved_row_positions[:self._active_count()]
        active_slot = saved.get('active_slot') or 'B1'
        self._sync_all_slot_meta_to_panel()
        if active_slot in self._active_positions():
            self.active_dummy_var.set(active_slot)
        if active_slot in self.slot_states and self.slot_states[active_slot].get('summary_text') == '-':
            if self._ensure_slot_plot_data(active_slot):
                self._apply_summary_text(self.slot_states[active_slot].get('summary_text') or '-')
        self._update_group_info_label()

    def _legacy_ensure_slot_plot_data(self, slot):
        state = self.slot_states.get(slot) or {}
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            return False
        try:
            if self.initial_mode == 'hic':
                if state.get('head_bundle'):
                    return True
                channels = dict(state.get('channels') or {})
                x_ch, y_ch, z_ch = channels.get('x'), channels.get('y'), channels.get('z')
                if not (x_ch and y_ch and z_ch):
                    return False
                time = self._get_time()
                x, _ = self._resolve_standard_series_for_calc(x_ch, 'head_injury', 'x', 1000, 1.0)
                y, _ = self._resolve_standard_series_for_calc(y_ch, 'head_injury', 'y', 1000, 1.0)
                z, _ = self._resolve_standard_series_for_calc(z_ch, 'head_injury', 'z', 1000, 1.0)
                resultant = compute_resultant_xyz(x, y, z)
                resultant_channel = self._head_resultant_channel_name(slot)
                result = build_head_injury_bundle(
                    time=time,
                    resultant_g=self._convert_resultant_to_g(resultant, (x_ch, y_ch, z_ch)),
                    x_plot=self._convert_channel_to_head_plot_unit(x, x_ch),
                    y_plot=self._convert_channel_to_head_plot_unit(y, y_ch),
                    z_plot=self._convert_channel_to_head_plot_unit(z, z_ch),
                    plot_unit=self._head_plot_unit((x_ch, y_ch, z_ch)),
                    channels=(x_ch, y_ch, z_ch),
                    resultant_channel=resultant_channel,
                    resultant_filter_label='CFC 1000',
                    use_high_res_cumulative_3ms=self._slot_use_high_res_cumulative_3ms(slot),
                )
                state['head_bundle'] = result['bundle']
                meta = dict(result.get('metadata') or {})
                meta['dummy_name'] = state.get('dummy_name') or ''
                meta['dummy_profile'] = state.get('dummy_profile') or ''
                meta['channels'] = dict(channels)
                meta['use_high_res_cumulative_3ms'] = self._slot_use_high_res_cumulative_3ms(slot)
                state['head_metadata'] = meta
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                state['use_high_res_cumulative_3ms'] = self._slot_use_high_res_cumulative_3ms(slot)
                return True

            if self.initial_mode == 'nij':
                if state.get('neck_metrics'):
                    return True
                selected = dict(state.get('channels') or {})
                if not selected.get('Fz') or not selected.get('My'):
                    return False
                neg_flags = dict(state.get('neg_flags') or {})
                sign_flags = {key: (-1.0 if bool(neg_flags.get(key, False)) else 1.0) for key in ('Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz')}
                result = calculate_neck_injury_bundle(
                    time=self._get_time(),
                    selected=selected,
                    sign_flags=sign_flags,
                    viewer=viewer,
                    criterion_key=state.get('dummy_profile') or self.nij_dummy_var.get(),
                    unit_getter=self._unit_text,
                    channel_desc_getter=lambda ch: viewer.get_channel_display_name(ch) if ch else '-',
                    resolve_series_for_calc=lambda source_channel, role, desired_cfc, sign: self._resolve_standard_series_for_calc(source_channel, 'neck_injury', role, desired_cfc, sign),
                )
                state['neck_metrics'] = result['metrics']
                if not state.get('neck_saved_payload'):
                    state['neck_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.nij_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(selected),
                        'neg_flags': dict(neg_flags),
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                return True

            if self.initial_mode == 'chest' and state.get('chest_metrics'):
                return True
            if self.initial_mode == 'chest':
                channels = dict(state.get('channels') or {})
                x_ch, y_ch, z_ch, disp_ch = channels.get('x'), channels.get('y'), channels.get('z'), channels.get('disp')
                if not all((x_ch, y_ch, z_ch, disp_ch)):
                    return False
                raw_disp_series = self._align_original_series(disp_ch)
                if raw_disp_series is not None:
                    raw_disp_series = np.asarray(raw_disp_series, dtype=float)
                raw_accel_series = {
                    'x': self._align_original_series(x_ch),
                    'y': self._align_original_series(y_ch),
                    'z': self._align_original_series(z_ch),
                }
                raw_accel_series = {k: (None if v is None else np.asarray(v, dtype=float)) for k, v in raw_accel_series.items()}
                disp_prefiltered = {k: np.asarray(v, dtype=float) for k, v in dict(self._collect_chest_disp_prefiltered(disp_ch) or {}).items()}
                x_calc, used_x = self._resolve_standard_series_for_calc(x_ch, 'chest_injury', 'x', 180, 1.0)
                y_calc, used_y = self._resolve_standard_series_for_calc(y_ch, 'chest_injury', 'y', 180, 1.0)
                z_calc, used_z = self._resolve_standard_series_for_calc(z_ch, 'chest_injury', 'z', 180, 1.0)
                x_calc = np.asarray(x_calc, dtype=float)
                y_calc = np.asarray(y_calc, dtype=float)
                z_calc = np.asarray(z_calc, dtype=float)
                disp_calc = np.asarray(viewer.get_numeric_column(disp_ch), dtype=float)
                result = calculate_chest_injury_bundle(
                    time=self._get_time(),
                    x_values=x_calc,
                    y_values=y_calc,
                    z_values=z_calc,
                    disp_values=disp_calc,
                    accel_units={'x': self._unit_text(x_ch), 'y': self._unit_text(y_ch), 'z': self._unit_text(z_ch)},
                    disp_unit=self._unit_text(disp_ch),
                    criterion_key=state.get('dummy_profile') or self.chest_dummy_var.get(),
                    raw_displacement=raw_disp_series,
                    raw_accel=raw_accel_series,
                    accel_filter_labels={
                        'x': self._channel_filter_label_for_calc(x_ch, used_x),
                        'y': self._channel_filter_label_for_calc(y_ch, used_y),
                        'z': self._channel_filter_label_for_calc(z_ch, used_z),
                    },
                    disp_filter_label=self._channel_filter_label_for_calc(disp_ch),
                    disp_prefiltered=disp_prefiltered,
                    vc_sign_pref=1.0,
                    use_high_res_cumulative_3ms=self._slot_use_high_res_cumulative_3ms(slot),
                )
                state['chest_metrics'] = result['metrics']
                state['use_high_res_cumulative_3ms'] = self._slot_use_high_res_cumulative_3ms(slot)
                if not state.get('chest_saved_payload'):
                    rp = result['metrics'].get('resultant_peak', {})
                    state['chest_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.chest_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(channels),
                        'neg_flags': {},
                        'use_high_res_cumulative_3ms': state['use_high_res_cumulative_3ms'],
                        'resultant_peak_g': float(rp['value']) if rp.get('value') is not None else None,
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = state.get('summary_text') or result.get('summary_text') or '-'
                return True

            if state.get('femur_metrics'):
                return True
            channels = dict(state.get('channels') or {})
            left_ch, right_ch = channels.get('left'), channels.get('right')
            if not (left_ch and right_ch):
                return False
            neg_flags = dict(state.get('neg_flags') or {})
            left_sign = -1.0 if bool(neg_flags.get('left', False)) else 1.0
            right_sign = -1.0 if bool(neg_flags.get('right', False)) else 1.0
            left_force, _ = self._resolve_standard_series_for_calc(left_ch, 'femur_injury', 'left', 600, left_sign)
            right_force, _ = self._resolve_standard_series_for_calc(right_ch, 'femur_injury', 'right', 600, right_sign)
            result = calculate_femur_injury_bundle(
                time=self._get_time(),
                left_force=np.asarray(left_force, dtype=float),
                right_force=np.asarray(right_force, dtype=float),
                criterion_key=state.get('dummy_profile') or self.femur_dummy_var.get(),
                left_unit=self._unit_text(left_ch),
                right_unit=self._unit_text(right_ch),
            )
            state['femur_metrics'] = result['metrics']
            if not state.get('femur_saved_payload'):
                state['femur_saved_payload'] = {
                    'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                    'summary_text': result['summary_text'],
                    'criterion_key': state.get('dummy_profile') or self.femur_dummy_var.get(),
                    'dummy_name': state.get('dummy_name') or '',
                    'dummy_profile': state.get('dummy_profile') or '',
                    'channels': dict(channels),
                    'neg_flags': dict(neg_flags),
                    'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                }
            state['summary_text'] = state.get('summary_text') or result.get('summary_text') or '-'
            return True
        except Exception:
            return False

    def _legacy_show_saved_graph_for_slot(self, slot, graph_key):
        if not self._ensure_slot_plot_data(slot):
            return
        if self.initial_mode == 'hic':
            self.show_hic_bundle_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'nij':
            self.show_neck_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'chest':
            self.show_chest_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'femur':
            self.show_femur_graph(graph_key, slot=slot, silent=True)

    def _numeric_channels(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            return []
        derived = set(dict((self.workbench.dataset_metadata or {}).get('derived_channels') or {}).keys())
        result = []
        for ch in viewer.get_numeric_channel_names(exclude_time=True):
            label = str((self.workbench.channel_filter_labels or {}).get(ch, '') or '').strip().upper()
            if ch in derived or label == 'CALC':
                continue
            result.append(ch)
        return result

    def _display_name(self, viewer, channel, used=None):
        filter_label = viewer.get_current_filter_title_label(channel)
        display = f"{channel} [{filter_label}]"
        if used is not None and display in used:
            display = f"{display} [{len(used)+1}]"
        return display

    def _isocode_parsed_map(self):
        metadata = dict(getattr(self.workbench, 'dataset_metadata', {}) or {})
        return dict(metadata.get('isocode_parsed_map') or {})

    def _channel_metadata_map(self):
        metadata = dict(getattr(self.workbench, 'dataset_metadata', {}) or {})
        return dict(metadata.get('channel_metadata_map') or {})

    def _channel_metadata(self, channel_name):
        return dict(self._channel_metadata_map().get(channel_name) or {})

    def _parsed_channel_info(self, channel_name):
        info = self._channel_metadata(channel_name)
        parsed = dict(info.get('isocode_parsed') or {})
        if parsed:
            return parsed
        return dict(self._isocode_parsed_map().get(channel_name) or {})

    def _channel_filter_code(self, channel_name):
        info = self._channel_metadata(channel_name)
        code = str(info.get('current_filter_code') or '').strip().upper()
        if code:
            return code
        parsed = self._parsed_channel_info(channel_name)
        code = str(parsed.get('filter_code_source') or '').strip().upper()
        if code:
            return code
        viewer = self.workbench.viewer
        label = viewer.get_current_filter_title_label(channel_name) if hasattr(viewer, 'get_current_filter_title_label') else ''
        if not label or str(label).strip().lower() == 'raw':
            label = (self.workbench.channel_filter_labels or {}).get(channel_name, '') or label
        return str(normalize_filter_label_to_code(label) or '').strip().upper()

    def _filter_preference_score(self, channel_name, preferred_codes=()):
        preferred = tuple(str(code or '').strip().upper() for code in (preferred_codes or ()) if str(code or '').strip())
        code = self._channel_filter_code(channel_name)
        if not code:
            return 0
        if preferred and code in preferred:
            return 48 - preferred.index(code) * 4
        if code in FILTERED_ISOCODE_CODES:
            return 16
        if code == 'P':
            return 4
        if code == '0':
            return 0
        return 2

    def _channel_filter_label_for_calc(self, selected_channel, used_channel=None):
        for channel in (used_channel, selected_channel):
            if not channel:
                continue
            info = self._channel_metadata(channel)
            label = str(info.get('current_filter_label') or '').strip()
            if label:
                return label
            label = str((self.workbench.channel_filter_labels or {}).get(channel) or '').strip()
            if label:
                return label
        return 'Raw'

    def _preferred_filter_codes(self, mode_key, role_key):
        role_map = dict(FILTER_PREFERENCE_MAP.get(str(mode_key or '').strip(), {}) or {})
        return tuple(role_map.get(role_key, ()) or ())


    def _channel_input_spec(self, mode_key, role_key):
        mode_specs = dict(CHANNEL_INPUT_ROLE_SPECS.get(str(mode_key or '').strip(), {}) or {})
        return dict(mode_specs.get(role_key, {}) or {})

    def _channel_matches_input_spec(self, channel_name, mode_key, role_key):
        spec = self._channel_input_spec(mode_key, role_key)
        if not spec:
            return True
        parsed = self._parsed_channel_info(channel_name)
        if not parsed:
            return False
        for field, expected in spec.items():
            if expected is None or expected == '':
                continue
            actual = str(parsed.get(field) or '').strip().lower()
            if actual != str(expected).strip().lower():
                return False
        return True

    def _is_strict_blank_role(self, mode_key, role_key):
        return (str(mode_key or '').strip(), str(role_key or '').strip()) in STRICT_BLANK_ROLE_KEYS

    def _parsed_match_score(
        self,
        channel_name,
        *,
        sensor_location=None,
        data_type_code=None,
        axis_code=None,
        side=None,
        level=None,
        position_detail=None,
        main_location_code=None,
        preferred_filter_codes=(),
    ):
        parsed = self._parsed_channel_info(channel_name)
        if not parsed:
            return -80

        score = 0

        def _match_value(actual, expected, good=24, bad=30):
            nonlocal score
            if expected is None or expected == '':
                return
            actual_norm = str(actual or '').strip().lower()
            expected_norm = str(expected or '').strip().lower()
            if not actual_norm:
                score -= max(4, bad // 3)
            elif actual_norm == expected_norm:
                score += good
            else:
                score -= bad

        actual_sensor = str(parsed.get('sensor_location') or '').strip().lower()
        if sensor_location is not None:
            exp = str(sensor_location or '').strip().lower()
            if not actual_sensor:
                score -= 12
            elif actual_sensor == exp:
                score += 42
            else:
                score -= 90

        actual_type = str(parsed.get('data_type_code') or '').strip().upper()
        if data_type_code is not None:
            exp = str(data_type_code or '').strip().upper()
            if not actual_type:
                score -= 10
            elif actual_type == exp:
                score += 34
            else:
                score -= 80

        actual_axis = str(parsed.get('axis_code') or '').strip().upper()
        if axis_code is not None:
            exp = str(axis_code or '').strip().upper()
            if not actual_axis:
                score -= 8
            elif actual_axis == exp:
                score += 28
            else:
                score -= 60

        _match_value(parsed.get('side'), side, good=18, bad=24)
        _match_value(parsed.get('level'), level, good=18, bad=24)
        _match_value(parsed.get('position_detail'), position_detail, good=18, bad=24)

        actual_main = str(parsed.get('main_location_code') or '').strip().upper()
        if main_location_code is not None:
            exp = str(main_location_code or '').strip().upper()
            if not actual_main:
                score -= 8
            elif actual_main == exp:
                score += 22
            else:
                score -= 36

        score += self._filter_preference_score(channel_name, preferred_filter_codes)
        return score

    def _best_channel_by_score(self, channels, scorer, exclude=()):
        exclude = set(v for v in (exclude or ()) if v)
        best = ''
        best_score = -10**9
        for ch in list(channels or []):
            if ch in exclude:
                continue
            score = scorer(ch)
            if score > best_score:
                best = ch
                best_score = score
        return best, best_score

    def _infer_dummy_type_for_slot(self, slot):
        counts = {}
        for channel in list(self.detected_groups.get(slot) or []):
            dummy_type = str((self._parsed_channel_info(channel) or {}).get('dummy_type_code') or '').strip().upper()
            if not dummy_type:
                continue
            counts[dummy_type] = counts.get(dummy_type, 0) + 1
        if not counts:
            return ''
        return max(counts.items(), key=lambda item: (item[1], item[0]))[0]

    def _infer_profile_for_slot(self, slot):
        dummy_type = self._infer_dummy_type_for_slot(slot)
        options = list(self._profile_options())
        if not options:
            return ''
        inferred = infer_dummy_profile_from_codes(dummy_type, test_mode='FRONTAL', module=self._section_key())
        if inferred in options:
            return inferred
        if inferred:
            inferred_upper = str(inferred).upper()
            for option in options:
                if str(option).upper() == inferred_upper:
                    return option
        return ''

    def _apply_detected_dummy_profiles(self):
        if not hasattr(self, 'multi_dummy_panel'):
            return
        for slot in DUMMY_POSITION_OPTIONS:
            inferred = self._infer_profile_for_slot(slot)
            if not inferred:
                continue
            state = self.slot_states.get(slot) or {}
            current = str(state.get('dummy_profile') or self.multi_dummy_panel.profile_var(slot).get() or '').strip()
            if current:
                continue
            state['dummy_profile'] = inferred
            self.multi_dummy_panel.profile_var(slot).set(inferred)
            if slot == self._active_slot():
                self._dummy_profile_var().set(inferred)

    def _detect_dummy_groups(self):
        viewer = self.workbench.viewer
        groups = {slot: [] for slot in DUMMY_POSITION_OPTIONS}
        for ch in self._numeric_channels():
            parsed = self._parsed_channel_info(ch)
            parsed_slot = str(parsed.get('dummy_position_normalized') or '').strip().upper()
            if parsed_slot in groups:
                if ch not in groups[parsed_slot]:
                    groups[parsed_slot].append(ch)
                continue
            desc = (viewer.get_channel_display_name(ch) or '').strip()
            for text in (str(ch), desc):
                m = DUMMY_SLOT_PREFIX_RE.search(text)
                if m:
                    slot = m.group(1).upper()
                    if ch not in groups[slot]:
                        groups[slot].append(ch)
                    break
        return {k: v for k, v in groups.items() if v}

    def _update_group_info_label(self):
        detected = self._detected_position_list()
        if not detected:
            self.multi_dummy_panel.set_group_info('검출 위치: 미검출')
            return
        self.multi_dummy_panel.set_group_info('검출 위치: ' + ', '.join(detected))

    def _candidate_channels_for_active_slot(self):
        slot = self._active_slot()
        grouped = list(self.detected_groups.get(slot) or [])
        if grouped:
            return grouped
        return list(self._numeric_channels())

    def _is_placeholder_slot(self, slot=None):
        slot = slot or self._active_slot()
        return bool(getattr(self, 'multi_dummy_panel', None) and self.multi_dummy_panel.is_empty_slot(slot))

    def _legacy_clear_channel_selections(self):
        if self.initial_mode == 'hic':
            for var in (self.hic_x_var, self.hic_y_var, self.hic_z_var):
                var.set(BLANK_DISPLAY_VALUE)
        elif self.initial_mode == 'nij':
            for var in (self.nij_fx_var, self.nij_fy_var, self.nij_fz_var, self.nij_mx_var, self.nij_my_var, self.nij_mz_var):
                var.set(BLANK_DISPLAY_VALUE)
        elif self.initial_mode == 'chest':
            for var in (self.chest_x_var, self.chest_y_var, self.chest_z_var, self.chest_disp_var):
                var.set(BLANK_DISPLAY_VALUE)
        else:
            for var in (self.femur_left_var, self.femur_right_var):
                var.set(BLANK_DISPLAY_VALUE)

    def _legacy_refresh_channel_lists(self, keep_existing=True):
        viewer = self.workbench.viewer
        try:
            self.detected_groups = self._detect_dummy_groups()
            self._sync_active_positions()
            placeholder_slot = self._is_placeholder_slot()
            channels = [] if placeholder_slot else self._candidate_channels_for_active_slot()
            self.current_available_channels = list(channels)
            display_values = [BLANK_DISPLAY_VALUE]
            mapping = {BLANK_DISPLAY_VALUE: ''}
            reverse = {'': BLANK_DISPLAY_VALUE}
            used = set()
            for ch in channels:
                display = self._display_name(viewer, ch, used)
                used.add(display)
                display_values.append(display)
                mapping[display] = ch
                reverse[ch] = display
            self._display_to_channel = mapping
            self._channel_to_display = reverse
            combos = []
            if self.initial_mode == 'hic':
                combos = [self.hic_x_combo, self.hic_y_combo, self.hic_z_combo]
            elif self.initial_mode == 'nij':
                combos = [self.nij_fx_combo, self.nij_fy_combo, self.nij_fz_combo, self.nij_mx_combo, self.nij_my_combo, self.nij_mz_combo]
            elif self.initial_mode == 'chest':
                combos = [self.chest_x_combo, self.chest_y_combo, self.chest_z_combo, self.chest_disp_combo]
            else:
                combos = [self.femur_left_combo, self.femur_right_combo]
            for combo in combos:
                combo['values'] = display_values
            self._update_group_info_label()
            slot_channels = self._active_slot_state().get('channels') or {}
            has_existing = any(slot_channels.values())
            if placeholder_slot:
                self._clear_channel_selections()
                for key in slot_channels.keys():
                    slot_channels[key] = ''
            elif keep_existing and has_existing:
                self._apply_slot_channels_to_ui(slot_channels)
            else:
                self.apply_auto_guess_for_active_slot()
            self._refresh_neck_guidance_text()
        except Exception as exc:
            self.current_available_channels = []
            self._display_to_channel = {}
            self._channel_to_display = {}
            for combo in ([self.hic_x_combo, self.hic_y_combo, self.hic_z_combo] if self.initial_mode == 'hic' else [self.nij_fx_combo, self.nij_fy_combo, self.nij_fz_combo, self.nij_mx_combo, self.nij_my_combo, self.nij_mz_combo] if self.initial_mode == 'nij' else [self.chest_x_combo, self.chest_y_combo, self.chest_z_combo, self.chest_disp_combo] if self.initial_mode == 'chest' else [self.femur_left_combo, self.femur_right_combo]):
                combo['values'] = []
            self._clear_channel_selections()

    def _score_text(self, text, keywords):
        text = text.lower().replace('_', ' ')
        return sum(3 if kw in text else 0 for kw in keywords)

    def _score_isocode_keywords(self, channel_name, keywords):
        parsed = self._parsed_channel_info(channel_name)
        if not parsed:
            return 0

        alias_groups = {
            'acc': ('acc', 'acceler', 'acceleration', 'ac'),
            'force': ('force', 'fo', 'load', 'axial'),
            'moment': ('moment', 'mo', 'bend'),
            'disp': ('disp', 'defl', 'deflection', 'distance', 'ds', 'displacement'),
            'x': ('x',),
            'y': ('y',),
            'z': ('z',),
            'fx': ('force', 'fo', 'x'),
            'fy': ('force', 'fo', 'y'),
            'fz': ('force', 'fo', 'z'),
            'mx': ('moment', 'mo', 'x'),
            'my': ('moment', 'mo', 'y'),
            'mz': ('moment', 'mo', 'z'),
            'thor': ('chest',),
            'stern': ('chest',),
            'hip': ('pelvis',),
            'slider': ('knee',),
            'clevis': ('clevis',),
            'inner': ('inner',),
            'outer': ('outer',),
            'left': ('left',),
            'right': ('right',),
            'upper': ('upper',),
            'lower': ('lower',),
        }

        tokens = set(str(token).strip().lower() for token in (parsed.get('tokens') or []) if str(token).strip())
        for value in (
            parsed.get('sensor_location'),
            parsed.get('data_type_label'),
            parsed.get('data_type_code'),
            parsed.get('axis_label'),
            parsed.get('axis_code'),
            parsed.get('side'),
            parsed.get('level'),
            parsed.get('position_detail'),
        ):
            text = str(value or '').strip().lower()
            if text:
                tokens.add(text)

        score = 0
        for keyword in keywords:
            normalized = str(keyword or '').strip().lower()
            if not normalized:
                continue
            aliases = alias_groups.get(normalized, (normalized,))
            if all(alias in tokens for alias in aliases):
                score += 24
            elif any(alias in tokens for alias in aliases):
                score += 12
        return score

    def _guess_from_candidates(self, keywords, exclude=(), preferred_filter_codes=()):
        viewer = self.workbench.viewer
        exclude = set(v for v in exclude if v)
        candidates = list(self.current_available_channels or self._candidate_channels_for_active_slot())

        # 1st pass: ISO code structure driven detection.
        best_iso = ''
        best_iso_score = -10**9
        for ch in candidates:
            if ch in exclude:
                continue
            score = self._score_isocode_keywords(ch, keywords) + self._filter_preference_score(ch, preferred_filter_codes)
            if score > best_iso_score:
                best_iso_score = score
                best_iso = ch
        if best_iso and best_iso_score > 0:
            return best_iso

        # 2nd pass: description / text fallback. When both fail, return blank.
        best_text = ''
        best_text_score = -10**9
        for ch in candidates:
            if ch in exclude:
                continue
            text = f"{ch} {viewer.get_channel_display_name(ch)} {viewer.get_y_axis_label(ch)}"
            score = self._score_text(text, keywords) + self._filter_preference_score(ch, preferred_filter_codes)
            if score > best_text_score:
                best_text_score = score
                best_text = ch
        return best_text if best_text_score > 0 else ''

    def _score_head_channel(self, channel_name, role='x'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f"{channel_name} {desc} {unit}"
        low = text.lower().replace('_', ' ')
        score = 0
        score += self._parsed_match_score(
            channel_name,
            sensor_location='head',
            data_type_code='AC',
            axis_code=role.upper(),
            preferred_filter_codes=self._preferred_filter_codes('hic', role),
        )
        score += self._score_isocode_keywords(channel_name, ['head', 'acc', role])
        if any(tag in low for tag in ('head', 'cg', 'head cg', 'head cg acc')):
            score += 12
        if any(tag in low for tag in ('acc', 'acceler')):
            score += 10
        axis_tokens = {
            'x': (' x ', ' ax', 'acx', 'acc x', 'accx', '_x', ' xa'),
            'y': (' y ', ' ay', 'acy', 'acc y', 'accy', '_y', ' ya'),
            'z': (' z ', ' az', 'acz', 'acc z', 'accz', '_z', ' za'),
        }
        if any(token in f" {low} " for token in axis_tokens[role]):
            score += 12
        for other_role, tokens in axis_tokens.items():
            if other_role == role:
                continue
            if any(token in f" {low} " for token in tokens):
                score -= 8
        unit_norm = unit.strip().lower().replace(' ', '')
        if unit_norm in ('g', 'm/s²', 'm/s^2', 'm/s2', 'ms-2', 'mps2'):
            score += 3
        return score

    def _auto_pick_head_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {'x': '', 'y': '', 'z': ''}
        selected = {}
        used = set()
        for role in ('x', 'y', 'z'):
            best, best_score = self._best_channel_by_score(channels, lambda ch, r=role: self._score_head_channel(ch, r), used)
            if best and best_score > 0:
                selected[role] = best
                used.add(best)
            else:
                selected[role] = self._guess_from_candidates(['head', 'acc', role], used, preferred_filter_codes=self._preferred_filter_codes('hic', role))
                if selected[role]:
                    used.add(selected[role])
        return selected

    def _score_neck_channel(self, channel_name, role='Fx'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f" {channel_name} {desc} {unit} ".lower().replace('_', ' ')
        normalized = str(role or '').strip().lower()
        component_type = 'force' if normalized.startswith('f') else 'moment'
        axis = normalized[-1] if normalized else ''
        score = 0
        score += self._parsed_match_score(
            channel_name,
            sensor_location='neck',
            data_type_code='FO' if component_type == 'force' else 'MO',
            axis_code=axis.upper(),
            preferred_filter_codes=self._preferred_filter_codes('nij', role),
        )
        score += self._score_isocode_keywords(channel_name, ['neck', component_type, axis])
        if 'neck' in text:
            score += 12
        if component_type == 'force' and any(tag in text for tag in ('force', 'load', 'axial', 'shear', ' fo ')):
            score += 12
        if component_type == 'moment' and any(tag in text for tag in ('moment', 'bending', ' mo ', 'mocy', 'moyf')):
            score += 12
        axis_tokens = {
            'x': (' x ', ' fx ', ' mx ', 'force x', 'moment x', 'fo x', 'mo x'),
            'y': (' y ', ' fy ', ' my ', 'force y', 'moment y', 'fo y', 'mo y', 'mocy', 'moyf'),
            'z': (' z ', ' fz ', ' mz ', 'force z', 'moment z', 'fo z', 'mo z'),
        }
        if axis and any(token in text for token in axis_tokens.get(axis, ())):
            score += 14
        for other_axis, tokens in axis_tokens.items():
            if other_axis == axis:
                continue
            if any(token in text for token in tokens):
                score -= 6
        unit_norm = unit.strip().lower().replace(' ', '')
        if component_type == 'force' and any(tag in unit_norm for tag in ('n', 'kn', 'lbf', 'lb')):
            score += 4
        if component_type == 'moment' and any(tag in unit_norm for tag in ('nm', 'n*m', 'lb*ft', 'lbf*ft', 'lb*in', 'lbf*in')):
            score += 4
        return score

    def _auto_pick_neck_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {'Fx': '', 'Fy': '', 'Fz': '', 'Mx': '', 'My': '', 'Mz': ''}
        selected = {}
        used = set()
        for role, fallback in (
            ('Fx', ['neck', 'force', 'fx']),
            ('Fy', ['neck', 'force', 'fy']),
            ('Fz', ['neck', 'force', 'fz', 'axial']),
            ('Mx', ['neck', 'moment', 'mx']),
            ('My', ['neck', 'moment', 'my', 'mocy', 'moyf']),
            ('Mz', ['neck', 'moment', 'mz']),
        ):
            best, best_score = self._best_channel_by_score(channels, lambda ch, r=role: self._score_neck_channel(ch, r), used)
            if best and best_score > 0:
                selected[role] = best
                used.add(best)
            else:
                selected[role] = self._guess_from_candidates(fallback, used, preferred_filter_codes=self._preferred_filter_codes('nij', role))
                if selected[role]:
                    used.add(selected[role])
        return selected

    def _score_chest_channel(self, channel_name, role='x'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f"{channel_name} {desc} {unit}"
        detected_role = detect_chest_channel_role(channel_name, desc, unit)
        score = 0
        if detected_role == role:
            score += 100
        elif detected_role is not None:
            score -= 50

        low = text.lower().replace('_', ' ')
        if any(tag in low for tag in ('chest', 'thor', 'stern', 'rib', 'chst')):
            score += 8

        if role in ('x', 'y', 'z'):
            score += self._parsed_match_score(
                channel_name,
                sensor_location='chest',
                data_type_code='AC',
                axis_code=role.upper(),
                preferred_filter_codes=self._preferred_filter_codes('chest', role),
            )
            score += self._score_isocode_keywords(channel_name, ['chest', 'acc', role])
            if any(tag in low for tag in ('acc', 'acceler')):
                score += 12
            axis_tokens = {
                'x': (' fx ', ' x ', ' ax', 'ax ', 'acc x', 'accx', '_x', ' xa', ' xacc'),
                'y': (' fy ', ' y ', ' ay', 'ay ', 'acc y', 'accy', '_y', ' ya', ' yacc'),
                'z': (' fz ', ' z ', ' az', 'az ', 'acc z', 'accz', '_z', ' za', ' zacc'),
            }
            wrong_axes = {'x', 'y', 'z'} - {role}
            for token in axis_tokens[role]:
                if token in f" {low} ":
                    score += 12
                    break
            for wrong in wrong_axes:
                for token in axis_tokens[wrong]:
                    if token in f" {low} ":
                        score -= 8
                        break
            u = unit.strip().lower().replace(' ', '')
            if u in ('g', 'm/s²', 'm/s^2', 'm/s2', 'ms-2', 'mps2'):
                score += 3
        else:
            score += self._parsed_match_score(
                channel_name,
                sensor_location='chest',
                data_type_code='DS',
                preferred_filter_codes=self._preferred_filter_codes('chest', role),
            )
            score += self._score_isocode_keywords(channel_name, ['chest', 'disp'])
            if any(tag in low for tag in ('disp', 'defl', 'deflection', ' ds', 'dsx', 'distance', 'compress')):
                score += 16
            if 'mm' in unit.lower():
                score += 6
        return score

    def _auto_pick_chest_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {'x': '', 'y': '', 'z': '', 'disp': ''}

        selected = {}
        used = set()
        for role in ('x', 'y', 'z', 'disp'):
            best = ''
            best_score = -10**9
            for ch in channels:
                if ch in used:
                    continue
                score = self._score_chest_channel(ch, role)
                if score > best_score:
                    best_score = score
                    best = ch
            if best and best_score > 0:
                selected[role] = best
                used.add(best)
            else:
                selected[role] = ''

        if not selected['x']:
            selected['x'] = self._guess_from_candidates(['chest', 'thor', 'stern', 'acc', 'x'], used)
            if selected['x']:
                used.add(selected['x'])
        if not selected['y']:
            selected['y'] = self._guess_from_candidates(['chest', 'thor', 'stern', 'acc', 'y'], used)
            if selected['y']:
                used.add(selected['y'])
        if not selected['z']:
            selected['z'] = self._guess_from_candidates(['chest', 'thor', 'stern', 'acc', 'z'], used)
            if selected['z']:
                used.add(selected['z'])
        if not selected['disp']:
            selected['disp'] = self._guess_from_candidates(['chest', 'thor', 'stern', 'disp', 'defl', 'ds'], used)

        return selected

    def _score_femur_channel(self, channel_name, role='left'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f"{channel_name} {desc} {unit}"
        detected_role = detect_femur_channel_role(channel_name, desc, unit)
        score = 0
        if detected_role == role:
            score += 100
        elif detected_role is not None:
            score -= 50
        score += self._parsed_match_score(
            channel_name,
            sensor_location='femur',
            data_type_code='FO',
            side=role,
            preferred_filter_codes=self._preferred_filter_codes('femur', role),
        )
        score += self._score_isocode_keywords(channel_name, ['femur', role, 'force'])
        low = text.lower().replace('_', ' ')
        if any(tag in low for tag in ('femur', 'thigh', 'upper leg', 'leg load')):
            score += 12
        if any(tag in low for tag in ('force', 'axial', 'load', 'fz')):
            score += 12
        if role == 'left' and any(tag in low for tag in (' left ', 'driver', ' lfem', 'l fem', ' feml')):
            score += 16
        if role == 'right' and any(tag in low for tag in (' right ', 'passenger', ' rfem', 'r fem', ' femr')):
            score += 16
        if 'n' in unit.lower():
            score += 4
        return score

    def _auto_pick_femur_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {'left': '', 'right': ''}
        selected = {}
        used = set()
        for role, fallback in (('left', ['femur', 'left', 'force']), ('right', ['femur', 'right', 'force'])):
            best = ''
            best_score = -10**9
            for ch in channels:
                if ch in used:
                    continue
                score = self._score_femur_channel(ch, role)
                if score > best_score:
                    best_score = score
                    best = ch
            if best and best_score > 0:
                selected[role] = best
                used.add(best)
            else:
                selected[role] = self._guess_from_candidates(fallback, used)
                if selected[role]:
                    used.add(selected[role])
        return selected

    def _channel_cfc_label_for_neck(self, channel_name):
        viewer = self.workbench.viewer
        if not channel_name:
            return 'RAW'
        label = viewer.get_current_filter_title_label(channel_name) if hasattr(viewer, 'get_current_filter_title_label') else ''
        if not label or str(label).strip().lower() == 'raw':
            label = (self.workbench.channel_filter_labels or {}).get(channel_name, '') or label
        return str(label or 'RAW').strip().upper()

    def _refresh_neck_guidance_text(self):
        if self.initial_mode != 'nij':
            return
        selected = {
            'Fx': self._selected_channel(self.nij_fx_var),
            'Fy': self._selected_channel(self.nij_fy_var),
            'Fz': self._selected_channel(self.nij_fz_var),
            'Mx': self._selected_channel(self.nij_mx_var),
            'My': self._selected_channel(self.nij_my_var),
            'Mz': self._selected_channel(self.nij_mz_var),
        }
        fxfyfz_grade = next((self._channel_cfc_label_for_neck(selected[k]) for k in ('Fx', 'Fy', 'Fz') if selected.get(k)), 'RAW')
        moment_grade = next((self._channel_cfc_label_for_neck(selected[k]) for k in ('Mx', 'My', 'Mz') if selected.get(k)), 'RAW')
        self.nij_guidance_var.set(f"활성 더미 {self._active_slot()} | Fx/Fy/Fz: [{fxfyfz_grade}] | Mx/My/Mz: [{moment_grade}]\nNij 계산은 Fz + My를 주로 사용하며, 축력 peak 확인은 Fz CFC1000을 병행합니다.")

    def _legacy_apply_auto_guess_for_active_slot(self):
        viewer = self.workbench.viewer
        if viewer.df is None:
            return
        slot = self._active_slot()
        if self._is_placeholder_slot(slot):
            self._clear_channel_selections()
            self.slot_states[slot]['channels'] = {k: '' for k in (self.slot_states[slot].get('channels') or ({'x': ''} if self.initial_mode == 'hic' else {'Fx': '', 'Fy': '', 'Fz': '', 'Mx': '', 'My': '', 'Mz': ''} if self.initial_mode == 'nij' else {'x': '', 'y': '', 'z': '', 'disp': ''} if self.initial_mode == 'chest' else {'left': '', 'right': ''}))}
            if hasattr(self.workbench, 'add_history_entry'):
                self._log_history('Channel auto-assignment skipped for empty dummy position', event_type='auto_assign', slot=slot, persist=True)
            return
        auto_pick = dict(auto_pick or self._compute_auto_pick_for_active_slot() or {})
        if self.initial_mode == 'hic':
            head_pick = auto_pick
            x = head_pick.get('x', '')
            y = head_pick.get('y', '')
            z = head_pick.get('z', '')
            self._set_var_from_channel(self.hic_x_var, x)
            self._set_var_from_channel(self.hic_y_var, y)
            self._set_var_from_channel(self.hic_z_var, z)
            self.slot_states[slot]['channels'] = {'x': x, 'y': y, 'z': z}
        elif self.initial_mode == 'nij':
            neck_pick = auto_pick
            fx = neck_pick.get('Fx', '')
            fy = neck_pick.get('Fy', '')
            fz = neck_pick.get('Fz', '')
            mx = neck_pick.get('Mx', '')
            my = neck_pick.get('My', '')
            mz = neck_pick.get('Mz', '')
            self._set_var_from_channel(self.nij_fx_var, fx)
            self._set_var_from_channel(self.nij_fy_var, fy)
            self._set_var_from_channel(self.nij_fz_var, fz)
            self._set_var_from_channel(self.nij_mx_var, mx)
            self._set_var_from_channel(self.nij_my_var, my)
            self._set_var_from_channel(self.nij_mz_var, mz)
            self.slot_states[slot]['channels'] = {'Fx': fx, 'Fy': fy, 'Fz': fz, 'Mx': mx, 'My': my, 'Mz': mz}
        elif self.initial_mode == 'chest':
            chest_pick = auto_pick
            x = chest_pick.get('x', '')
            y = chest_pick.get('y', '')
            z = chest_pick.get('z', '')
            d = chest_pick.get('disp', '')
            self._set_var_from_channel(self.chest_x_var, x)
            self._set_var_from_channel(self.chest_y_var, y)
            self._set_var_from_channel(self.chest_z_var, z)
            self._set_var_from_channel(self.chest_disp_var, d)
            self.slot_states[slot]['channels'] = {'x': x, 'y': y, 'z': z, 'disp': d}
        else:
            femur_pick = self._auto_pick_femur_channels()
            left = femur_pick.get('left', '')
            right = femur_pick.get('right', '')
            self._set_var_from_channel(self.femur_left_var, left)
            self._set_var_from_channel(self.femur_right_var, right)
            self.slot_states[slot]['channels'] = {'left': left, 'right': right}
        self._refresh_neck_guidance_text()
        assigned_count = sum(1 for _k, v in (self.slot_states[slot].get('channels') or {}).items() if v)
        self._log_history(f'Channel auto-assignment completed successfully ({assigned_count} channel(s))', event_type='auto_assign', slot=slot, persist=True)

    def _confirm_missing_dummy_profile(self, slot=None):
        slot = slot or self._active_slot()
        grouped = self.detected_groups.get(slot) or []
        profile = (self.slot_states.get(slot) or {}).get('dummy_profile') or self.multi_dummy_panel.profile_var(slot).get().strip()
        if grouped and not profile:
            return messagebox.askyesno('확인', f'{slot} 위치에 데이터는 있으나 더미 유형 설정이 없습니다. 계속 진행하시겠습니까?')
        return True

    def _calculate_all_slots(self, single_calc):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('경고', '먼저 DAT 데이터를 로드하세요.')
            return
        previous = self._active_slot()
        any_success = False
        for slot in self._active_positions():
            if not self._confirm_missing_dummy_profile(slot):
                continue
            self.active_dummy_var.set(slot)
            try:
                single_calc()
                any_success = True
            except Exception as exc:
                messagebox.showwarning('경고', f'{slot} 계산 중 오류가 발생했습니다.\n{exc}')
        self.active_dummy_var.set(previous if previous in self._active_positions() else self._first_active_position())
        self._update_combined_summary()
        if any_success:
            if hasattr(self.workbench, 'add_history_entry'):
                self._log_history(f'Calculation completed successfully for {len(self._active_positions())} active dummy position(s)', event_type='batch_calculation', slot=self._active_slot(), persist=True)

    def calculate_hic_bundle_all(self):
        self._calculate_all_slots(self.calculate_hic_bundle)

    def calculate_nij_all(self):
        self._calculate_all_slots(self.calculate_nij)

    def calculate_chest_all(self):
        self._calculate_all_slots(self.calculate_chest)

    def calculate_femur_all(self):
        self._calculate_all_slots(self.calculate_femur)


    def _unit_text(self, channel):
        viewer = self.workbench.viewer
        if not channel:
            return ''
        units = dict(getattr(viewer, 'units', {}) or {})
        unit = str(units.get(channel, '') or '').strip()
        if not unit or unit == '-':
            return ''
        return unit

    def _find_derived_channel(self, source_channel, purpose, role, cfc_value):
        metadata = dict((self.workbench.dataset_metadata or {}).get('derived_channels') or {})
        viewer_df = getattr(self.workbench.viewer, 'df', pd.DataFrame())
        return find_derived_channel(metadata, getattr(viewer_df, 'columns', []), source_channel, purpose, role, cfc_value)

    def _derived_source_channel(self, channel_name):
        channel_name = self._normalize_channel_reference(channel_name)
        if not channel_name:
            return ''
        metadata = dict((self.workbench.dataset_metadata or {}).get('derived_channels') or {})
        viewer_df = getattr(self.workbench.viewer, 'df', pd.DataFrame())
        columns = set(getattr(viewer_df, 'columns', []))
        reference_df = getattr(self.workbench, 'pre_filter_reference_df', None)
        reference_columns = set(getattr(reference_df, 'columns', [])) if reference_df is not None else set()
        current = str(channel_name)
        visited = set()
        while current and current not in visited:
            visited.add(current)
            info = dict(metadata.get(current) or {})
            source = str(info.get('source_channel') or '').strip()
            if not source:
                break
            # Composite sources like x|y|z are not physical raw channels.
            if "|" in source:
                break
            if source in columns or source in reference_columns:
                current = source
                continue
            break
        return current

    def _raw_root_channel_name(self, channel_name):
        channel_name = self._normalize_channel_reference(channel_name)
        if not channel_name:
            return ''
        reference_df = getattr(self.workbench, 'pre_filter_reference_df', None)
        reference_columns = set(getattr(reference_df, 'columns', [])) if reference_df is not None else set()
        meta = self._channel_metadata(channel_name)
        for candidate in (
            meta.get('root_source_channel'),
            self._derived_source_channel(channel_name),
            channel_name,
        ):
            candidate = str(candidate or '').strip()
            if candidate and candidate in reference_columns:
                return candidate
        raw_isocode = str(meta.get('raw_isocode') or '').strip().upper()
        if raw_isocode:
            rewritten = str(rewrite_filter_code_in_text(channel_name, 'Raw', raw_code=raw_isocode) or '').strip()
            if rewritten and rewritten in reference_columns:
                return rewritten
        return str(meta.get('root_source_channel') or self._derived_source_channel(channel_name) or channel_name or '').strip()

    def _collect_chest_disp_prefiltered(self, channel_name):
        viewer = self.workbench.viewer
        result = {}
        selected = self._normalize_channel_reference(channel_name)
        if not selected or getattr(viewer, 'df', None) is None:
            return result

        # If the currently selected channel already has a real CFC label, keep it.
        selected_label = self._channel_filter_label_for_calc(selected)
        selected_cfc = parse_cfc_filter_label(selected_label)
        try:
            if selected_cfc in (180, 600):
                result[int(selected_cfc)] = viewer.get_numeric_column(selected)
        except Exception:
            pass

        root_source = self._raw_root_channel_name(selected) or self._derived_source_channel(selected) or selected
        for cfc in (180, 600):
            derived = self._find_derived_channel(root_source, 'chest_injury', 'disp', cfc)
            if not derived:
                continue
            try:
                result[int(cfc)] = viewer.get_numeric_column(derived)
            except Exception:
                pass
        return result

    def _align_original_series(self, channel_name):
        viewer = self.workbench.viewer
        time = self._get_time()
        reference_df = getattr(self.workbench, 'pre_filter_reference_df', None)
        channel_name = self._raw_root_channel_name(channel_name) or self._normalize_channel_reference(channel_name)
        if time is None or reference_df is None or channel_name not in reference_df.columns:
            return None
        try:
            raw_values = pd.to_numeric(reference_df[channel_name], errors='coerce').to_numpy(dtype=float)
            if raw_values.shape == time.shape:
                return raw_values
            orig_time_col = (
                getattr(self.workbench, 'pre_filter_reference_time_column', None)
                or self.workbench.dataset_metadata.get('time_column')
                or viewer.time_column
            )
            if not orig_time_col or orig_time_col not in reference_df.columns:
                return None
            raw_time = pd.to_numeric(reference_df[orig_time_col], errors='coerce').to_numpy(dtype=float)
            if raw_time.shape != raw_values.shape or time.size == 0:
                return None
            aligned = np.full(time.shape, np.nan, dtype=float)
            valid = np.isfinite(raw_time) & np.isfinite(raw_values)
            if not np.any(valid):
                return None
            raw_time_v = raw_time[valid]
            raw_values_v = raw_values[valid]
            if raw_time_v.size < 2:
                return None
            order = np.argsort(raw_time_v)
            raw_time_v = raw_time_v[order]
            raw_values_v = raw_values_v[order]
            dt_candidates = np.diff(raw_time_v)
            dt_candidates = dt_candidates[np.isfinite(dt_candidates) & (dt_candidates > 0)]
            tol = float(np.median(dt_candidates) * 0.25) if dt_candidates.size else 1e-9
            idx = np.searchsorted(raw_time_v, time)
            left = np.clip(idx - 1, 0, raw_time_v.size - 1)
            right = np.clip(idx, 0, raw_time_v.size - 1)
            left_diff = np.abs(raw_time_v[left] - time)
            right_diff = np.abs(raw_time_v[right] - time)
            choose_right = right_diff < left_diff
            best = np.where(choose_right, right, left)
            best_diff = np.minimum(left_diff, right_diff)
            keep = best_diff <= tol
            aligned[keep] = raw_values_v[best[keep]]
            return aligned if np.any(np.isfinite(aligned)) else None
        except Exception:
            return None

    def _resolve_standard_series_for_calc(self, source_channel, purpose, role, desired_cfc=None, sign=1.0):
        viewer = self.workbench.viewer
        source_channel = self._normalize_channel_reference(source_channel)
        if not source_channel:
            return None, None
        sign = float(sign)
        selected_values = viewer.get_numeric_column(source_channel) * sign
        if desired_cfc is None:
            return selected_values, source_channel

        root_source = self._derived_source_channel(source_channel) or source_channel

        # Prefer a stored derived channel rebuilt from the traced physical source.
        derived = self._find_derived_channel(root_source, purpose, role, desired_cfc)
        if derived:
            return viewer.get_numeric_column(derived) * sign, derived

        # If the selected channel itself already matches the desired CFC, use it.
        selected_label = (self.workbench.channel_filter_labels or {}).get(source_channel)
        if parse_cfc_filter_label(selected_label) == int(desired_cfc):
            return selected_values, source_channel

        # If the traced source channel exists in the current dataset and already has the desired
        # CFC label, use that source channel directly.
        root_label = (self.workbench.channel_filter_labels or {}).get(root_source)
        if root_source in getattr(viewer, 'df', pd.DataFrame()).columns and parse_cfc_filter_label(root_label) == int(desired_cfc):
            return viewer.get_numeric_column(root_source) * sign, root_source

        raw_values = self._align_original_series(root_source)
        if raw_values is not None:
            time = self._get_time()
            filtered = np.asarray(apply_cfc_filter_to_series(time, raw_values, int(desired_cfc)), dtype=float) * sign
            return filtered, f"{root_source} [raw→CFC{int(desired_cfc)}]"
        return selected_values, source_channel

    def _get_xyz_resultant(self):
        x_ch = self._selected_channel(self.hic_x_var)
        y_ch = self._selected_channel(self.hic_y_var)
        z_ch = self._selected_channel(self.hic_z_var)
        if not (x_ch and y_ch and z_ch):
            raise ValueError('X/Y/Z 채널을 모두 선택하세요.')
        time = self._get_time()
        x, used_x = self._resolve_standard_series_for_calc(x_ch, 'head_injury', 'x', 1000, 1.0)
        y, used_y = self._resolve_standard_series_for_calc(y_ch, 'head_injury', 'y', 1000, 1.0)
        z, used_z = self._resolve_standard_series_for_calc(z_ch, 'head_injury', 'z', 1000, 1.0)
        resultant = compute_resultant_xyz(x, y, z)
        return time, resultant, (x_ch, y_ch, z_ch), (x, y, z), (used_x, used_y, used_z)

    def _convert_resultant_to_g(self, resultant, channels):
        unit_text = ' / '.join(self._unit_text(ch) for ch in channels)
        if 'm/s' in unit_text.lower() or 'ms-2' in unit_text.lower() or 'mps2' in unit_text.lower():
            return resultant / 9.80665
        return resultant

    def _convert_channel_to_head_plot_unit(self, values, channel):
        unit_text = (self._unit_text(channel) or '').lower()
        if 'm/s' in unit_text or 'ms-2' in unit_text or 'mps2' in unit_text:
            return np.asarray(values, dtype=float) / 9.80665
        return np.asarray(values, dtype=float)

    def _head_plot_unit(self, channels):
        return 'g'

    def _head_resultant_channel_name(self, slot):
        return f"{slot}_HEAD_RESULTANT_CFC1000"

    def _head_axis_display_names(self, channels):
        labels = {}
        for axis_key, channel_name in zip(('x', 'y', 'z'), channels):
            rewritten = str(rewrite_filter_code_in_text(channel_name, 'CFC 1000') or channel_name or '-').strip()
            labels[axis_key] = f"ACC {axis_key.upper()} - {rewritten}"
        return labels

    def _head_resultant_channel_metadata(self, slot, channels):
        x_ch, y_ch, z_ch = channels
        return {
            'description': f'{slot} Head Resultant Acceleration - CFC1000',
            'unit': self._head_plot_unit(channels),
            'filter_label': 'CFC 1000',
            'display_filter_label': 'CFC 1000',
            'required_cfc': 'CFC 1000',
            'calculation_label': 'CALC',
            'purpose': 'head_injury',
            'role': 'resultant',
            'source_channel': f'{x_ch}|{y_ch}|{z_ch}',
        }

    def _chest_vc_channel_name(self, slot, directive):
        tag = 'SAE_J1727' if str(directive).upper().startswith('SAE') else 'ECE94'
        return f"{slot}_CHEST_VC_{tag}"

    def _chest_vc_channel_metadata(self, slot, source_channel, directive):
        is_sae = str(directive).upper().startswith('SAE')
        tag = 'SAE J1727' if is_sae else 'ECE94'
        role = 'vc_sae' if is_sae else 'vc_ece'
        required_cfc = 'CFC 600' if is_sae else 'CFC 180'
        return {
            'description': f'{slot} Chest V*C {tag}',
            'unit': 'm/s',
            'filter_label': 'CALC',
            'display_filter_label': required_cfc,
            'calculation_label': 'CALC',
            'required_cfc': required_cfc,
            'purpose': 'chest_injury',
            'role': role,
            'source_channel': str(source_channel or ''),
        }

    def _merge_metadata_dicts(self, *dicts):
        merged = {}
        for d in dicts:
            if d:
                merged.update(dict(d))
        return merged

    def _femur_force_channel_name(self, slot, side):
        return f"{slot}_FEMUR_{str(side).upper()}_FORCE_CFC600"

    def _femur_force_channel_metadata(self, slot, source_channel, side):
        side_text = str(side).upper()
        return {
            'description': f'{slot} Femur {side_text} Axial Force - CFC600',
            'unit': 'N',
            'filter_label': 'CFC 600',
            'display_filter_label': 'CFC 600',
            'required_cfc': 'CFC 600',
            'purpose': 'femur_injury',
            'role': str(side).lower(),
            'source_channel': str(source_channel or ''),
        }

    def _current_use_high_res_cumulative_3ms(self):
        return bool(self.use_high_res_cumulative_3ms_var.get())

    def _slot_use_high_res_cumulative_3ms(self, slot=None):
        slot = slot or self._active_slot()
        state = dict(self.slot_states.get(slot) or {})
        if 'use_high_res_cumulative_3ms' in state:
            return bool(state.get('use_high_res_cumulative_3ms'))
        if 'high_res_3ms_sliding_window' in state:
            return bool(state.get('high_res_3ms_sliding_window'))
        for payload_key in ('head_metadata', 'chest_saved_payload', 'pelvis_saved_payload'):
            payload = dict(state.get(payload_key) or {})
            if 'use_high_res_cumulative_3ms' in payload:
                return bool(payload.get('use_high_res_cumulative_3ms'))
            if 'high_res_3ms_sliding_window' in payload:
                return bool(payload.get('high_res_3ms_sliding_window'))
        return self._current_use_high_res_cumulative_3ms()


    def calculate_hic_bundle(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('경고', '먼저 DAT 데이터를 로드하세요.')
            return
        if not self._confirm_missing_dummy_profile():
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        try:
            time, resultant, channels, resolved_axes, used_channels = self._get_xyz_resultant()
            resultant_channel = self._head_resultant_channel_name(slot)
            result = build_head_injury_bundle(
                time=time,
                resultant_g=self._convert_resultant_to_g(resultant, channels),
                x_plot=self._convert_channel_to_head_plot_unit(resolved_axes[0], channels[0]),
                y_plot=self._convert_channel_to_head_plot_unit(resolved_axes[1], channels[1]),
                z_plot=self._convert_channel_to_head_plot_unit(resolved_axes[2], channels[2]),
                plot_unit=self._head_plot_unit(channels),
                channels=channels,
                axis_display_names=self._head_axis_display_names(channels),
                resultant_channel=resultant_channel,
                resultant_filter_label='CFC 1000',
                use_high_res_cumulative_3ms=self._current_use_high_res_cumulative_3ms(),
            )
            st = self.slot_states[slot]
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
            st['channels'] = {'x': channels[0], 'y': channels[1], 'z': channels[2]}
            st['summary_text'] = result['summary_text']
            st['head_bundle'] = result['bundle']
            meta = dict(result['metadata'] or {})
            meta['dummy_name'] = st['dummy_name']
            meta['dummy_profile'] = st['dummy_profile']
            meta['channels'] = dict(st['channels'])
            meta['use_high_res_cumulative_3ms'] = self._current_use_high_res_cumulative_3ms()
            st['head_metadata'] = meta
            preferred_graph_key = self._default_graph_key('head_resultant')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['head_metadata']['graph_key'] = st['graph_key']
            st['head_metadata']['graph_uid'] = st['graph_uid']
            st['use_high_res_cumulative_3ms'] = self._current_use_high_res_cumulative_3ms()
            self._apply_summary_text(result['summary_text'])
            injury_df = viewer.df.copy(deep=True)
            injury_df[resultant_channel] = np.asarray(result['bundle']['resultant_g'], dtype=float)
            metadata_override = {
                'units': self._merge_metadata_dicts(getattr(viewer, 'external_units', {}) or {}, {resultant_channel: result['bundle'].get('plot_unit', 'g')}),
                'descriptions': self._merge_metadata_dicts(getattr(viewer, 'external_descriptions', {}) or {}, {resultant_channel: f'{slot} Head Resultant Acceleration'}),
                'channel_filter_labels': self._merge_metadata_dicts(self.workbench.channel_filter_labels or {}, {resultant_channel: 'CFC 1000'}),
                'derived_channels': dict((self.workbench.dataset_metadata or {}).get('derived_channels') or {}),
            }
            metadata_override['derived_channels'][resultant_channel] = self._head_resultant_channel_metadata(slot, channels)
            self._save_section_payload({
                'type': 'injury_calculation',
                'section': 'HEAD',
                'slot': slot,
                'dummy_position': slot,
                'result_uid': st.get('result_uid') or self._injury_result_uid(slot),
                'graph_uid': st.get('graph_uid'),
                'message': 'Head injury calculated',
            }, dataframe=injury_df, metadata_extra=metadata_override)
            self.show_hic_bundle_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('경고', str(exc))

    def show_hic_bundle_graph(self, metric_key, slot=None, silent=False):
        slot = slot or self._active_slot()
        bundle = (self.slot_states.get(slot) or {}).get('head_bundle')
        if not bundle:
            if not silent:
                messagebox.showwarning('경고', '먼저 HEAD 계산을 실행하세요.')
            return
        metric_key = self._normalize_head_graph_key(metric_key)
        if metric_key == 'head_xyz':
            self._plot_head_xyz(bundle, slot)
        else:
            self._plot_head_resultant(bundle, slot)
        self.slot_states[slot]['graph_key'] = metric_key
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, metric_key)
        self._select_graph_tab(metric_key)
        if not silent:
            self._record_graph_selection(slot, metric_key)

    def _normalize_head_graph_key(self, graph_key):
        key = str(graph_key or '').strip().lower()
        if key in {'head_xyz', 'xyz'}:
            return 'head_xyz'
        if key in {'head_resultant', 'resultant', 'hic15', 'hic36', 'clip3'}:
            return 'head_resultant'
        return 'head_resultant'

    def _plot_head_curves(self, bundle, include_resultant=False):
        self.ax.clear()
        t = np.asarray(bundle.get('time', []), dtype=float)
        curves = [
            ('HEAD X', np.asarray(bundle.get('x_plot', []), dtype=float), 1.0),
            ('HEAD Y', np.asarray(bundle.get('y_plot', []), dtype=float), 1.0),
            ('HEAD Z', np.asarray(bundle.get('z_plot', []), dtype=float), 1.0),
        ]
        if include_resultant:
            curves.append(('HEAD Resultant', np.asarray(bundle.get('resultant_g', []), dtype=float), 1.6))
        for label, values, width in curves:
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, values)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)

    def _plot_head_xyz(self, bundle, slot):
        self._plot_head_curves(bundle, include_resultant=True)
        self.ax.set_title(self._head_graph_title(slot, 'head_xyz'))
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Acceleration ({bundle.get('plot_unit', 'g')})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Head_XYZ_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_head_resultant(self, bundle, slot):
        self.ax.clear()
        t = np.asarray(bundle.get('time', []), dtype=float)
        resultant = np.asarray(bundle.get('resultant_g', []), dtype=float)
        valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, resultant)
        if np.any(valid):
            self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.6, label='HEAD Resultant')
        for hic_key, color, label in (
            ('hic15', '#fca5a5', 'HIC15 구간'),
            ('hic36', '#87ceeb', 'HIC36 구간'),
        ):
            info = bundle.get(hic_key)
            if not info:
                continue
            self.ax.axvspan(
                info['start_time'] * 1000.0,
                info['end_time'] * 1000.0,
                alpha=0.22,
                color=color,
                label=label,
            )
        clip_value = bundle.get('clip3')
        if clip_value is not None:
            self.ax.axhline(
                clip_value,
                linestyle='--',
                linewidth=1.0,
                color='#7c3aed',
                label=f'One Peak 3ms_Clip = {fmt_value(clip_value, bundle.get("plot_unit", "g"), decimals=4)}',
            )
        self.ax.set_title(self._head_graph_title(slot, 'head_resultant'))
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Acceleration ({bundle.get('plot_unit', 'g')})")
        self.ax.set_xlim(0.0, 150.0)
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Head_Resultant_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def calculate_nij(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('경고', '먼저 DAT 데이터를 로드하세요.')
            return
        if not self._confirm_missing_dummy_profile():
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        selected = {
            'Fx': self._selected_channel(self.nij_fx_var),
            'Fy': self._selected_channel(self.nij_fy_var),
            'Fz': self._selected_channel(self.nij_fz_var),
            'Mx': self._selected_channel(self.nij_mx_var),
            'My': self._selected_channel(self.nij_my_var),
            'Mz': self._selected_channel(self.nij_mz_var),
        }
        if not selected['Fz'] or not selected['My']:
            messagebox.showwarning('경고', 'NECK 계산에는 Fz와 My 채널이 필요합니다.')
            return
        sign_flags = {
            'Fx': -1.0 if self.nij_fx_neg_var.get() else 1.0,
            'Fy': -1.0 if self.nij_fy_neg_var.get() else 1.0,
            'Fz': -1.0 if self.nij_fz_neg_var.get() else 1.0,
            'Mx': -1.0 if self.nij_mx_neg_var.get() else 1.0,
            'My': -1.0 if self.nij_my_neg_var.get() else 1.0,
            'Mz': -1.0 if self.nij_mz_neg_var.get() else 1.0,
        }
        try:
            result = calculate_neck_injury_bundle(
                time=self._get_time(),
                selected=selected,
                sign_flags=sign_flags,
                viewer=viewer,
                criterion_key=self.nij_dummy_var.get(),
                dummy_profile_label=self.multi_dummy_panel.profile_var(slot).get().strip(),
                unit_getter=self._unit_text,
                channel_desc_getter=lambda ch: viewer.get_channel_display_name(ch) if ch else '-',
                resolve_series_for_calc=lambda source_channel, role, desired_cfc, sign: self._resolve_standard_series_for_calc(source_channel, 'neck_injury', role, desired_cfc, sign),
            )
            metrics = result['metrics']
            st = self.slot_states[slot]
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
            st['channels'] = dict(selected)
            st['neg_flags'] = {}
            st['summary_text'] = result['summary_text']
            st['result_uid'] = st.get('result_uid') or self._injury_result_uid(slot)
            st['neck_metrics'] = metrics
            st['neck_saved_payload'] = {
                'result_uid': st['result_uid'],
                'summary_text': result['summary_text'],
                'criterion_key': self.nij_dummy_var.get(),
                'overall_nij': float(metrics['overall_nij']) if metrics.get('overall_nij') is not None else None,
                'dominant_mode': metrics.get('dominant_mode'),
                'dummy_name': st['dummy_name'],
                'dummy_profile': st['dummy_profile'],
                'channels': dict(selected),
                'neg_flags': dict(st['neg_flags']),
                'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
            }
            preferred_graph_key = self._default_graph_key('nij_components')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['neck_saved_payload']['graph_key'] = st['graph_key']
            st['neck_saved_payload']['graph_uid'] = st['graph_uid']
            self._apply_summary_text(result['summary_text'])
            injury_df = viewer.df.copy(deep=True)
            calc_channels = build_neck_injury_channels(metrics)
            calc_meta = build_neck_injury_channel_metadata(metrics)
            calc_desc = dict((calc_meta or {}).get('descriptions') or {})
            calc_units = dict((calc_meta or {}).get('units') or {})
            calc_filters = dict((calc_meta or {}).get('channel_filter_labels') or {})
            prefix = f'{slot}_'
            renamed_meta = {}
            added_units = {}
            added_descriptions = {}
            added_filter_labels = {}
            source_map = {
                'NECKUP_FZ_CFC1000': selected.get('Fz') or '',
                'NECKUP_FZ_CFC600': selected.get('Fz') or '',
                'NECKUP_FX_CFC600': selected.get('Fx') or '',
                'NECKUP_MY_CFC600': selected.get('My') or '',
                'NECKUP_MOCY': f"{selected.get('My') or ''}|{selected.get('Fx') or ''}",
                'NECKUP_NIJ_TE': f"{selected.get('Fz') or ''}|{selected.get('My') or ''}",
                'NECKUP_NIJ_TF': f"{selected.get('Fz') or ''}|{selected.get('My') or ''}",
                'NECKUP_NIJ_CE': f"{selected.get('Fz') or ''}|{selected.get('My') or ''}",
                'NECKUP_NIJ_CF': f"{selected.get('Fz') or ''}|{selected.get('My') or ''}",
                'NECKUP_NIJ': f"{selected.get('Fz') or ''}|{selected.get('My') or ''}",
            }
            calc_channel_names = {'NECKUP_MOCY', 'NECKUP_NIJ_TE', 'NECKUP_NIJ_TF', 'NECKUP_NIJ_CE', 'NECKUP_NIJ_CF', 'NECKUP_NIJ'}
            role_map = {
                'NECKUP_FZ_CFC1000': 'fz_peak',
                'NECKUP_FZ_CFC600': 'fz_nij',
                'NECKUP_FX_CFC600': 'fx_nij',
                'NECKUP_MY_CFC600': 'my_nij',
                'NECKUP_MOCY': 'mocy',
                'NECKUP_NIJ_TE': 'nte',
                'NECKUP_NIJ_TF': 'ntf',
                'NECKUP_NIJ_CE': 'nce',
                'NECKUP_NIJ_CF': 'ncf',
                'NECKUP_NIJ': 'nij',
            }
            for ch_name, ch_values in calc_channels.items():
                new_name = prefix + ch_name
                injury_df[new_name] = np.asarray(ch_values, dtype=float)
                desc = str(calc_desc.get(ch_name) or ch_name).strip()
                unit = str(calc_units.get(ch_name) or '').strip()
                filter_label = str(calc_filters.get(ch_name) or 'Raw').strip() or 'Raw'
                is_calc_channel = ch_name in calc_channel_names
                normalized_filter_label = filter_label if filter_label not in ('', '-') else 'Raw'
                derived_meta = {
                    'description': desc,
                    'unit': unit,
                    'filter_label': normalized_filter_label,
                    'purpose': 'neck_injury',
                    'role': role_map.get(ch_name, ''),
                    'source_channel': source_map.get(ch_name, ''),
                }
                if is_calc_channel:
                    calc_filter_label = normalized_filter_label
                    if calc_filter_label == 'Raw':
                        calc_filter_label = 'CFC 600'
                    derived_meta['filter_label'] = calc_filter_label
                    derived_meta['calculation_label'] = 'CALC'
                    derived_meta['display_filter_label'] = calc_filter_label
                    derived_meta['required_cfc'] = calc_filter_label
                    filter_label = calc_filter_label
                renamed_meta[new_name] = derived_meta
                added_units[new_name] = unit
                added_descriptions[new_name] = desc
                added_filter_labels[new_name] = filter_label
            metadata_override = {
                'units': self._merge_metadata_dicts(getattr(viewer, 'external_units', {}) or {}, added_units),
                'descriptions': self._merge_metadata_dicts(getattr(viewer, 'external_descriptions', {}) or {}, added_descriptions),
                'channel_filter_labels': self._merge_metadata_dicts(self.workbench.channel_filter_labels or {}, added_filter_labels),
                'neck_injury_metrics': {slot: st['neck_saved_payload']},
                'derived_channels': dict((self.workbench.dataset_metadata or {}).get('derived_channels') or {}),
            }
            metadata_override['derived_channels'].update(renamed_meta)
            self._save_section_payload(
                {
                    'type': 'injury_calculation',
                    'section': 'NECK',
                    'slot': slot,
                    'dummy_position': slot,
                    'result_uid': st['result_uid'],
                    'graph_uid': st.get('graph_uid'),
                    'message': 'Neck injury calculated',
                    'display_message': 'Neck injury calculated successfully',
                },
                dataframe=injury_df,
                metadata_extra=metadata_override,
            )
            self.show_neck_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('경고', str(exc))

    def show_neck_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('neck_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('경고', '먼저 NECK 계산을 실행하세요.')
            return
        mode = self._normalize_neck_graph_key(mode)
        if mode == 'fo':
            self._plot_neck_force_overlay(metrics, slot)
        elif mode == 'mo':
            self._plot_neck_moment_overlay(metrics, slot)
        elif mode == 'mocy':
            self._plot_neck_mocy(metrics, slot)
        elif mode == 'nij_overall':
            self._plot_neck_nij_overall(metrics, slot)
        else:
            self._plot_neck_nij(metrics, slot)
        self.slot_states[slot]['graph_key'] = mode
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, mode)
        self._select_graph_tab(mode)
        if not silent:
            self._record_graph_selection(slot, mode)

    def _normalize_neck_graph_key(self, graph_key):
        key = str(graph_key or '').strip().lower()
        return {
            'fz': 'fo',
            'my': 'mo',
            'nij': 'nij_components',
            'nij_components': 'nij_components',
            'nij_overall': 'nij_overall',
            'upper_neck_index_nij': 'nij_components',
        }.get(key, key or 'nij_components')

    def _plot_neck_force_overlay(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        display_series = dict(metrics.get('display_series') or {})
        display_units = dict(metrics.get('display_units') or {})
        for label in ('Fx', 'Fy', 'Fz'):
            arr = display_series.get(label)
            if arr is None:
                continue
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, np.asarray(arr, dtype=float))
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.2, label=label)
        force_unit = next((display_units.get(label) for label in ('Fx', 'Fy', 'Fz') if display_units.get(label)), 'N')
        self.ax.set_title(f"INJURY - NECK FO ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Force ({force_unit})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Neck_FO_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_neck_moment_overlay(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        display_series = dict(metrics.get('display_series') or {})
        display_units = dict(metrics.get('display_units') or {})
        for label in ('Mx', 'My', 'Mz'):
            arr = display_series.get(label)
            if arr is None:
                continue
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, np.asarray(arr, dtype=float))
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.2, label=label)
        moment_unit = next((display_units.get(label) for label in ('Mx', 'My', 'Mz') if display_units.get(label)), 'Nm')
        self.ax.set_title(f"INJURY - NECK MO ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Moment ({moment_unit})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Neck_MO_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_neck_mocy(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        y = np.asarray(metrics.get('my_filtered', metrics.get('my_raw_filtered', metrics.get('my', []))), dtype=float)
        self.ax.clear()
        valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, y)
        if np.any(valid):
            self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.4, label='MOCy')
        self.ax.set_title(f"INJURY - NECK MOCy ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Moment ({metrics.get('my_unit', 'Nm')})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Neck_MOCy_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_neck_nij(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        for label, key, width in (
            ('NTE', 'nte', 1.0),
            ('NTF', 'ntf', 1.0),
            ('NCE', 'nce', 1.0),
            ('NCF', 'ncf', 1.0),
        ):
            case_arr = np.asarray(metrics.get(key), dtype=float)
            case_valid, case_t_plot, case_v_plot = self._time_value_valid_mask_ms(t, case_arr)
            if np.any(case_valid):
                self.ax.plot(case_t_plot[case_valid], case_v_plot[case_valid], linewidth=width, label=label)
        self.ax.set_title(f"INJURY - Nij Components ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Nij')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Neck_Nij_Components_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_neck_nij_overall(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        arr = np.asarray(metrics.get('nij'), dtype=float)
        valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
        if np.any(valid):
            self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.8, label='Overall Nij')
        self.ax.set_title(f"INJURY - Nij Overall ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Nij')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Neck_Nij_Overall_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def calculate_chest(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('경고', '먼저 DAT 데이터를 로드하세요.')
            return
        if not self._confirm_missing_dummy_profile():
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        try:
            time = self._get_time()
            x_ch = self._selected_channel(self.chest_x_var)
            y_ch = self._selected_channel(self.chest_y_var)
            z_ch = self._selected_channel(self.chest_z_var)
            disp_ch = self._selected_channel(self.chest_disp_var)
            if not all((x_ch, y_ch, z_ch, disp_ch)):
                raise ValueError('CHEST 계산에는 X/Y/Z 가속도와 변위 채널이 모두 필요합니다.')
            raw_disp_series = self._align_original_series(disp_ch)
            if raw_disp_series is not None:
                raw_disp_series = np.asarray(raw_disp_series, dtype=float)
            raw_accel_series = {
                'x': self._align_original_series(x_ch),
                'y': self._align_original_series(y_ch),
                'z': self._align_original_series(z_ch),
            }
            raw_accel_series = {k: (None if v is None else np.asarray(v, dtype=float)) for k, v in raw_accel_series.items()}
            disp_prefiltered = {k: np.asarray(v, dtype=float) for k, v in dict(self._collect_chest_disp_prefiltered(disp_ch) or {}).items()}
            x_calc, used_x = self._resolve_standard_series_for_calc(x_ch, 'chest_injury', 'x', 180, 1.0)
            y_calc, used_y = self._resolve_standard_series_for_calc(y_ch, 'chest_injury', 'y', 180, 1.0)
            z_calc, used_z = self._resolve_standard_series_for_calc(z_ch, 'chest_injury', 'z', 180, 1.0)
            x_calc = np.asarray(x_calc, dtype=float)
            y_calc = np.asarray(y_calc, dtype=float)
            z_calc = np.asarray(z_calc, dtype=float)
            disp_calc = np.asarray(viewer.get_numeric_column(disp_ch), dtype=float)
            result = calculate_chest_injury_bundle(
                time=time,
                x_values=x_calc,
                y_values=y_calc,
                z_values=z_calc,
                disp_values=disp_calc,
                accel_units={'x': self._unit_text(x_ch), 'y': self._unit_text(y_ch), 'z': self._unit_text(z_ch)},
                disp_unit=self._unit_text(disp_ch),
                criterion_key=self.chest_dummy_var.get(),
                raw_displacement=raw_disp_series,
                raw_accel=raw_accel_series,
                accel_filter_labels={
                    'x': self._channel_filter_label_for_calc(x_ch, used_x),
                    'y': self._channel_filter_label_for_calc(y_ch, used_y),
                    'z': self._channel_filter_label_for_calc(z_ch, used_z),
                },
                disp_filter_label=self._channel_filter_label_for_calc(disp_ch),
                disp_prefiltered=disp_prefiltered,
                vc_sign_pref=1.0,
                use_high_res_cumulative_3ms=self._current_use_high_res_cumulative_3ms(),
            )
            metrics = result['metrics']
            st = self.slot_states[slot]
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
            st['channels'] = {'x': x_ch, 'y': y_ch, 'z': z_ch, 'disp': disp_ch}
            st['summary_text'] = result['summary_text']
            st['result_uid'] = st.get('result_uid') or self._injury_result_uid(slot)
            st['neg_flags'] = {}
            st['chest_metrics'] = metrics
            st['use_high_res_cumulative_3ms'] = self._current_use_high_res_cumulative_3ms()
            rp = metrics.get('resultant_peak', {})
            st['chest_saved_payload'] = {
                'result_uid': st['result_uid'],
                'summary_text': result['summary_text'],
                'criterion_key': self.chest_dummy_var.get(),
                'dummy_name': st['dummy_name'],
                'dummy_profile': st['dummy_profile'],
                'channels': dict(st['channels']),
                'neg_flags': dict(st['neg_flags']),
                'use_high_res_cumulative_3ms': st['use_high_res_cumulative_3ms'],
                'resultant_peak_g': float(rp['value']) if rp.get('value') is not None else None,
                'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
            }
            preferred_graph_key = self._default_graph_key('accel')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['chest_saved_payload']['graph_key'] = st['graph_key']
            st['chest_saved_payload']['graph_uid'] = st['graph_uid']
            self._apply_summary_text(result['summary_text'])
            vc_sae_channel = self._chest_vc_channel_name(slot, 'SAE_J1727')
            vc_ece_channel = self._chest_vc_channel_name(slot, 'ECE94')
            st['vc_channels'] = {'sae': vc_sae_channel, 'ece': vc_ece_channel}
            injury_df = viewer.df.copy(deep=True)
            injury_df[vc_sae_channel] = np.asarray(metrics.get('vc_sae', []), dtype=float)
            injury_df[vc_ece_channel] = np.asarray(metrics.get('vc_ece', []), dtype=float)
            metadata_override = {
                'units': self._merge_metadata_dicts(getattr(viewer, 'external_units', {}) or {}, {vc_sae_channel: 'm/s', vc_ece_channel: 'm/s'}),
                'descriptions': self._merge_metadata_dicts(getattr(viewer, 'external_descriptions', {}) or {}, {vc_sae_channel: f'{slot} Chest V*C SAE J1727', vc_ece_channel: f'{slot} Chest V*C ECE94'}),
                'channel_filter_labels': self._merge_metadata_dicts(self.workbench.channel_filter_labels or {}, {vc_sae_channel: 'CALC', vc_ece_channel: 'CALC'}),
                'derived_channels': dict((self.workbench.dataset_metadata or {}).get('derived_channels') or {}),
            }
            metadata_override['derived_channels'][vc_sae_channel] = self._chest_vc_channel_metadata(slot, disp_ch, 'SAE_J1727')
            metadata_override['derived_channels'][vc_ece_channel] = self._chest_vc_channel_metadata(slot, disp_ch, 'ECE94')
            self._save_section_payload(
                {
                    'type': 'injury_calculation',
                    'section': 'CHEST',
                    'slot': slot,
                    'dummy_position': slot,
                    'result_uid': st['result_uid'],
                    'graph_uid': st.get('graph_uid'),
                    'message': 'Chest injury calculated',
                    'display_message': 'Chest injury calculated successfully',
                },
                dataframe=injury_df,
                metadata_extra=metadata_override,
            )
            self.show_chest_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('경고', str(exc))

    def show_chest_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('chest_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('경고', '먼저 CHEST 계산을 실행하세요.')
            return
        if mode == 'accel':
            self._plot_chest_accel(metrics, slot)
        elif mode == 'disp':
            self._plot_chest_disp(metrics, slot)
        else:
            self._plot_chest_vc(metrics, slot)
        self.slot_states[slot]['graph_key'] = mode
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, mode)
        self._select_graph_tab(mode)
        if not silent:
            self._record_graph_selection(slot, mode)

    def _plot_chest_accel(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        for label, arr, width in (
            ('CHEST X', metrics['x_g'], 1.0),
            ('CHEST Y', metrics['y_g'], 1.0),
            ('CHEST Z', metrics['z_g'], 1.0),
            ('CHEST RES', metrics['resultant_g'], 1.6),
        ):
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)
        self.ax.set_title(f"INJURY - CHEST ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Acceleration (g)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Chest_Acceleration_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_chest_disp(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        disp = np.asarray(metrics['displacement_mm'], dtype=float)
        self.ax.clear()
        valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, disp)
        if np.any(valid):
            self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.2, label='Chest Displacement')
        self.ax.set_title(f"INJURY - CHEST ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Displacement (mm)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Chest_Displacement_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_chest_vc(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        viewer = self.workbench.viewer
        vc_channels = dict((self.slot_states.get(slot) or {}).get('vc_channels') or {})
        series_to_plot = []
        sae_ch = vc_channels.get('sae')
        ece_ch = vc_channels.get('ece')
        if sae_ch and getattr(viewer, 'df', None) is not None and sae_ch in viewer.df.columns:
            series_to_plot.append(('V*C SAE J1727', viewer.get_numeric_column(sae_ch), 1.4))
        else:
            series_to_plot.append(('V*C SAE J1727', metrics['vc_sae'], 1.4))
        if ece_ch and getattr(viewer, 'df', None) is not None and ece_ch in viewer.df.columns:
            series_to_plot.append(('V*C ECE-R94', viewer.get_numeric_column(ece_ch), 1.2))
        else:
            series_to_plot.append(('V*C ECE-R94', metrics['vc_ece'], 1.2))
        for label, arr, width in series_to_plot:
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)
        self.ax.set_title(f"INJURY - CHEST ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('V*C (m/s)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Chest_VC_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def calculate_femur(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('寃쎄퀬', '癒쇱? DAT ?곗씠?곕? 濡쒕뱶?섏꽭??')
            return
        if not self._confirm_missing_dummy_profile():
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        left_ch = self._selected_channel(self.femur_left_var)
        right_ch = self._selected_channel(self.femur_right_var)
        if not (left_ch and right_ch):
            messagebox.showwarning('寃쎄퀬', 'FEMUR 怨꾩궛?먮뒗 Left/Right axial force 梨꾨꼸???꾩슂?⑸땲??')
            return
        left_sign = 1.0
        right_sign = 1.0
        try:
            left_force, used_left = self._resolve_standard_series_for_calc(left_ch, 'femur_injury', 'left', 600, left_sign)
            right_force, used_right = self._resolve_standard_series_for_calc(right_ch, 'femur_injury', 'right', 600, right_sign)
            result = calculate_femur_injury_bundle(
                time=self._get_time(),
                left_force=np.asarray(left_force, dtype=float),
                right_force=np.asarray(right_force, dtype=float),
                criterion_key=self.femur_dummy_var.get(),
                left_unit=self._unit_text(left_ch),
                right_unit=self._unit_text(right_ch),
            )
            metrics = result['metrics']
            st = self.slot_states[slot]
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
            st['channels'] = {'left': left_ch, 'right': right_ch}
            st['neg_flags'] = {}
            st['summary_text'] = result['summary_text']
            st['result_uid'] = st.get('result_uid') or self._injury_result_uid(slot)
            st['femur_metrics'] = metrics
            st['filtered_channels'] = {
                'left': self._femur_force_channel_name(slot, 'left'),
                'right': self._femur_force_channel_name(slot, 'right'),
            }
            st['femur_saved_payload'] = {
                'result_uid': st['result_uid'],
                'summary_text': result['summary_text'],
                'criterion_key': self.femur_dummy_var.get(),
                'dummy_name': st['dummy_name'],
                'dummy_profile': st['dummy_profile'],
                'channels': dict(st['channels']),
                'neg_flags': dict(st['neg_flags']),
                'governing_side': metrics.get('governing_side'),
                'overall_peak_n': float((metrics.get('overall_peak') or {}).get('value')) if (metrics.get('overall_peak') or {}).get('value') is not None else None,
                'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
            }
            preferred_graph_key = self._default_graph_key('combined')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['femur_saved_payload']['graph_key'] = st['graph_key']
            st['femur_saved_payload']['graph_uid'] = st['graph_uid']
            self._apply_summary_text(result['summary_text'])

            left_calc_name = self._femur_force_channel_name(slot, 'left')
            right_calc_name = self._femur_force_channel_name(slot, 'right')
            injury_df = viewer.df.copy(deep=True)
            injury_df[left_calc_name] = np.asarray(metrics.get('left_force_n', []), dtype=float)
            injury_df[right_calc_name] = np.asarray(metrics.get('right_force_n', []), dtype=float)
            metadata_override = {
                'units': self._merge_metadata_dicts(getattr(viewer, 'external_units', {}) or {}, {left_calc_name: 'N', right_calc_name: 'N'}),
                'descriptions': self._merge_metadata_dicts(getattr(viewer, 'external_descriptions', {}) or {}, {left_calc_name: f'{slot} Femur LEFT Axial Force - CFC600', right_calc_name: f'{slot} Femur RIGHT Axial Force - CFC600'}),
                'channel_filter_labels': self._merge_metadata_dicts(self.workbench.channel_filter_labels or {}, {left_calc_name: 'CFC 600', right_calc_name: 'CFC 600'}),
                'derived_channels': dict((self.workbench.dataset_metadata or {}).get('derived_channels') or {}),
            }
            metadata_override['derived_channels'][left_calc_name] = self._femur_force_channel_metadata(slot, used_left or left_ch, 'left')
            metadata_override['derived_channels'][right_calc_name] = self._femur_force_channel_metadata(slot, used_right or right_ch, 'right')
            self._save_section_payload(
                {
                    'type': 'injury_calculation',
                    'section': 'FEMUR',
                    'slot': slot,
                    'dummy_position': slot,
                    'result_uid': st['result_uid'],
                    'graph_uid': st.get('graph_uid'),
                    'message': 'Femur injury calculated',
                    'display_message': 'Femur injury calculated successfully',
                },
                dataframe=injury_df,
                metadata_extra=metadata_override,
            )
            self.show_femur_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('寃쎄퀬', str(exc))

    def _legacy_calculate_femur(self):
        self.calculate_femur()

    def _legacy_show_femur_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('femur_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('寃쎄퀬', '癒쇱? FEMUR 怨꾩궛???ㅽ뻾?섏꽭??')
            return
        if mode == 'left':
            self._plot_femur_side(metrics, slot, 'left')
        elif mode == 'right':
            self._plot_femur_side(metrics, slot, 'right')
        else:
            self._plot_femur_combined(metrics, slot)
        self.slot_states[slot]['graph_key'] = mode
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, mode)
        self._select_graph_tab(mode)
        if not silent:
            self._record_graph_selection(slot, mode)

    def _legacy_plot_femur_side(self, metrics, slot, side):
        t = np.asarray(metrics['time'], dtype=float)
        arr = np.asarray(metrics.get(f'{side}_force_n', []), dtype=float)
        limit = (metrics.get('criteria') or {}).get('femur_force_limit_n')
        self.ax.clear()
        valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
        if np.any(valid):
            self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.4, label=f'{side.upper()} FEMUR')
        if limit is not None:
            self.ax.axhline(limit, linestyle='--', linewidth=1.0, color='#dc2626', label=f'Limit = {fmt_value(limit, "N")}')
            self.ax.axhline(-limit, linestyle='--', linewidth=1.0, color='#dc2626')
        self.ax.set_title(f"INJURY - FEMUR ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Force (N)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Femur_{side.capitalize()}_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _legacy_plot_femur_combined(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        left = np.asarray(metrics.get('left_force_n', []), dtype=float)
        right = np.asarray(metrics.get('right_force_n', []), dtype=float)
        limit = (metrics.get('criteria') or {}).get('femur_force_limit_n')
        self.ax.clear()
        for label, arr, width in (('LEFT FEMUR', left, 1.3), ('RIGHT FEMUR', right, 1.3)):
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)
        if limit is not None:
            self.ax.axhline(limit, linestyle='--', linewidth=1.0, color='#dc2626', label=f'Limit = {fmt_value(limit, "N")}')
            self.ax.axhline(-limit, linestyle='--', linewidth=1.0, color='#dc2626')
        self.ax.set_title(f"INJURY - FEMUR ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Force (N)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Femur_Combined_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _build_pelvis_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="PELVIS - Resultant / 3ms", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            box,
            text="\uace8\ubc18 XYZ \uac00\uc18d\ub3c4 \ucc44\ub110\ub85c Resultant\uc640 3ms \uc9c0\ud45c\ub97c \uacc4\uc0b0\ud569\ub2c8\ub2e4.",
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="\uc785\ub825 \ucc44\ub110 \uc120\ud0dd", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.pelvis_x_combo = self._combo_row(inputs, "Pelvis Acc X", self.pelvis_x_var)
        self.pelvis_y_combo = self._combo_row(inputs, "Pelvis Acc Y", self.pelvis_y_var)
        self.pelvis_z_combo = self._combo_row(inputs, "Pelvis Acc Z", self.pelvis_z_var)
        tk.Label(
            box,
            textvariable=self.pelvis_guidance_var,
            bg="#ffffff",
            fg="#555555",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Checkbutton(
            opt,
            text="High-Resolution 3ms Search",
            variable=self.use_high_res_cumulative_3ms_var,
            onvalue=True,
            offvalue=False,
            bg="#ffffff",
        ).pack(side=tk.LEFT)
        tk.Button(opt, text="\uc804\uccb4 \uacc4\uc0b0", command=self.calculate_pelvis_all).pack(side=tk.RIGHT)
        return panel

    def _build_femur_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="FEMUR - Axial Force", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            box,
            text="\uc88c/\uc6b0 FEMUR \ucd95\ub825 \ucc44\ub110\uc744 \uc120\ud0dd\ud558\uba74 peak axial force\ub97c \uacc4\uc0b0\ud569\ub2c8\ub2e4.",
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="\uc785\ub825 \ucc44\ub110 \uc120\ud0dd", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.femur_left_combo = self._combo_row(inputs, "Left Femur *", self.femur_left_var)
        self.femur_right_combo = self._combo_row(inputs, "Right Femur *", self.femur_right_var)
        tk.Label(
            box,
            textvariable=self.femur_guidance_var,
            bg="#ffffff",
            fg="#555555",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Button(opt, text="\uc804\uccb4 \uacc4\uc0b0", command=self.calculate_femur_all).pack(side=tk.RIGHT)
        return panel

    def _build_knee_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="KNEE - Slider", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            box,
            text="\uc88c/\uc6b0 Hybrid III knee slider \ubcc0\uc704 \ucc44\ub110\uc744 \uc120\ud0dd\ud558\uba74 each side peak displacement\uc640 \ubc1c\uc0dd \uc2dc\uc810\uc744 \uacc4\uc0b0\ud569\ub2c8\ub2e4.",
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="\uc785\ub825 \ucc44\ub110 \uc120\ud0dd", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.knee_left_combo = self._combo_row(inputs, "Left Knee Slider *", self.knee_left_var)
        self.knee_right_combo = self._combo_row(inputs, "Right Knee Slider *", self.knee_right_var)
        tk.Label(
            box,
            textvariable=self.knee_guidance_var,
            bg="#ffffff",
            fg="#555555",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Button(opt, text="\uc804\uccb4 \uacc4\uc0b0", command=self.calculate_knee_all).pack(side=tk.RIGHT)
        return panel

    def _build_iliac_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="ILIAC - ASIS Fx / My", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            box,
            text="THOR 계열 iliac wing(ASIS) 좌/우 Fx, My 채널을 선택하면 side별 peak compression/tension, peak |My|와 Fx-My 응답을 계산합니다.",
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        inputs = tk.LabelFrame(box, text="입력 채널 선택", bg="#ffffff")
        inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.iliac_left_fx_combo = self._combo_row(inputs, "Left Iliac Fx *", self.iliac_left_fx_var)
        self.iliac_left_my_combo = self._combo_row(inputs, "Left Iliac My *", self.iliac_left_my_var)
        self.iliac_right_fx_combo = self._combo_row(inputs, "Right Iliac Fx *", self.iliac_right_fx_var)
        self.iliac_right_my_combo = self._combo_row(inputs, "Right Iliac My *", self.iliac_right_my_var)
        tk.Label(
            box,
            textvariable=self.iliac_guidance_var,
            bg="#ffffff",
            fg="#555555",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Button(opt, text="전체 계산", command=self.calculate_iliac_all).pack(side=tk.RIGHT)
        return panel

    def _build_tibia_panel(self, parent):
        panel = tk.Frame(parent, bg="#ffffff")
        box = tk.LabelFrame(panel, text="TIBIA - Index / Force / Moment", bg="#ffffff")
        box.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            box,
            text="Euro NCAP / IIHS lower-leg review를 대비해 좌/우 knee clevis와 upper/lower tibia 채널을 모두 입력받고, 현재 Tibia Index 계산은 upper/lower Fz, Mx, My를 사용합니다.",
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        left_inputs = tk.LabelFrame(box, text="LEFT TIBIA", bg="#ffffff")
        left_inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.tibia_left_knee_clevis_inner_fz_combo = self._combo_row(left_inputs, "Left Knee Clevis Inner Fz", self.tibia_left_knee_clevis_inner_fz_var, label_width=24)
        self.tibia_left_knee_clevis_outer_fz_combo = self._combo_row(left_inputs, "Left Knee Clevis Outer Fz", self.tibia_left_knee_clevis_outer_fz_var, label_width=24)
        self.tibia_left_upper_fx_combo = self._combo_row(left_inputs, "Left Upper Fx", self.tibia_left_upper_fx_var)
        self.tibia_left_upper_fz_combo = self._combo_row(left_inputs, "Left Upper Fz *", self.tibia_left_upper_fz_var)
        self.tibia_left_upper_mx_combo = self._combo_row(left_inputs, "Left Upper Mx *", self.tibia_left_upper_mx_var)
        self.tibia_left_upper_my_combo = self._combo_row(left_inputs, "Left Upper My *", self.tibia_left_upper_my_var)
        self.tibia_left_lower_fx_combo = self._combo_row(left_inputs, "Left Lower Fx", self.tibia_left_lower_fx_var)
        self.tibia_left_lower_fz_combo = self._combo_row(left_inputs, "Left Lower Fz *", self.tibia_left_lower_fz_var)
        self.tibia_left_lower_mx_combo = self._combo_row(left_inputs, "Left Lower Mx *", self.tibia_left_lower_mx_var)
        self.tibia_left_lower_my_combo = self._combo_row(left_inputs, "Left Lower My *", self.tibia_left_lower_my_var)
        right_inputs = tk.LabelFrame(box, text="RIGHT TIBIA", bg="#ffffff")
        right_inputs.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.tibia_right_knee_clevis_inner_fz_combo = self._combo_row(right_inputs, "Right Knee Clevis Inner Fz", self.tibia_right_knee_clevis_inner_fz_var, label_width=24)
        self.tibia_right_knee_clevis_outer_fz_combo = self._combo_row(right_inputs, "Right Knee Clevis Outer Fz", self.tibia_right_knee_clevis_outer_fz_var, label_width=24)
        self.tibia_right_upper_fx_combo = self._combo_row(right_inputs, "Right Upper Fx", self.tibia_right_upper_fx_var)
        self.tibia_right_upper_fz_combo = self._combo_row(right_inputs, "Right Upper Fz *", self.tibia_right_upper_fz_var)
        self.tibia_right_upper_mx_combo = self._combo_row(right_inputs, "Right Upper Mx *", self.tibia_right_upper_mx_var)
        self.tibia_right_upper_my_combo = self._combo_row(right_inputs, "Right Upper My *", self.tibia_right_upper_my_var)
        self.tibia_right_lower_fx_combo = self._combo_row(right_inputs, "Right Lower Fx", self.tibia_right_lower_fx_var)
        self.tibia_right_lower_fz_combo = self._combo_row(right_inputs, "Right Lower Fz *", self.tibia_right_lower_fz_var)
        self.tibia_right_lower_mx_combo = self._combo_row(right_inputs, "Right Lower Mx *", self.tibia_right_lower_mx_var)
        self.tibia_right_lower_my_combo = self._combo_row(right_inputs, "Right Lower My *", self.tibia_right_lower_my_var)
        tk.Label(
            box,
            textvariable=self.tibia_guidance_var,
            bg="#ffffff",
            fg="#555555",
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill=tk.X, padx=10, pady=(0, 6))
        opt = tk.Frame(box, bg="#ffffff")
        opt.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Button(opt, text="전체 계산", command=self.calculate_tibia_all).pack(side=tk.RIGHT)
        return panel

    def _graph_tab_specs(self):
        if self.initial_mode == 'hic':
            return [('head_xyz', 'HEAD X/Y/Z'), ('head_resultant', 'HEAD RESULTANT')]
        if self.initial_mode == 'nij':
            return [('fo', 'NECK FO'), ('mo', 'NECK MO'), ('mocy', 'MOCy'), ('nij_components', 'Nij - Components'), ('nij_overall', 'Nij - Overall')]
        if self.initial_mode == 'chest':
            return [('accel', 'Acceleration'), ('disp', 'Displacement'), ('vc', 'V*C')]
        if self.initial_mode == 'pelvis':
            return [('accel_resultant', 'ACC-RESULTANT')]
        if self.initial_mode == 'knee':
            return [('combined', 'Knee Slider')]
        if self.initial_mode == 'iliac':
            return [('force', 'Force'), ('moment', 'Moment'), ('crossplot', 'Fx-My')]
        if self.initial_mode == 'tibia':
            return [('tibia_index', 'Tibia Index'), ('axial_force', 'Axial Force'), ('moment_resultant', 'Moment')]
        return [('left', 'Left'), ('right', 'Right'), ('combined', 'Combined')]

    def reset_session_state(self):
        self.slot_states = {slot: self._new_slot_state() for slot in DUMMY_POSITION_OPTIONS}
        self.detected_groups = {}
        self.active_positions = ['B1']
        self.requested_row_positions = ['B1']
        self.current_available_channels = []
        self._display_to_channel = {}
        self._channel_to_display = {}
        self.dummy_count_var.set('1')
        self.active_dummy_var.set('B1')
        self.head_dummy_profile_var.set(HEAD_PROFILE_OPTIONS[0] if HEAD_PROFILE_OPTIONS else '')
        self.nij_dummy_var.set('H3_50M_FMVSS208')
        self.chest_dummy_var.set('H3_50M_FMVSS208')
        self.pelvis_dummy_var.set(HEAD_PROFILE_OPTIONS[0] if HEAD_PROFILE_OPTIONS else 'H3_50M_FMVSS208')
        self.femur_dummy_var.set(FEMUR_PROFILE_OPTIONS[0] if FEMUR_PROFILE_OPTIONS else 'H3_50M_FMVSS208')
        self.iliac_dummy_var.set(ILIAC_PROFILE_OPTIONS[0] if ILIAC_PROFILE_OPTIONS else 'THOR_50M_ASIS')
        self.tibia_dummy_var.set(TIBIA_PROFILE_OPTIONS[0] if TIBIA_PROFILE_OPTIONS else 'H3_50M_EURO_NCAP')

        for var in (
            self.hic_x_var, self.hic_y_var, self.hic_z_var,
            self.nij_fx_var, self.nij_fy_var, self.nij_fz_var, self.nij_mx_var, self.nij_my_var, self.nij_mz_var,
            self.chest_x_var, self.chest_y_var, self.chest_z_var, self.chest_disp_var,
            self.pelvis_x_var, self.pelvis_y_var, self.pelvis_z_var,
            self.femur_left_var, self.femur_right_var,
            self.knee_left_var, self.knee_right_var,
            self.iliac_left_fx_var, self.iliac_left_my_var, self.iliac_right_fx_var, self.iliac_right_my_var,
            self.tibia_left_knee_clevis_inner_fz_var, self.tibia_left_knee_clevis_outer_fz_var,
            self.tibia_left_upper_fx_var,
            self.tibia_left_upper_fz_var, self.tibia_left_upper_mx_var, self.tibia_left_upper_my_var,
            self.tibia_left_lower_fx_var,
            self.tibia_left_lower_fz_var, self.tibia_left_lower_mx_var, self.tibia_left_lower_my_var,
            self.tibia_right_knee_clevis_inner_fz_var, self.tibia_right_knee_clevis_outer_fz_var,
            self.tibia_right_upper_fx_var,
            self.tibia_right_upper_fz_var, self.tibia_right_upper_mx_var, self.tibia_right_upper_my_var,
            self.tibia_right_lower_fx_var,
            self.tibia_right_lower_fz_var, self.tibia_right_lower_mx_var, self.tibia_right_lower_my_var,
        ):
            var.set(BLANK_DISPLAY_VALUE)
        for var in (
            self.nij_fx_neg_var, self.nij_fy_neg_var, self.nij_fz_neg_var,
            self.nij_mx_neg_var, self.nij_my_neg_var, self.nij_mz_neg_var,
        ):
            var.set(False)

        self.hic15_var.set('HIC15')
        self.hic36_var.set('HIC36')
        self.clip3_var.set('3ms Clip')
        self.pelvis_guidance_var.set("\uace8\ubc18 XYZ \uac00\uc18d\ub3c4\ub85c Resultant \ubc0f 3ms \uc9c0\ud45c\ub97c \uacc4\uc0b0\ud569\ub2c8\ub2e4.")
        self.femur_guidance_var.set("\ub300\ud1f4\ubd80 \ucd95\ub825\uc740 CFC600 \uacbd\ub85c\ub97c \uae30\uc900\uc73c\ub85c \uacc4\uc0b0\ud569\ub2c8\ub2e4.")
        self.knee_guidance_var.set("Hybrid III knee slider 채널의 좌/우 peak displacement와 발생 시점을 계산합니다.")
        self.iliac_guidance_var.set("THOR 계열 iliac wing(ASIS) Fx/My 좌우 채널로 side별 peak 하중/모멘트와 Fx-My 응답을 계산합니다.")
        self.tibia_guidance_var.set("좌/우 knee clevis, upper/lower tibia의 Fx/Fz/Mx/My 채널을 모두 저장하고, 현재 계산은 upper/lower Fz, Mx, My 기반 Tibia Index와 compression, bending resultant를 사용합니다.")
        self.nij_guidance_var.set('Fx/Fy/Fz \uad8c\uc7a5 CFC1000 | Mx/My/Mz \uad8c\uc7a5 CFC600')

        if hasattr(self, 'multi_dummy_panel'):
            for slot in DUMMY_POSITION_OPTIONS:
                self.multi_dummy_panel.name_var(slot).set('')
                self.multi_dummy_panel.profile_var(slot).set('')
            self.multi_dummy_panel.set_detected_positions([])
            self.multi_dummy_panel.set_active_positions(['B1'], explicit_positions=['B1'])
            self.multi_dummy_panel.set_group_info("\uac80\ucd9c \uc704\uce58: \ubbf8\uac80\ucd9c")
            self.multi_dummy_panel.refresh_tab_labels(['B1'])
            self.multi_dummy_panel.refresh_profile_options()

        self._clear_channel_selections()
        if self._result_widget is not None:
            self._set_result_text(self._result_widget, '-')
        self.ax.clear()
        self.ax.set_title('INJURY GRAPH')
        self.ax.set_xlabel('Time (ms)')
        self.ax.set_ylabel('Value')
        self.ax.grid(True)
        self.canvas.draw_idle()
        specs = self._graph_tab_specs()
        if specs:
            self._select_graph_tab(specs[0][0])

    def _save_slot_state(self, slot):
        state = self.slot_states[slot]
        state['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
        state['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
        if self.initial_mode == 'hic':
            state['channels'] = {'x': self._selected_channel(self.hic_x_var), 'y': self._selected_channel(self.hic_y_var), 'z': self._selected_channel(self.hic_z_var)}
            state['neg_flags'] = {}
        elif self.initial_mode == 'nij':
            state['channels'] = {
                'Fx': self._selected_channel(self.nij_fx_var),
                'Fy': self._selected_channel(self.nij_fy_var),
                'Fz': self._selected_channel(self.nij_fz_var),
                'Mx': self._selected_channel(self.nij_mx_var),
                'My': self._selected_channel(self.nij_my_var),
                'Mz': self._selected_channel(self.nij_mz_var),
            }
            state['neg_flags'] = {
                'Fx': bool(self.nij_fx_neg_var.get()),
                'Fy': bool(self.nij_fy_neg_var.get()),
                'Fz': bool(self.nij_fz_neg_var.get()),
                'Mx': bool(self.nij_mx_neg_var.get()),
                'My': bool(self.nij_my_neg_var.get()),
                'Mz': bool(self.nij_mz_neg_var.get()),
            }
        elif self.initial_mode == 'chest':
            state['channels'] = {
                'x': self._selected_channel(self.chest_x_var),
                'y': self._selected_channel(self.chest_y_var),
                'z': self._selected_channel(self.chest_z_var),
                'disp': self._selected_channel(self.chest_disp_var),
            }
            state['neg_flags'] = {}
        elif self.initial_mode == 'pelvis':
            state['channels'] = {
                'x': self._selected_channel(self.pelvis_x_var),
                'y': self._selected_channel(self.pelvis_y_var),
                'z': self._selected_channel(self.pelvis_z_var),
            }
            state['neg_flags'] = {}
        elif self.initial_mode == 'femur':
            state['channels'] = {'left': self._selected_channel(self.femur_left_var), 'right': self._selected_channel(self.femur_right_var)}
            state['neg_flags'] = {}
        elif self.initial_mode == 'knee':
            state['channels'] = {'left': self._selected_channel(self.knee_left_var), 'right': self._selected_channel(self.knee_right_var)}
            state['neg_flags'] = {}
        elif self.initial_mode == 'iliac':
            state['channels'] = {
                'left_fx': self._selected_channel(self.iliac_left_fx_var),
                'left_my': self._selected_channel(self.iliac_left_my_var),
                'right_fx': self._selected_channel(self.iliac_right_fx_var),
                'right_my': self._selected_channel(self.iliac_right_my_var),
            }
            state['neg_flags'] = {}
        else:
            state['channels'] = {
                'left_knee_clevis_inner_fz': self._selected_channel(self.tibia_left_knee_clevis_inner_fz_var),
                'left_knee_clevis_outer_fz': self._selected_channel(self.tibia_left_knee_clevis_outer_fz_var),
                'left_upper_fx': self._selected_channel(self.tibia_left_upper_fx_var),
                'left_upper_fz': self._selected_channel(self.tibia_left_upper_fz_var),
                'left_upper_mx': self._selected_channel(self.tibia_left_upper_mx_var),
                'left_upper_my': self._selected_channel(self.tibia_left_upper_my_var),
                'left_lower_fx': self._selected_channel(self.tibia_left_lower_fx_var),
                'left_lower_fz': self._selected_channel(self.tibia_left_lower_fz_var),
                'left_lower_mx': self._selected_channel(self.tibia_left_lower_mx_var),
                'left_lower_my': self._selected_channel(self.tibia_left_lower_my_var),
                'right_knee_clevis_inner_fz': self._selected_channel(self.tibia_right_knee_clevis_inner_fz_var),
                'right_knee_clevis_outer_fz': self._selected_channel(self.tibia_right_knee_clevis_outer_fz_var),
                'right_upper_fx': self._selected_channel(self.tibia_right_upper_fx_var),
                'right_upper_fz': self._selected_channel(self.tibia_right_upper_fz_var),
                'right_upper_mx': self._selected_channel(self.tibia_right_upper_mx_var),
                'right_upper_my': self._selected_channel(self.tibia_right_upper_my_var),
                'right_lower_fx': self._selected_channel(self.tibia_right_lower_fx_var),
                'right_lower_fz': self._selected_channel(self.tibia_right_lower_fz_var),
                'right_lower_mx': self._selected_channel(self.tibia_right_lower_mx_var),
                'right_lower_my': self._selected_channel(self.tibia_right_lower_my_var),
            }
            state['neg_flags'] = {}

    def _load_active_slot_state(self):
        slot = self._active_slot()
        self._last_ui_slot = slot
        state = self.slot_states[slot]
        profile_var = self._dummy_profile_var()
        if state.get('dummy_profile'):
            profile_var.set(state['dummy_profile'])
        else:
            inferred = self._infer_profile_for_slot(slot)
            if inferred:
                state['dummy_profile'] = inferred
                profile_var.set(inferred)
            elif not profile_var.get() and self._profile_options():
                profile_var.set(self._profile_options()[0])
        self._apply_slot_meta_to_ui(slot)
        self._apply_slot_channels_to_ui(state.get('channels') or {})
        if self.initial_mode == 'nij':
            neg = state.get('neg_flags') or {}
            self.nij_fx_neg_var.set(bool(neg.get('Fx', False)))
            self.nij_fy_neg_var.set(bool(neg.get('Fy', False)))
            self.nij_fz_neg_var.set(bool(neg.get('Fz', False)))
            self.nij_mx_neg_var.set(bool(neg.get('Mx', False)))
            self.nij_my_neg_var.set(bool(neg.get('My', False)))
            self.nij_mz_neg_var.set(bool(neg.get('Mz', False)))
        self._update_combined_summary()
        graph_key = state.get('graph_key')
        if graph_key:
            self._show_saved_graph_for_slot(slot, graph_key)

    def _apply_slot_channels_to_ui(self, channels):
        if self.initial_mode == 'hic':
            self._set_var_from_channel(self.hic_x_var, channels.get('x'))
            self._set_var_from_channel(self.hic_y_var, channels.get('y'))
            self._set_var_from_channel(self.hic_z_var, channels.get('z'))
        elif self.initial_mode == 'nij':
            self._set_var_from_channel(self.nij_fx_var, channels.get('Fx'))
            self._set_var_from_channel(self.nij_fy_var, channels.get('Fy'))
            self._set_var_from_channel(self.nij_fz_var, channels.get('Fz'))
            self._set_var_from_channel(self.nij_mx_var, channels.get('Mx'))
            self._set_var_from_channel(self.nij_my_var, channels.get('My'))
            self._set_var_from_channel(self.nij_mz_var, channels.get('Mz'))
        elif self.initial_mode == 'chest':
            self._set_var_from_channel(self.chest_x_var, channels.get('x'))
            self._set_var_from_channel(self.chest_y_var, channels.get('y'))
            self._set_var_from_channel(self.chest_z_var, channels.get('z'))
            self._set_var_from_channel(self.chest_disp_var, channels.get('disp'))
        elif self.initial_mode == 'pelvis':
            self._set_var_from_channel(self.pelvis_x_var, channels.get('x'))
            self._set_var_from_channel(self.pelvis_y_var, channels.get('y'))
            self._set_var_from_channel(self.pelvis_z_var, channels.get('z'))
        elif self.initial_mode == 'femur':
            self._set_var_from_channel(self.femur_left_var, channels.get('left'))
            self._set_var_from_channel(self.femur_right_var, channels.get('right'))
        elif self.initial_mode == 'knee':
            self._set_var_from_channel(self.knee_left_var, channels.get('left'))
            self._set_var_from_channel(self.knee_right_var, channels.get('right'))
        elif self.initial_mode == 'iliac':
            self._set_var_from_channel(self.iliac_left_fx_var, channels.get('left_fx'))
            self._set_var_from_channel(self.iliac_left_my_var, channels.get('left_my'))
            self._set_var_from_channel(self.iliac_right_fx_var, channels.get('right_fx'))
            self._set_var_from_channel(self.iliac_right_my_var, channels.get('right_my'))
        else:
            self._set_var_from_channel(self.tibia_left_knee_clevis_inner_fz_var, channels.get('left_knee_clevis_inner_fz'))
            self._set_var_from_channel(self.tibia_left_knee_clevis_outer_fz_var, channels.get('left_knee_clevis_outer_fz'))
            self._set_var_from_channel(self.tibia_left_upper_fx_var, channels.get('left_upper_fx'))
            self._set_var_from_channel(self.tibia_left_upper_fz_var, channels.get('left_upper_fz'))
            self._set_var_from_channel(self.tibia_left_upper_mx_var, channels.get('left_upper_mx'))
            self._set_var_from_channel(self.tibia_left_upper_my_var, channels.get('left_upper_my'))
            self._set_var_from_channel(self.tibia_left_lower_fx_var, channels.get('left_lower_fx'))
            self._set_var_from_channel(self.tibia_left_lower_fz_var, channels.get('left_lower_fz'))
            self._set_var_from_channel(self.tibia_left_lower_mx_var, channels.get('left_lower_mx'))
            self._set_var_from_channel(self.tibia_left_lower_my_var, channels.get('left_lower_my'))
            self._set_var_from_channel(self.tibia_right_knee_clevis_inner_fz_var, channels.get('right_knee_clevis_inner_fz'))
            self._set_var_from_channel(self.tibia_right_knee_clevis_outer_fz_var, channels.get('right_knee_clevis_outer_fz'))
            self._set_var_from_channel(self.tibia_right_upper_fx_var, channels.get('right_upper_fx'))
            self._set_var_from_channel(self.tibia_right_upper_fz_var, channels.get('right_upper_fz'))
            self._set_var_from_channel(self.tibia_right_upper_mx_var, channels.get('right_upper_mx'))
            self._set_var_from_channel(self.tibia_right_upper_my_var, channels.get('right_upper_my'))
            self._set_var_from_channel(self.tibia_right_lower_fx_var, channels.get('right_lower_fx'))
            self._set_var_from_channel(self.tibia_right_lower_fz_var, channels.get('right_lower_fz'))
            self._set_var_from_channel(self.tibia_right_lower_mx_var, channels.get('right_lower_mx'))
            self._set_var_from_channel(self.tibia_right_lower_my_var, channels.get('right_lower_my'))

    def _clear_channel_selections(self):
        if self.initial_mode == 'hic':
            vars_to_clear = (self.hic_x_var, self.hic_y_var, self.hic_z_var)
        elif self.initial_mode == 'nij':
            vars_to_clear = (self.nij_fx_var, self.nij_fy_var, self.nij_fz_var, self.nij_mx_var, self.nij_my_var, self.nij_mz_var)
        elif self.initial_mode == 'chest':
            vars_to_clear = (self.chest_x_var, self.chest_y_var, self.chest_z_var, self.chest_disp_var)
        elif self.initial_mode == 'pelvis':
            vars_to_clear = (self.pelvis_x_var, self.pelvis_y_var, self.pelvis_z_var)
        elif self.initial_mode == 'femur':
            vars_to_clear = (self.femur_left_var, self.femur_right_var)
        elif self.initial_mode == 'knee':
            vars_to_clear = (self.knee_left_var, self.knee_right_var)
        elif self.initial_mode == 'iliac':
            vars_to_clear = (self.iliac_left_fx_var, self.iliac_left_my_var, self.iliac_right_fx_var, self.iliac_right_my_var)
        else:
            vars_to_clear = (
                self.tibia_left_knee_clevis_inner_fz_var, self.tibia_left_knee_clevis_outer_fz_var,
                self.tibia_left_upper_fx_var,
                self.tibia_left_upper_fz_var, self.tibia_left_upper_mx_var, self.tibia_left_upper_my_var,
                self.tibia_left_lower_fx_var,
                self.tibia_left_lower_fz_var, self.tibia_left_lower_mx_var, self.tibia_left_lower_my_var,
                self.tibia_right_knee_clevis_inner_fz_var, self.tibia_right_knee_clevis_outer_fz_var,
                self.tibia_right_upper_fx_var,
                self.tibia_right_upper_fz_var, self.tibia_right_upper_mx_var, self.tibia_right_upper_my_var,
                self.tibia_right_lower_fx_var,
                self.tibia_right_lower_fz_var, self.tibia_right_lower_mx_var, self.tibia_right_lower_my_var,
            )
        for var in vars_to_clear:
            var.set(BLANK_DISPLAY_VALUE)

    def _build_section_payload(self):
        slots_payload = {}
        for slot in self._active_positions():
            st = self.slot_states[slot]
            payload = {}
            if self.initial_mode == 'hic':
                payload.update(dict(st.get('head_metadata') or {}))
            elif self.initial_mode == 'nij':
                payload.update(dict(st.get('neck_saved_payload') or {}))
            elif self.initial_mode == 'chest':
                payload.update(dict(st.get('chest_saved_payload') or {}))
            elif self.initial_mode == 'pelvis':
                payload.update(dict(st.get('pelvis_saved_payload') or {}))
            elif self.initial_mode == 'femur':
                payload.update(dict(st.get('femur_saved_payload') or {}))
            elif self.initial_mode == 'knee':
                payload.update(dict(st.get('knee_saved_payload') or {}))
            elif self.initial_mode == 'iliac':
                payload.update(dict(st.get('iliac_saved_payload') or {}))
            else:
                payload.update(dict(st.get('tibia_saved_payload') or {}))
            payload.update({
                'result_uid': st.get('result_uid') or self._injury_result_uid(slot),
                'section_key': self._section_key(),
                'slot': slot,
                'dummy_name': st.get('dummy_name') or '',
                'dummy_profile': st.get('dummy_profile') or '',
                'channels': dict(st.get('channels') or {}),
                'neg_flags': dict(st.get('neg_flags') or {}),
                'summary_text': st.get('summary_text') or '-',
                'graph_key': st.get('graph_key'),
                'graph_uid': st.get('graph_uid') or (self._injury_graph_uid(slot, st.get('graph_key')) if st.get('graph_key') else ''),
            })
            payload = self._enrich_payload_with_structured_results(payload, st)
            payload_key = self._slot_saved_payload_key()
            if payload_key:
                st[payload_key] = dict(payload)
            slots_payload[slot] = payload
        return {
            'dummy_count': self._active_count(),
            'active_slot': self._active_slot(),
            'active_positions': list(self._active_positions()),
            'row_positions': list(self.requested_row_positions[:self._active_count()]),
            'detected_groups': {k: list(v) for k, v in self.detected_groups.items()},
            'slots': slots_payload,
            'result_registry': {slot: (payload.get('result_uid') or self._injury_result_uid(slot)) for slot, payload in slots_payload.items()},
        }

    def _restore_saved_injury_results(self):
        saved = self._injury_metadata_bundle().get(self._section_key()) or {}
        if not saved:
            return
        count = int(saved.get('dummy_count') or 1)
        self.dummy_count_var.set(str(min(max(count, 1), 6)))
        self.detected_groups = {k: list(v) for k, v in dict(saved.get('detected_groups') or {}).items()}
        if not self.detected_groups:
            self.detected_groups = self._detect_dummy_groups()
        for slot in DUMMY_POSITION_OPTIONS:
            payload = dict((saved.get('slots') or {}).get(slot) or {})
            st = self.slot_states[slot]
            st['result_uid'] = payload.get('result_uid') or st.get('result_uid') or self._injury_result_uid(slot)
            st['dummy_name'] = payload.get('dummy_name') or st.get('dummy_name') or ''
            st['dummy_profile'] = payload.get('dummy_profile') or st.get('dummy_profile') or ''
            st['channels'] = dict(payload.get('channels') or {})
            st['neg_flags'] = dict(payload.get('neg_flags') or {})
            payload_version = int(payload.get('summary_format_version') or 0)
            st['summary_text'] = payload.get('summary_text') or '-'
            if payload_version and payload_version < SUMMARY_FORMAT_VERSION:
                st['summary_text'] = '-'
            if 'use_high_res_cumulative_3ms' in payload:
                st['use_high_res_cumulative_3ms'] = bool(payload.get('use_high_res_cumulative_3ms'))
            elif 'high_res_3ms_sliding_window' in payload:
                st['use_high_res_cumulative_3ms'] = bool(payload.get('high_res_3ms_sliding_window'))
            restored_graph_key = payload.get('graph_key')
            if self.initial_mode == 'nij':
                restored_graph_key = self._normalize_neck_graph_key(restored_graph_key)
            st['graph_key'] = restored_graph_key
            st['graph_uid'] = payload.get('graph_uid') or (self._injury_graph_uid(slot, restored_graph_key) if restored_graph_key else '')
            if self.initial_mode == 'hic':
                st['head_metadata'] = payload
            elif self.initial_mode == 'nij':
                st['neck_saved_payload'] = payload
            elif self.initial_mode == 'chest':
                st['chest_saved_payload'] = payload
            elif self.initial_mode == 'pelvis':
                st['pelvis_saved_payload'] = payload
            elif self.initial_mode == 'femur':
                st['femur_saved_payload'] = payload
            elif self.initial_mode == 'knee':
                st['knee_saved_payload'] = payload
            elif self.initial_mode == 'iliac':
                st['iliac_saved_payload'] = payload
            else:
                st['tibia_saved_payload'] = payload
        restored_positions = [slot for slot in (saved.get('active_positions') or []) if slot in DUMMY_POSITION_OPTIONS]
        if restored_positions:
            self.active_positions = restored_positions[:self._active_count()]
        saved_row_positions = list(saved.get('row_positions') or [])
        if saved_row_positions:
            self.requested_row_positions = saved_row_positions[:self._active_count()]
        active_slot = saved.get('active_slot') or 'B1'
        self._sync_all_slot_meta_to_panel()
        if active_slot in self._active_positions():
            self.active_dummy_var.set(active_slot)
        if active_slot in self.slot_states and self.slot_states[active_slot].get('summary_text') == '-':
            if self._ensure_slot_plot_data(active_slot):
                self._apply_summary_text(self.slot_states[active_slot].get('summary_text') or '-')
        self._update_group_info_label()

    def refresh_channel_lists(self, keep_existing=True):
        viewer = self.workbench.viewer
        try:
            self.detected_groups = self._detect_dummy_groups()
            self._sync_active_positions()
            placeholder_slot = self._is_placeholder_slot()
            channels = [] if placeholder_slot else self._candidate_channels_for_active_slot()
            self.current_available_channels = list(channels)
            display_values = [BLANK_DISPLAY_VALUE]
            mapping = {BLANK_DISPLAY_VALUE: ''}
            reverse = {'': BLANK_DISPLAY_VALUE}
            used = set()
            for ch in channels:
                display = self._display_name(viewer, ch, used)
                used.add(display)
                display_values.append(display)
                mapping[display] = ch
                reverse[ch] = display
            self._display_to_channel = mapping
            self._channel_to_display = reverse
            if self.initial_mode == 'hic':
                combos = [self.hic_x_combo, self.hic_y_combo, self.hic_z_combo]
            elif self.initial_mode == 'nij':
                combos = [self.nij_fx_combo, self.nij_fy_combo, self.nij_fz_combo, self.nij_mx_combo, self.nij_my_combo, self.nij_mz_combo]
            elif self.initial_mode == 'chest':
                combos = [self.chest_x_combo, self.chest_y_combo, self.chest_z_combo, self.chest_disp_combo]
            elif self.initial_mode == 'pelvis':
                combos = [self.pelvis_x_combo, self.pelvis_y_combo, self.pelvis_z_combo]
            elif self.initial_mode == 'femur':
                combos = [self.femur_left_combo, self.femur_right_combo]
            elif self.initial_mode == 'knee':
                combos = [self.knee_left_combo, self.knee_right_combo]
            elif self.initial_mode == 'iliac':
                combos = [self.iliac_left_fx_combo, self.iliac_left_my_combo, self.iliac_right_fx_combo, self.iliac_right_my_combo]
            else:
                combos = [
                    self.tibia_left_knee_clevis_inner_fz_combo, self.tibia_left_knee_clevis_outer_fz_combo,
                    self.tibia_left_upper_fx_combo,
                    self.tibia_left_upper_fz_combo, self.tibia_left_upper_mx_combo, self.tibia_left_upper_my_combo,
                    self.tibia_left_lower_fx_combo,
                    self.tibia_left_lower_fz_combo, self.tibia_left_lower_mx_combo, self.tibia_left_lower_my_combo,
                    self.tibia_right_knee_clevis_inner_fz_combo, self.tibia_right_knee_clevis_outer_fz_combo,
                    self.tibia_right_upper_fx_combo,
                    self.tibia_right_upper_fz_combo, self.tibia_right_upper_mx_combo, self.tibia_right_upper_my_combo,
                    self.tibia_right_lower_fx_combo,
                    self.tibia_right_lower_fz_combo, self.tibia_right_lower_mx_combo, self.tibia_right_lower_my_combo,
                ]
            for combo in combos:
                combo['values'] = display_values
            self._update_group_info_label()
            slot_channels = self._active_slot_state().get('channels') or {}
            has_existing = any(slot_channels.values())
            if placeholder_slot:
                self._clear_channel_selections()
                for key in list(slot_channels.keys()):
                    slot_channels[key] = ''
            else:
                auto_pick = self._compute_auto_pick_for_active_slot()
                if keep_existing and has_existing:
                    merged = self._merge_existing_with_auto_pick(slot_channels, auto_pick)
                    self.slot_states[self._active_slot()]['channels'] = dict(merged)
                    self._apply_slot_channels_to_ui(merged)
                else:
                    self.apply_auto_guess_for_active_slot(auto_pick=auto_pick)
            self._refresh_neck_guidance_text()
        except Exception:
            self.current_available_channels = []
            self._display_to_channel = {}
            self._channel_to_display = {}
            if self.initial_mode == 'hic':
                combos = [self.hic_x_combo, self.hic_y_combo, self.hic_z_combo]
            elif self.initial_mode == 'nij':
                combos = [self.nij_fx_combo, self.nij_fy_combo, self.nij_fz_combo, self.nij_mx_combo, self.nij_my_combo, self.nij_mz_combo]
            elif self.initial_mode == 'chest':
                combos = [self.chest_x_combo, self.chest_y_combo, self.chest_z_combo, self.chest_disp_combo]
            elif self.initial_mode == 'pelvis':
                combos = [self.pelvis_x_combo, self.pelvis_y_combo, self.pelvis_z_combo]
            elif self.initial_mode == 'femur':
                combos = [self.femur_left_combo, self.femur_right_combo]
            elif self.initial_mode == 'knee':
                combos = [self.knee_left_combo, self.knee_right_combo]
            elif self.initial_mode == 'iliac':
                combos = [self.iliac_left_fx_combo, self.iliac_left_my_combo, self.iliac_right_fx_combo, self.iliac_right_my_combo]
            else:
                combos = [
                    self.tibia_left_knee_clevis_inner_fz_combo, self.tibia_left_knee_clevis_outer_fz_combo,
                    self.tibia_left_upper_fx_combo,
                    self.tibia_left_upper_fz_combo, self.tibia_left_upper_mx_combo, self.tibia_left_upper_my_combo,
                    self.tibia_left_lower_fx_combo,
                    self.tibia_left_lower_fz_combo, self.tibia_left_lower_mx_combo, self.tibia_left_lower_my_combo,
                    self.tibia_right_knee_clevis_inner_fz_combo, self.tibia_right_knee_clevis_outer_fz_combo,
                    self.tibia_right_upper_fx_combo,
                    self.tibia_right_upper_fz_combo, self.tibia_right_upper_mx_combo, self.tibia_right_upper_my_combo,
                    self.tibia_right_lower_fx_combo,
                    self.tibia_right_lower_fz_combo, self.tibia_right_lower_mx_combo, self.tibia_right_lower_my_combo,
                ]
            for combo in combos:
                combo['values'] = []
            self._clear_channel_selections()

    def _score_knee_slider_channel(self, channel_name, side='left'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f" {channel_name} {desc} {unit} ".lower().replace('_', ' ')
        score = 0
        score += self._parsed_match_score(
            channel_name,
            sensor_location='knee',
            data_type_code='DS',
            side=side,
            preferred_filter_codes=self._preferred_filter_codes('knee', side),
        )
        score += self._score_isocode_keywords(channel_name, ['knee', 'slider', side, 'disp'])
        if 'slider' in text or 'slide' in text:
            score += 24
        if 'clevis' in text:
            score -= 30
        if 'knee' in text or 'knsl' in text:
            score += 10
        if side == 'left' and any(tag in text for tag in (' left ', 'driver', ' lt ')):
            score += 12
        if side == 'right' and any(tag in text for tag in (' right ', 'passenger', ' rt ')):
            score += 12
        if 'mm' in unit.lower():
            score += 4
        return score

    def _auto_pick_knee_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {'left': '', 'right': ''}
        selected = {}
        used = set()
        for role, fallback in (('left', ['knee', 'slider', 'left']), ('right', ['knee', 'slider', 'right'])):
            best, best_score = self._best_channel_by_score(channels, lambda ch, r=role: self._score_knee_slider_channel(ch, r), used)
            if best and best_score > 0:
                selected[role] = best
                used.add(best)
            else:
                selected[role] = self._guess_from_candidates(fallback, used, preferred_filter_codes=self._preferred_filter_codes('knee', role))
                if selected[role]:
                    used.add(selected[role])
        return selected

    def _score_iliac_channel(self, channel_name, side='left', component='fx'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f" {channel_name} {desc} {unit} ".lower().replace('_', ' ')
        score = 0
        keyword_type = 'force' if component == 'fx' else 'moment'
        axis = 'x' if component == 'fx' else 'y'
        score += self._parsed_match_score(
            channel_name,
            sensor_location='iliac',
            data_type_code='FO' if keyword_type == 'force' else 'MO',
            axis_code=axis.upper(),
            side=side,
            preferred_filter_codes=self._preferred_filter_codes('iliac', f'{side}_{component}'),
        )
        score += self._score_isocode_keywords(channel_name, ['iliac', side, keyword_type, axis])
        if any(tag in text for tag in ('iliac', 'asis', 'pelvis')):
            score += 14
        if side == 'left' and any(tag in text for tag in (' left ', 'driver', ' lt ')):
            score += 14
        if side == 'right' and any(tag in text for tag in (' right ', 'passenger', ' rt ')):
            score += 14
        if component == 'fx' and any(tag in text for tag in (' fx ', 'force x', 'fo x', 'load')):
            score += 16
        if component == 'my' and any(tag in text for tag in (' my ', 'moment y', 'mo y')):
            score += 16
        unit_norm = unit.lower().replace(' ', '')
        if component == 'fx' and any(tag in unit_norm for tag in ('n', 'kn', 'lbf', 'lb')):
            score += 4
        if component == 'my' and any(tag in unit_norm for tag in ('nm', 'n*m', 'lb*ft', 'lbf*ft', 'lb*in', 'lbf*in')):
            score += 4
        return score

    def _auto_pick_iliac_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {'left_fx': '', 'left_my': '', 'right_fx': '', 'right_my': ''}
        selected = {}
        used = set()
        for role in ('left_fx', 'left_my', 'right_fx', 'right_my'):
            side, component = role.split('_', 1)
            best, best_score = self._best_channel_by_score(
                channels,
                lambda ch, s=side, c=component: self._score_iliac_channel(ch, s, c),
                used,
            )
            if best and best_score > 0 and self._channel_matches_input_spec(best, 'iliac', role):
                selected[role] = best
                used.add(best)
            else:
                # Strict ISOCODE-first policy: if there is no valid iliac channel, keep blank.
                # Do not fall back to loosely matched knee/pelvis channels.
                selected[role] = ''
        return selected

    def _score_pelvis_channel(self, channel_name, role='x'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f"{channel_name} {desc} {unit}".lower().replace('_', ' ')
        score = 0
        score += self._parsed_match_score(
            channel_name,
            sensor_location='pelvis',
            data_type_code='AC',
            axis_code=role.upper(),
            preferred_filter_codes=self._preferred_filter_codes('pelvis', role),
        )
        score += self._score_isocode_keywords(channel_name, ['pelvis', 'acc', role])
        if any(tag in text for tag in ('pelvis', 'pelv', 'hip', 'iliac')):
            score += 14
        if any(tag in text for tag in ('acc', 'acceler')):
            score += 12
        axis_tokens = {
            'x': (' x ', 'ax', 'acc x', 'accx', '_x'),
            'y': (' y ', 'ay', 'acc y', 'accy', '_y'),
            'z': (' z ', 'az', 'acc z', 'accz', '_z'),
        }
        if any(token in f" {text} " for token in axis_tokens[role]):
            score += 16
        for other_role, tokens in axis_tokens.items():
            if other_role == role:
                continue
            if any(token in f" {text} " for token in tokens):
                score -= 8
        unit_norm = unit.strip().lower().replace(' ', '')
        if unit_norm in ('g', 'm/s²', 'm/s^2', 'm/s2', 'ms-2', 'mps2'):
            score += 3
        return score

    def _auto_pick_pelvis_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {'x': '', 'y': '', 'z': ''}
        selected = {}
        used = set()
        for role, fallback in (('x', ['pelvis', 'acc', 'x']), ('y', ['pelvis', 'acc', 'y']), ('z', ['pelvis', 'acc', 'z'])):
            best = ''
            best_score = -10**9
            for ch in channels:
                if ch in used:
                    continue
                score = self._score_pelvis_channel(ch, role)
                if score > best_score:
                    best = ch
                    best_score = score
            if best and best_score > 0:
                selected[role] = best
                used.add(best)
            else:
                selected[role] = self._guess_from_candidates(fallback, used)
                if selected[role]:
                    used.add(selected[role])
        return selected

    def _score_tibia_channel(self, channel_name, side='left', level='upper', component='fz'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f" {channel_name} {desc} {unit} ".lower().replace('_', ' ')
        score = 0
        score += self._parsed_match_score(
            channel_name,
            sensor_location='tibia',
            data_type_code='FO' if component in ('fx', 'fz') else 'MO',
            axis_code=component[-1].upper(),
            side=side,
            level=level,
            preferred_filter_codes=self._preferred_filter_codes('tibia', f'{side}_{level}_{component}'),
        )
        score += self._score_isocode_keywords(
            channel_name,
            ['tibia', side, level, 'force' if component in ('fx', 'fz') else 'moment', component],
        )
        if any(tag in text for tag in ('knee clevis', 'clevis')):
            score += 10
        if any(tag in text for tag in ('tibia', 'tib', 'lower leg', 'shin')):
            score += 16
        if side == 'left' and any(tag in text for tag in (' left ', 'driver', ' lt ', ' l tib', ' tib l', ' tibia l')):
            score += 16
        if side == 'right' and any(tag in text for tag in (' right ', 'passenger', ' rt ', ' r tib', ' tib r', ' tibia r')):
            score += 16
        if level == 'upper' and any(tag in text for tag in (' upper ', 'up ', 'prox', 'proximal')):
            score += 12
        if level == 'lower' and any(tag in text for tag in (' lower ', 'low ', 'dist', 'distal')):
            score += 12
        if component == 'fx' and any(tag in text for tag in (' fx ', ' force x', 'shear', 'lateral', 'fore-aft')):
            score += 16
        if component == 'fz' and any(tag in text for tag in (' fz ', ' force z', 'axial', 'compression', 'load')):
            score += 16
        if component == 'mx' and any(tag in text for tag in (' mx ', ' moment x', 'mxb', 'bend x')):
            score += 16
        if component == 'my' and any(tag in text for tag in (' my ', ' moment y', 'myb', 'bend y', 'a-p')):
            score += 16
        unit_norm = unit.lower().replace(' ', '')
        if component in ('fx', 'fz') and any(tag in unit_norm for tag in ('n', 'kn', 'lbf', 'lb')):
            score += 4
        if component in ('mx', 'my') and any(tag in unit_norm for tag in ('nm', 'n*m', 'lb*ft', 'lbf*ft', 'lb*in', 'lbf*in')):
            score += 4
        return score

    def _score_tibia_clevis_channel(self, channel_name, side='left', position='inner'):
        viewer = self.workbench.viewer
        desc = (viewer.get_channel_display_name(channel_name) or '')
        unit = (viewer.get_y_axis_label(channel_name) or '')
        text = f" {channel_name} {desc} {unit} ".lower().replace('_', ' ')
        score = 0
        score += self._parsed_match_score(
            channel_name,
            sensor_location='knee',
            data_type_code='FO',
            axis_code='Z',
            side=side,
            position_detail=position,
            main_location_code='CLEV',
            preferred_filter_codes=self._preferred_filter_codes('tibia', f'{side}_knee_clevis_{position}_fz'),
        )
        score += self._score_isocode_keywords(channel_name, ['knee', 'clevis', side, position, 'force', 'z'])
        if 'clevis' in text:
            score += 24
        if 'slider' in text:
            score -= 30
        if side == 'left' and any(tag in text for tag in (' left ', 'driver', ' lt ')):
            score += 14
        if side == 'right' and any(tag in text for tag in (' right ', 'passenger', ' rt ')):
            score += 14
        if position == 'inner' and any(tag in text for tag in (' inner ', ' inboard ')):
            score += 14
        if position == 'outer' and any(tag in text for tag in (' outer ', ' outboard ')):
            score += 14
        if any(tag in text for tag in (' fz ', ' force z', 'axial', 'compression', 'load')):
            score += 12
        unit_norm = unit.lower().replace(' ', '')
        if any(tag in unit_norm for tag in ('n', 'kn', 'lbf', 'lb')):
            score += 4
        return score

    def _auto_pick_tibia_channels(self):
        channels = list(self.current_available_channels or self._candidate_channels_for_active_slot())
        if not channels:
            return {
                'left_knee_clevis_inner_fz': '', 'left_knee_clevis_outer_fz': '',
                'left_upper_fx': '',
                'left_upper_fz': '', 'left_upper_mx': '', 'left_upper_my': '',
                'left_lower_fx': '',
                'left_lower_fz': '', 'left_lower_mx': '', 'left_lower_my': '',
                'right_knee_clevis_inner_fz': '', 'right_knee_clevis_outer_fz': '',
                'right_upper_fx': '',
                'right_upper_fz': '', 'right_upper_mx': '', 'right_upper_my': '',
                'right_lower_fx': '',
                'right_lower_fz': '', 'right_lower_mx': '', 'right_lower_my': '',
            }
        selected = {}
        used = set()
        for side in ('left', 'right'):
            for position in ('inner', 'outer'):
                key = f'{side}_knee_clevis_{position}_fz'
                best = ''
                best_score = -10**9
                for ch in channels:
                    if ch in used:
                        continue
                    score = self._score_tibia_clevis_channel(ch, side=side, position=position)
                    if score > best_score:
                        best = ch
                        best_score = score
                if best and best_score > 0 and self._channel_matches_input_spec(best, 'tibia', key):
                    selected[key] = best
                    used.add(best)
                else:
                    # Strict ISOCODE-first policy: knee clevis must remain blank when no true CLEV channel exists.
                    # Do not fall back to knee slider channels.
                    selected[key] = ''
        for side, level in (('left', 'upper'), ('left', 'lower'), ('right', 'upper'), ('right', 'lower')):
            for component in ('fx', 'fz', 'mx', 'my'):
                key = f'{side}_{level}_{component}'
                best = ''
                best_score = -10**9
                for ch in channels:
                    if ch in used:
                        continue
                    score = self._score_tibia_channel(ch, side=side, level=level, component=component)
                    if score > best_score:
                        best = ch
                        best_score = score
                if best and best_score > 0 and self._channel_matches_input_spec(best, 'tibia', key):
                    selected[key] = best
                    used.add(best)
                else:
                    # Strict structured-match policy: tibia roles must stay blank when no true tibia channel exists.
                    # Do not fall back to femur/neck/knee slider or loose text matches.
                    selected[key] = ''
        return selected

    def _compute_auto_pick_for_active_slot(self):
        if self.initial_mode == 'hic':
            return self._auto_pick_head_channels()
        if self.initial_mode == 'nij':
            return self._auto_pick_neck_channels()
        if self.initial_mode == 'chest':
            return self._auto_pick_chest_channels()
        if self.initial_mode == 'pelvis':
            return self._auto_pick_pelvis_channels()
        if self.initial_mode == 'femur':
            return self._auto_pick_femur_channels()
        if self.initial_mode == 'knee':
            return self._auto_pick_knee_channels()
        if self.initial_mode == 'iliac':
            return self._auto_pick_iliac_channels()
        return self._auto_pick_tibia_channels()

    def _merge_existing_with_auto_pick(self, existing, auto_pick):
        existing = dict(existing or {})
        auto_pick = dict(auto_pick or {})
        merged = {}
        mode_key = str(self.initial_mode or '').strip()
        for key, auto_channel in auto_pick.items():
            current = str(existing.get(key) or '').strip()
            strict_blank = self._is_strict_blank_role(mode_key, key)
            current_valid = bool(current and current in (self.current_available_channels or []) and self._channel_matches_input_spec(current, mode_key, key))
            auto_valid = bool(auto_channel and auto_channel in (self.current_available_channels or []) and self._channel_matches_input_spec(auto_channel, mode_key, key))
            if not current:
                merged[key] = auto_channel if auto_valid else ''
                continue
            if not current_valid:
                if auto_valid:
                    merged[key] = auto_channel
                else:
                    merged[key] = '' if strict_blank else current
                continue
            if not auto_valid:
                merged[key] = '' if strict_blank else current
                continue
            current_filter = self._channel_filter_code(current)
            auto_filter = self._channel_filter_code(auto_channel)
            # Prefer auto-picked channel when it upgrades to a filtered channel or when the channel identity differs.
            if current != auto_channel and current_filter in ('0', 'P', '') and auto_filter in FILTERED_ISOCODE_CODES:
                merged[key] = auto_channel
            else:
                merged[key] = current
        for key, value in existing.items():
            merged.setdefault(key, value)
        return merged

    def apply_auto_guess_for_active_slot(self, auto_pick=None):
        viewer = self.workbench.viewer
        if viewer.df is None:
            return
        slot = self._active_slot()
        if self._is_placeholder_slot(slot):
            self._clear_channel_selections()
            defaults = (
                {'x': '', 'y': '', 'z': ''} if self.initial_mode in ('hic', 'pelvis')
                else {'Fx': '', 'Fy': '', 'Fz': '', 'Mx': '', 'My': '', 'Mz': ''} if self.initial_mode == 'nij'
                else {'x': '', 'y': '', 'z': '', 'disp': ''} if self.initial_mode == 'chest'
                else {'left': '', 'right': ''} if self.initial_mode in ('femur', 'knee')
                else {'left_fx': '', 'left_my': '', 'right_fx': '', 'right_my': ''} if self.initial_mode == 'iliac'
                else {
                    'left_knee_clevis_inner_fz': '', 'left_knee_clevis_outer_fz': '',
                    'left_upper_fx': '',
                    'left_upper_fz': '', 'left_upper_mx': '', 'left_upper_my': '',
                    'left_lower_fx': '',
                    'left_lower_fz': '', 'left_lower_mx': '', 'left_lower_my': '',
                    'right_knee_clevis_inner_fz': '', 'right_knee_clevis_outer_fz': '',
                    'right_upper_fx': '',
                    'right_upper_fz': '', 'right_upper_mx': '', 'right_upper_my': '',
                    'right_lower_fx': '',
                    'right_lower_fz': '', 'right_lower_mx': '', 'right_lower_my': '',
                }
            )
            self.slot_states[slot]['channels'] = defaults
            if hasattr(self.workbench, 'add_history_entry'):
                self._log_history('Channel auto-assignment skipped for empty dummy position', event_type='auto_assign', slot=slot, persist=True)
            return
        auto_pick = dict(auto_pick or self._compute_auto_pick_for_active_slot() or {})
        if self.initial_mode == 'hic':
            head_pick = auto_pick
            x = head_pick.get('x', '')
            y = head_pick.get('y', '')
            z = head_pick.get('z', '')
            self._set_var_from_channel(self.hic_x_var, x)
            self._set_var_from_channel(self.hic_y_var, y)
            self._set_var_from_channel(self.hic_z_var, z)
            self.slot_states[slot]['channels'] = {'x': x, 'y': y, 'z': z}
        elif self.initial_mode == 'nij':
            neck_pick = auto_pick
            fx = neck_pick.get('Fx', '')
            fy = neck_pick.get('Fy', '')
            fz = neck_pick.get('Fz', '')
            mx = neck_pick.get('Mx', '')
            my = neck_pick.get('My', '')
            mz = neck_pick.get('Mz', '')
            self._set_var_from_channel(self.nij_fx_var, fx)
            self._set_var_from_channel(self.nij_fy_var, fy)
            self._set_var_from_channel(self.nij_fz_var, fz)
            self._set_var_from_channel(self.nij_mx_var, mx)
            self._set_var_from_channel(self.nij_my_var, my)
            self._set_var_from_channel(self.nij_mz_var, mz)
            self.slot_states[slot]['channels'] = {'Fx': fx, 'Fy': fy, 'Fz': fz, 'Mx': mx, 'My': my, 'Mz': mz}
        elif self.initial_mode == 'chest':
            chest_pick = auto_pick
            self._set_var_from_channel(self.chest_x_var, chest_pick.get('x', ''))
            self._set_var_from_channel(self.chest_y_var, chest_pick.get('y', ''))
            self._set_var_from_channel(self.chest_z_var, chest_pick.get('z', ''))
            self._set_var_from_channel(self.chest_disp_var, chest_pick.get('disp', ''))
            self.slot_states[slot]['channels'] = chest_pick
        elif self.initial_mode == 'pelvis':
            pelvis_pick = auto_pick
            self._set_var_from_channel(self.pelvis_x_var, pelvis_pick.get('x', ''))
            self._set_var_from_channel(self.pelvis_y_var, pelvis_pick.get('y', ''))
            self._set_var_from_channel(self.pelvis_z_var, pelvis_pick.get('z', ''))
            self.slot_states[slot]['channels'] = pelvis_pick
        elif self.initial_mode == 'femur':
            femur_pick = auto_pick
            self._set_var_from_channel(self.femur_left_var, femur_pick.get('left', ''))
            self._set_var_from_channel(self.femur_right_var, femur_pick.get('right', ''))
            self.slot_states[slot]['channels'] = femur_pick
        elif self.initial_mode == 'knee':
            knee_pick = auto_pick
            left = knee_pick.get('left', '')
            right = knee_pick.get('right', '')
            self._set_var_from_channel(self.knee_left_var, left)
            self._set_var_from_channel(self.knee_right_var, right)
            self.slot_states[slot]['channels'] = {'left': left, 'right': right}
        elif self.initial_mode == 'iliac':
            iliac_pick = auto_pick
            left_fx = iliac_pick.get('left_fx', '')
            left_my = iliac_pick.get('left_my', '')
            right_fx = iliac_pick.get('right_fx', '')
            right_my = iliac_pick.get('right_my', '')
            self._set_var_from_channel(self.iliac_left_fx_var, left_fx)
            self._set_var_from_channel(self.iliac_left_my_var, left_my)
            self._set_var_from_channel(self.iliac_right_fx_var, right_fx)
            self._set_var_from_channel(self.iliac_right_my_var, right_my)
            self.slot_states[slot]['channels'] = {'left_fx': left_fx, 'left_my': left_my, 'right_fx': right_fx, 'right_my': right_my}
        else:
            tibia_pick = auto_pick
            self._set_var_from_channel(self.tibia_left_knee_clevis_inner_fz_var, tibia_pick.get('left_knee_clevis_inner_fz', ''))
            self._set_var_from_channel(self.tibia_left_knee_clevis_outer_fz_var, tibia_pick.get('left_knee_clevis_outer_fz', ''))
            self._set_var_from_channel(self.tibia_left_upper_fx_var, tibia_pick.get('left_upper_fx', ''))
            self._set_var_from_channel(self.tibia_left_upper_fz_var, tibia_pick.get('left_upper_fz', ''))
            self._set_var_from_channel(self.tibia_left_upper_mx_var, tibia_pick.get('left_upper_mx', ''))
            self._set_var_from_channel(self.tibia_left_upper_my_var, tibia_pick.get('left_upper_my', ''))
            self._set_var_from_channel(self.tibia_left_lower_fx_var, tibia_pick.get('left_lower_fx', ''))
            self._set_var_from_channel(self.tibia_left_lower_fz_var, tibia_pick.get('left_lower_fz', ''))
            self._set_var_from_channel(self.tibia_left_lower_mx_var, tibia_pick.get('left_lower_mx', ''))
            self._set_var_from_channel(self.tibia_left_lower_my_var, tibia_pick.get('left_lower_my', ''))
            self._set_var_from_channel(self.tibia_right_knee_clevis_inner_fz_var, tibia_pick.get('right_knee_clevis_inner_fz', ''))
            self._set_var_from_channel(self.tibia_right_knee_clevis_outer_fz_var, tibia_pick.get('right_knee_clevis_outer_fz', ''))
            self._set_var_from_channel(self.tibia_right_upper_fx_var, tibia_pick.get('right_upper_fx', ''))
            self._set_var_from_channel(self.tibia_right_upper_fz_var, tibia_pick.get('right_upper_fz', ''))
            self._set_var_from_channel(self.tibia_right_upper_mx_var, tibia_pick.get('right_upper_mx', ''))
            self._set_var_from_channel(self.tibia_right_upper_my_var, tibia_pick.get('right_upper_my', ''))
            self._set_var_from_channel(self.tibia_right_lower_fx_var, tibia_pick.get('right_lower_fx', ''))
            self._set_var_from_channel(self.tibia_right_lower_fz_var, tibia_pick.get('right_lower_fz', ''))
            self._set_var_from_channel(self.tibia_right_lower_mx_var, tibia_pick.get('right_lower_mx', ''))
            self._set_var_from_channel(self.tibia_right_lower_my_var, tibia_pick.get('right_lower_my', ''))
            self.slot_states[slot]['channels'] = tibia_pick
        self._refresh_neck_guidance_text()
        assigned_count = sum(1 for _k, v in (self.slot_states[slot].get('channels') or {}).items() if v)
        self._log_history(f'Channel auto-assignment completed successfully ({assigned_count} channel(s))', event_type='auto_assign', slot=slot, persist=True)

    def calculate_pelvis_all(self):
        self._calculate_all_slots(self.calculate_pelvis)

    def calculate_knee_all(self):
        self._calculate_all_slots(self.calculate_knee)

    def calculate_iliac_all(self):
        self._calculate_all_slots(self.calculate_iliac)

    def calculate_tibia_all(self):
        self._calculate_all_slots(self.calculate_tibia)

    def _ensure_slot_plot_data(self, slot):
        state = self.slot_states.get(slot) or {}
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            return False
        try:
            if self.initial_mode == 'hic':
                if state.get('head_bundle'):
                    return True
                channels = dict(state.get('channels') or {})
                x_ch, y_ch, z_ch = channels.get('x'), channels.get('y'), channels.get('z')
                if not (x_ch and y_ch and z_ch):
                    return False
                time = self._get_time()
                x, _ = self._resolve_standard_series_for_calc(x_ch, 'head_injury', 'x', 1000, 1.0)
                y, _ = self._resolve_standard_series_for_calc(y_ch, 'head_injury', 'y', 1000, 1.0)
                z, _ = self._resolve_standard_series_for_calc(z_ch, 'head_injury', 'z', 1000, 1.0)
                resultant = compute_resultant_xyz(x, y, z)
                resultant_channel = self._head_resultant_channel_name(slot)
                result = build_head_injury_bundle(
                    time=time,
                    resultant_g=self._convert_resultant_to_g(resultant, (x_ch, y_ch, z_ch)),
                    x_plot=self._convert_channel_to_head_plot_unit(x, x_ch),
                    y_plot=self._convert_channel_to_head_plot_unit(y, y_ch),
                    z_plot=self._convert_channel_to_head_plot_unit(z, z_ch),
                    plot_unit=self._head_plot_unit((x_ch, y_ch, z_ch)),
                    channels=(x_ch, y_ch, z_ch),
                    resultant_channel=resultant_channel,
                    resultant_filter_label='CFC 1000',
                    use_high_res_cumulative_3ms=self._slot_use_high_res_cumulative_3ms(slot),
                )
                state['head_bundle'] = result['bundle']
                meta = dict(result.get('metadata') or {})
                meta['dummy_name'] = state.get('dummy_name') or ''
                meta['dummy_profile'] = state.get('dummy_profile') or ''
                meta['channels'] = dict(channels)
                meta['use_high_res_cumulative_3ms'] = self._slot_use_high_res_cumulative_3ms(slot)
                state['head_metadata'] = meta
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                state['use_high_res_cumulative_3ms'] = self._slot_use_high_res_cumulative_3ms(slot)
                return True

            if self.initial_mode == 'nij':
                if state.get('neck_metrics'):
                    return True
                selected = dict(state.get('channels') or {})
                if not selected.get('Fz') or not selected.get('My'):
                    return False
                neg_flags = dict(state.get('neg_flags') or {})
                sign_flags = {key: (-1.0 if bool(neg_flags.get(key, False)) else 1.0) for key in ('Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz')}
                result = calculate_neck_injury_bundle(
                    time=self._get_time(),
                    selected=selected,
                    sign_flags=sign_flags,
                    viewer=viewer,
                    criterion_key=state.get('dummy_profile') or self.nij_dummy_var.get(),
                    unit_getter=self._unit_text,
                    channel_desc_getter=lambda ch: viewer.get_channel_display_name(ch) if ch else '-',
                    resolve_series_for_calc=lambda source_channel, role, desired_cfc, sign: self._resolve_standard_series_for_calc(source_channel, 'neck_injury', role, desired_cfc, sign),
                )
                state['neck_metrics'] = result['metrics']
                if not state.get('neck_saved_payload'):
                    state['neck_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.nij_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(selected),
                        'neg_flags': dict(neg_flags),
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                return True

            if self.initial_mode == 'chest':
                if state.get('chest_metrics'):
                    return True
                channels = dict(state.get('channels') or {})
                x_ch, y_ch, z_ch, disp_ch = channels.get('x'), channels.get('y'), channels.get('z'), channels.get('disp')
                if not all((x_ch, y_ch, z_ch, disp_ch)):
                    return False
                raw_disp_series = self._align_original_series(disp_ch)
                if raw_disp_series is not None:
                    raw_disp_series = np.asarray(raw_disp_series, dtype=float)
                raw_accel_series = {'x': self._align_original_series(x_ch), 'y': self._align_original_series(y_ch), 'z': self._align_original_series(z_ch)}
                raw_accel_series = {k: (None if v is None else np.asarray(v, dtype=float)) for k, v in raw_accel_series.items()}
                disp_prefiltered = {k: np.asarray(v, dtype=float) for k, v in dict(self._collect_chest_disp_prefiltered(disp_ch) or {}).items()}
                x_calc, used_x = self._resolve_standard_series_for_calc(x_ch, 'chest_injury', 'x', 180, 1.0)
                y_calc, used_y = self._resolve_standard_series_for_calc(y_ch, 'chest_injury', 'y', 180, 1.0)
                z_calc, used_z = self._resolve_standard_series_for_calc(z_ch, 'chest_injury', 'z', 180, 1.0)
                disp_calc = np.asarray(viewer.get_numeric_column(disp_ch), dtype=float)
                result = calculate_chest_injury_bundle(
                    time=self._get_time(),
                    x_values=np.asarray(x_calc, dtype=float),
                    y_values=np.asarray(y_calc, dtype=float),
                    z_values=np.asarray(z_calc, dtype=float),
                    disp_values=disp_calc,
                    accel_units={'x': self._unit_text(x_ch), 'y': self._unit_text(y_ch), 'z': self._unit_text(z_ch)},
                    disp_unit=self._unit_text(disp_ch),
                    criterion_key=state.get('dummy_profile') or self.chest_dummy_var.get(),
                    raw_displacement=raw_disp_series,
                    raw_accel=raw_accel_series,
                    accel_filter_labels={
                        'x': self._channel_filter_label_for_calc(x_ch, used_x),
                        'y': self._channel_filter_label_for_calc(y_ch, used_y),
                        'z': self._channel_filter_label_for_calc(z_ch, used_z),
                    },
                    disp_filter_label=self._channel_filter_label_for_calc(disp_ch),
                    disp_prefiltered=disp_prefiltered,
                    vc_sign_pref=1.0,
                    use_high_res_cumulative_3ms=self._slot_use_high_res_cumulative_3ms(slot),
                )
                state['chest_metrics'] = result['metrics']
                state['use_high_res_cumulative_3ms'] = self._slot_use_high_res_cumulative_3ms(slot)
                if not state.get('chest_saved_payload'):
                    rp = result['metrics'].get('resultant_peak', {})
                    state['chest_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.chest_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(channels),
                        'neg_flags': {},
                        'use_high_res_cumulative_3ms': state['use_high_res_cumulative_3ms'],
                        'resultant_peak_g': float(rp['value']) if rp.get('value') is not None else None,
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = state.get('summary_text') or result.get('summary_text') or '-'
                return True

            if self.initial_mode == 'pelvis':
                if state.get('pelvis_metrics'):
                    return True
                channels = dict(state.get('channels') or {})
                x_ch, y_ch, z_ch = channels.get('x'), channels.get('y'), channels.get('z')
                if not (x_ch and y_ch and z_ch):
                    return False
                time = self._get_time()
                x_values, _ = self._resolve_standard_series_for_calc(x_ch, 'pelvis_injury', 'x', 1000, 1.0)
                y_values, _ = self._resolve_standard_series_for_calc(y_ch, 'pelvis_injury', 'y', 1000, 1.0)
                z_values, _ = self._resolve_standard_series_for_calc(z_ch, 'pelvis_injury', 'z', 1000, 1.0)
                plot_unit = self._head_plot_unit((x_ch, y_ch, z_ch))
                result = calculate_pelvis_injury_bundle(
                    time=time,
                    x_values=self._convert_channel_to_head_plot_unit(x_values, x_ch),
                    y_values=self._convert_channel_to_head_plot_unit(y_values, y_ch),
                    z_values=self._convert_channel_to_head_plot_unit(z_values, z_ch),
                    plot_unit=plot_unit,
                    use_high_res_cumulative_3ms=self._slot_use_high_res_cumulative_3ms(slot),
                )
                state['pelvis_metrics'] = result['metrics']
                state['use_high_res_cumulative_3ms'] = self._slot_use_high_res_cumulative_3ms(slot)
                if not state.get('pelvis_saved_payload'):
                    state['pelvis_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.pelvis_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(channels),
                        'neg_flags': {},
                        'use_high_res_cumulative_3ms': state['use_high_res_cumulative_3ms'],
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                return True

            if self.initial_mode == 'femur':
                if state.get('femur_metrics'):
                    return True
                channels = dict(state.get('channels') or {})
                left_ch, right_ch = channels.get('left'), channels.get('right')
                if not (left_ch and right_ch):
                    return False
                left_force, _ = self._resolve_standard_series_for_calc(left_ch, 'femur_injury', 'left', 600, 1.0)
                right_force, _ = self._resolve_standard_series_for_calc(right_ch, 'femur_injury', 'right', 600, 1.0)
                result = calculate_femur_injury_bundle(
                    time=self._get_time(),
                    left_force=np.asarray(left_force, dtype=float),
                    right_force=np.asarray(right_force, dtype=float),
                    criterion_key=state.get('dummy_profile') or self.femur_dummy_var.get(),
                    left_unit=self._unit_text(left_ch),
                    right_unit=self._unit_text(right_ch),
                )
                state['femur_metrics'] = result['metrics']
                if not state.get('femur_saved_payload'):
                    state['femur_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.femur_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(channels),
                        'neg_flags': {},
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                return True

            if self.initial_mode == 'knee':
                if state.get('knee_metrics'):
                    return True
                channels = dict(state.get('channels') or {})
                left_ch, right_ch = channels.get('left'), channels.get('right')
                if not (left_ch and right_ch):
                    return False
                result = calculate_knee_injury_bundle(
                    time=self._get_time(),
                    left_slider=np.asarray(viewer.get_numeric_column(left_ch), dtype=float),
                    right_slider=np.asarray(viewer.get_numeric_column(right_ch), dtype=float),
                    left_unit=self._unit_text(left_ch),
                    right_unit=self._unit_text(right_ch),
                )
                state['knee_metrics'] = result['metrics']
                if not state.get('knee_saved_payload'):
                    state['knee_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(channels),
                        'neg_flags': {},
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                return True

            if self.initial_mode == 'iliac':
                if state.get('iliac_metrics'):
                    return True
                channels = dict(state.get('channels') or {})
                left_fx_ch = channels.get('left_fx')
                left_my_ch = channels.get('left_my')
                right_fx_ch = channels.get('right_fx')
                right_my_ch = channels.get('right_my')
                if not all((left_fx_ch, left_my_ch, right_fx_ch, right_my_ch)):
                    return False
                result = calculate_iliac_injury_bundle(
                    time=self._get_time(),
                    left_fx=np.asarray(viewer.get_numeric_column(left_fx_ch), dtype=float),
                    left_my=np.asarray(viewer.get_numeric_column(left_my_ch), dtype=float),
                    right_fx=np.asarray(viewer.get_numeric_column(right_fx_ch), dtype=float),
                    right_my=np.asarray(viewer.get_numeric_column(right_my_ch), dtype=float),
                    left_fx_unit=self._unit_text(left_fx_ch),
                    left_my_unit=self._unit_text(left_my_ch),
                    right_fx_unit=self._unit_text(right_fx_ch),
                    right_my_unit=self._unit_text(right_my_ch),
                    criterion_key=state.get('dummy_profile') or self.iliac_dummy_var.get(),
                )
                state['iliac_metrics'] = result['metrics']
                if not state.get('iliac_saved_payload'):
                    state['iliac_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.iliac_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(channels),
                        'neg_flags': {},
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                return True

            if self.initial_mode == 'tibia':
                if state.get('tibia_metrics'):
                    return True
                channels = dict(state.get('channels') or {})
                required_keys = (
                    'left_upper_fz', 'left_upper_mx', 'left_upper_my',
                    'left_lower_fz', 'left_lower_mx', 'left_lower_my',
                    'right_upper_fz', 'right_upper_mx', 'right_upper_my',
                    'right_lower_fz', 'right_lower_mx', 'right_lower_my',
                )
                if not all(channels.get(key) for key in required_keys):
                    return False
                units = {key: self._unit_text(channels.get(key)) for key in required_keys}
                result = calculate_tibia_injury_bundle(
                    time=self._get_time(),
                    left_upper_fz=np.asarray(viewer.get_numeric_column(channels['left_upper_fz']), dtype=float),
                    left_upper_mx=np.asarray(viewer.get_numeric_column(channels['left_upper_mx']), dtype=float),
                    left_upper_my=np.asarray(viewer.get_numeric_column(channels['left_upper_my']), dtype=float),
                    left_lower_fz=np.asarray(viewer.get_numeric_column(channels['left_lower_fz']), dtype=float),
                    left_lower_mx=np.asarray(viewer.get_numeric_column(channels['left_lower_mx']), dtype=float),
                    left_lower_my=np.asarray(viewer.get_numeric_column(channels['left_lower_my']), dtype=float),
                    right_upper_fz=np.asarray(viewer.get_numeric_column(channels['right_upper_fz']), dtype=float),
                    right_upper_mx=np.asarray(viewer.get_numeric_column(channels['right_upper_mx']), dtype=float),
                    right_upper_my=np.asarray(viewer.get_numeric_column(channels['right_upper_my']), dtype=float),
                    right_lower_fz=np.asarray(viewer.get_numeric_column(channels['right_lower_fz']), dtype=float),
                    right_lower_mx=np.asarray(viewer.get_numeric_column(channels['right_lower_mx']), dtype=float),
                    right_lower_my=np.asarray(viewer.get_numeric_column(channels['right_lower_my']), dtype=float),
                    criterion_key=state.get('dummy_profile') or self.tibia_dummy_var.get(),
                    units=units,
                )
                state['tibia_metrics'] = result['metrics']
                if not state.get('tibia_saved_payload'):
                    state['tibia_saved_payload'] = {
                        'result_uid': state.get('result_uid') or self._injury_result_uid(slot),
                        'summary_text': result['summary_text'],
                        'criterion_key': state.get('dummy_profile') or self.tibia_dummy_var.get(),
                        'dummy_name': state.get('dummy_name') or '',
                        'dummy_profile': state.get('dummy_profile') or '',
                        'channels': dict(channels),
                        'neg_flags': {},
                        'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
                    }
                state['summary_text'] = result.get('summary_text') or state.get('summary_text') or '-'
                return True
        except Exception:
            return False

    def _show_saved_graph_for_slot(self, slot, graph_key):
        if not self._ensure_slot_plot_data(slot):
            return
        if self.initial_mode == 'hic':
            self.show_hic_bundle_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'nij':
            self.show_neck_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'chest':
            self.show_chest_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'pelvis':
            self.show_pelvis_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'femur':
            self.show_femur_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'knee':
            self.show_knee_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'iliac':
            self.show_iliac_graph(graph_key, slot=slot, silent=True)
        elif self.initial_mode == 'tibia':
            self.show_tibia_graph(graph_key, slot=slot, silent=True)

    def calculate_pelvis(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('\uacbd\uace0', '\uba3c\uc800 DAT \ub370\uc774\ud130\ub97c \ub85c\ub4dc\ud574\uc8fc\uc138\uc694.')
            return
        if not self._confirm_missing_dummy_profile():
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        try:
            x_ch = self._selected_channel(self.pelvis_x_var)
            y_ch = self._selected_channel(self.pelvis_y_var)
            z_ch = self._selected_channel(self.pelvis_z_var)
            if not all((x_ch, y_ch, z_ch)):
                raise ValueError('PELVIS \uacc4\uc0b0\uc5d0\ub294 X/Y/Z \uac00\uc18d\ub3c4 \ucc44\ub110\uc774 \ubaa8\ub450 \ud544\uc694\ud569\ub2c8\ub2e4.')
            time = self._get_time()
            x_values, _ = self._resolve_standard_series_for_calc(x_ch, 'pelvis_injury', 'x', 1000, 1.0)
            y_values, _ = self._resolve_standard_series_for_calc(y_ch, 'pelvis_injury', 'y', 1000, 1.0)
            z_values, _ = self._resolve_standard_series_for_calc(z_ch, 'pelvis_injury', 'z', 1000, 1.0)
            result = calculate_pelvis_injury_bundle(
                time=time,
                x_values=self._convert_channel_to_head_plot_unit(x_values, x_ch),
                y_values=self._convert_channel_to_head_plot_unit(y_values, y_ch),
                z_values=self._convert_channel_to_head_plot_unit(z_values, z_ch),
                plot_unit=self._head_plot_unit((x_ch, y_ch, z_ch)),
                use_high_res_cumulative_3ms=self._current_use_high_res_cumulative_3ms(),
            )
            metrics = result['metrics']
            st = self.slot_states[slot]
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
            st['channels'] = {'x': x_ch, 'y': y_ch, 'z': z_ch}
            st['neg_flags'] = {}
            st['summary_text'] = result['summary_text']
            st['result_uid'] = st.get('result_uid') or self._injury_result_uid(slot)
            st['pelvis_metrics'] = metrics
            st['use_high_res_cumulative_3ms'] = self._current_use_high_res_cumulative_3ms()
            st['pelvis_saved_payload'] = {
                'result_uid': st['result_uid'],
                'summary_text': result['summary_text'],
                'criterion_key': self.pelvis_dummy_var.get(),
                'dummy_name': st['dummy_name'],
                'dummy_profile': st['dummy_profile'],
                'channels': dict(st['channels']),
                'neg_flags': {},
                'use_high_res_cumulative_3ms': st['use_high_res_cumulative_3ms'],
                'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
            }
            preferred_graph_key = self._default_graph_key('accel_resultant')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['pelvis_saved_payload']['graph_key'] = st['graph_key']
            st['pelvis_saved_payload']['graph_uid'] = st['graph_uid']
            self._apply_summary_text(result['summary_text'])
            self._save_section_payload(
                {
                    'type': 'injury_calculation',
                    'section': 'PELVIS',
                    'slot': slot,
                    'dummy_position': slot,
                    'result_uid': st['result_uid'],
                    'graph_uid': st.get('graph_uid'),
                    'message': 'Pelvis injury calculated',
                    'display_message': 'Pelvis injury calculated successfully',
                }
            )
            self.show_pelvis_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('\uacbd\uace0', str(exc))

    def show_pelvis_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('pelvis_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('\uacbd\uace0', '\uba3c\uc800 PELVIS \uacc4\uc0b0\uc744 \uc2e4\ud589\ud574\uc8fc\uc138\uc694.')
            return
        self._plot_pelvis_resultant(metrics, slot)
        self.slot_states[slot]['graph_key'] = 'accel_resultant'
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, 'accel_resultant')
        self._select_graph_tab('accel_resultant')
        if not silent:
            self._record_graph_selection(slot, 'accel_resultant')

    def _plot_pelvis_resultant(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        for label, arr, width in (
            ('PELVIS X', np.asarray(metrics.get('x_plot', []), dtype=float), 1.0),
            ('PELVIS Y', np.asarray(metrics.get('y_plot', []), dtype=float), 1.0),
            ('PELVIS Z', np.asarray(metrics.get('z_plot', []), dtype=float), 1.0),
            ('PELVIS RES', np.asarray(metrics.get('resultant', []), dtype=float), 1.6),
        ):
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)
        self.ax.set_title(f"INJURY - PELVIS ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Acceleration ({metrics.get('plot_unit') or 'g'})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Pelvis_Resultant_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _apply_zero_centered_kn_ylim(self, *series_list):
        finite_values = []
        for series in series_list:
            arr = np.asarray(series, dtype=float)
            vals = arr[np.isfinite(arr)]
            if vals.size:
                finite_values.append(vals)
        if not finite_values:
            return
        combined = np.concatenate(finite_values)
        data_min = min(float(np.nanmin(combined)), 0.0)
        data_max = max(float(np.nanmax(combined)), 0.0)
        pos_span = max(data_max, 0.0)
        neg_span = max(abs(data_min), 0.0)
        pos_pad = max(0.05 * pos_span, 0.02) if pos_span > 0.0 else 0.1
        neg_pad = max(0.05 * neg_span, 0.02) if neg_span > 0.0 else 0.1
        y_min = -neg_span - neg_pad if neg_span > 0.0 else -neg_pad
        y_max = pos_span + pos_pad if pos_span > 0.0 else pos_pad
        if y_min >= y_max:
            y_min, y_max = -1.0, 1.0
        self.ax.set_ylim(y_min, y_max)

    def calculate_knee(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('경고', '먼저 DAT 데이터를 로드하세요.')
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        left_ch = self._selected_channel(self.knee_left_var)
        right_ch = self._selected_channel(self.knee_right_var)
        if not (left_ch and right_ch):
            messagebox.showwarning('경고', 'KNEE 계산에는 Left/Right knee slider 채널이 모두 필요합니다.')
            return
        try:
            result = calculate_knee_injury_bundle(
                time=self._get_time(),
                left_slider=np.asarray(viewer.get_numeric_column(left_ch), dtype=float),
                right_slider=np.asarray(viewer.get_numeric_column(right_ch), dtype=float),
                left_unit=self._unit_text(left_ch),
                right_unit=self._unit_text(right_ch),
            )
            metrics = result['metrics']
            st = self.slot_states[slot]
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = self.multi_dummy_panel.profile_var(slot).get().strip()
            st['channels'] = {'left': left_ch, 'right': right_ch}
            st['neg_flags'] = {}
            st['summary_text'] = result['summary_text']
            st['result_uid'] = st.get('result_uid') or self._injury_result_uid(slot)
            st['knee_metrics'] = metrics
            st['knee_saved_payload'] = {
                'result_uid': st['result_uid'],
                'summary_text': result['summary_text'],
                'dummy_name': st['dummy_name'],
                'dummy_profile': st['dummy_profile'],
                'channels': dict(st['channels']),
                'neg_flags': {},
                'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
            }
            preferred_graph_key = self._default_graph_key('combined')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['knee_saved_payload']['graph_key'] = st['graph_key']
            st['knee_saved_payload']['graph_uid'] = st['graph_uid']
            self._apply_summary_text(result['summary_text'])
            self._save_section_payload(
                {
                    'type': 'injury_calculation',
                    'section': 'KNEE',
                    'slot': slot,
                    'dummy_position': slot,
                    'result_uid': st['result_uid'],
                    'graph_uid': st.get('graph_uid'),
                    'message': 'Knee slider calculated',
                    'display_message': 'Knee slider calculated successfully',
                }
            )
            self.show_knee_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('경고', str(exc))

    def calculate_iliac(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('경고', '먼저 DAT 데이터를 로드하세요.')
            return
        if not self._confirm_missing_dummy_profile():
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        left_fx_ch = self._selected_channel(self.iliac_left_fx_var)
        left_my_ch = self._selected_channel(self.iliac_left_my_var)
        right_fx_ch = self._selected_channel(self.iliac_right_fx_var)
        right_my_ch = self._selected_channel(self.iliac_right_my_var)
        if not all((left_fx_ch, left_my_ch, right_fx_ch, right_my_ch)):
            messagebox.showwarning('경고', 'ILIAC 계산에는 Left/Right Fx/My 채널이 모두 필요합니다.')
            return
        try:
            st = self.slot_states[slot]
            criterion_key = (self.multi_dummy_panel.profile_var(slot).get().strip() or self.iliac_dummy_var.get().strip() or 'THOR_50M_ASIS')
            result = calculate_iliac_injury_bundle(
                time=self._get_time(),
                left_fx=np.asarray(viewer.get_numeric_column(left_fx_ch), dtype=float),
                left_my=np.asarray(viewer.get_numeric_column(left_my_ch), dtype=float),
                right_fx=np.asarray(viewer.get_numeric_column(right_fx_ch), dtype=float),
                right_my=np.asarray(viewer.get_numeric_column(right_my_ch), dtype=float),
                left_fx_unit=self._unit_text(left_fx_ch),
                left_my_unit=self._unit_text(left_my_ch),
                right_fx_unit=self._unit_text(right_fx_ch),
                right_my_unit=self._unit_text(right_my_ch),
                criterion_key=criterion_key,
            )
            metrics = result['metrics']
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = criterion_key
            st['channels'] = {'left_fx': left_fx_ch, 'left_my': left_my_ch, 'right_fx': right_fx_ch, 'right_my': right_my_ch}
            st['neg_flags'] = {}
            st['summary_text'] = result['summary_text']
            st['result_uid'] = st.get('result_uid') or self._injury_result_uid(slot)
            st['iliac_metrics'] = metrics
            st['iliac_saved_payload'] = {
                'result_uid': st['result_uid'],
                'summary_text': result['summary_text'],
                'criterion_key': criterion_key,
                'dummy_name': st['dummy_name'],
                'dummy_profile': st['dummy_profile'],
                'channels': dict(st['channels']),
                'neg_flags': {},
                'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
            }
            preferred_graph_key = self._default_graph_key('force')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['iliac_saved_payload']['graph_key'] = st['graph_key']
            st['iliac_saved_payload']['graph_uid'] = st['graph_uid']
            self._apply_summary_text(result['summary_text'])
            self._save_section_payload(
                {
                    'type': 'injury_calculation',
                    'section': 'ILIAC',
                    'slot': slot,
                    'dummy_position': slot,
                    'result_uid': st['result_uid'],
                    'graph_uid': st.get('graph_uid'),
                    'message': 'Iliac injury calculated',
                    'display_message': 'Iliac injury calculated successfully',
                }
            )
            self.show_iliac_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('경고', str(exc))

    def calculate_tibia(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning('경고', '먼저 DAT 데이터를 로드하세요.')
            return
        if not self._confirm_missing_dummy_profile():
            return
        slot = self._active_slot()
        self._save_active_slot_state()
        channel_map = {
            'left_knee_clevis_inner_fz': self._selected_channel(self.tibia_left_knee_clevis_inner_fz_var),
            'left_knee_clevis_outer_fz': self._selected_channel(self.tibia_left_knee_clevis_outer_fz_var),
            'left_upper_fx': self._selected_channel(self.tibia_left_upper_fx_var),
            'left_upper_fz': self._selected_channel(self.tibia_left_upper_fz_var),
            'left_upper_mx': self._selected_channel(self.tibia_left_upper_mx_var),
            'left_upper_my': self._selected_channel(self.tibia_left_upper_my_var),
            'left_lower_fx': self._selected_channel(self.tibia_left_lower_fx_var),
            'left_lower_fz': self._selected_channel(self.tibia_left_lower_fz_var),
            'left_lower_mx': self._selected_channel(self.tibia_left_lower_mx_var),
            'left_lower_my': self._selected_channel(self.tibia_left_lower_my_var),
            'right_knee_clevis_inner_fz': self._selected_channel(self.tibia_right_knee_clevis_inner_fz_var),
            'right_knee_clevis_outer_fz': self._selected_channel(self.tibia_right_knee_clevis_outer_fz_var),
            'right_upper_fx': self._selected_channel(self.tibia_right_upper_fx_var),
            'right_upper_fz': self._selected_channel(self.tibia_right_upper_fz_var),
            'right_upper_mx': self._selected_channel(self.tibia_right_upper_mx_var),
            'right_upper_my': self._selected_channel(self.tibia_right_upper_my_var),
            'right_lower_fx': self._selected_channel(self.tibia_right_lower_fx_var),
            'right_lower_fz': self._selected_channel(self.tibia_right_lower_fz_var),
            'right_lower_mx': self._selected_channel(self.tibia_right_lower_mx_var),
            'right_lower_my': self._selected_channel(self.tibia_right_lower_my_var),
        }
        required_keys = (
            'left_upper_fz', 'left_upper_mx', 'left_upper_my',
            'left_lower_fz', 'left_lower_mx', 'left_lower_my',
            'right_upper_fz', 'right_upper_mx', 'right_upper_my',
            'right_lower_fz', 'right_lower_mx', 'right_lower_my',
        )
        if not all(channel_map[key] for key in required_keys):
            messagebox.showwarning('경고', 'TIBIA 계산에는 좌/우 upper/lower Fz, Mx, My 채널이 모두 필요합니다.')
            return
        try:
            criterion_key = (self.multi_dummy_panel.profile_var(slot).get().strip() or self.tibia_dummy_var.get().strip() or 'H3_50M_EURO_NCAP')
            units = {key: self._unit_text(channel_map[key]) for key in channel_map}
            result = calculate_tibia_injury_bundle(
                time=self._get_time(),
                left_upper_fz=np.asarray(viewer.get_numeric_column(channel_map['left_upper_fz']), dtype=float),
                left_upper_mx=np.asarray(viewer.get_numeric_column(channel_map['left_upper_mx']), dtype=float),
                left_upper_my=np.asarray(viewer.get_numeric_column(channel_map['left_upper_my']), dtype=float),
                left_lower_fz=np.asarray(viewer.get_numeric_column(channel_map['left_lower_fz']), dtype=float),
                left_lower_mx=np.asarray(viewer.get_numeric_column(channel_map['left_lower_mx']), dtype=float),
                left_lower_my=np.asarray(viewer.get_numeric_column(channel_map['left_lower_my']), dtype=float),
                right_upper_fz=np.asarray(viewer.get_numeric_column(channel_map['right_upper_fz']), dtype=float),
                right_upper_mx=np.asarray(viewer.get_numeric_column(channel_map['right_upper_mx']), dtype=float),
                right_upper_my=np.asarray(viewer.get_numeric_column(channel_map['right_upper_my']), dtype=float),
                right_lower_fz=np.asarray(viewer.get_numeric_column(channel_map['right_lower_fz']), dtype=float),
                right_lower_mx=np.asarray(viewer.get_numeric_column(channel_map['right_lower_mx']), dtype=float),
                right_lower_my=np.asarray(viewer.get_numeric_column(channel_map['right_lower_my']), dtype=float),
                criterion_key=criterion_key,
                units=units,
            )
            metrics = result['metrics']
            st = self.slot_states[slot]
            st['dummy_name'] = self.multi_dummy_panel.name_var(slot).get().strip()
            st['dummy_profile'] = criterion_key
            st['channels'] = dict(channel_map)
            st['neg_flags'] = {}
            st['summary_text'] = result['summary_text']
            st['result_uid'] = st.get('result_uid') or self._injury_result_uid(slot)
            st['tibia_metrics'] = metrics
            st['tibia_saved_payload'] = {
                'result_uid': st['result_uid'],
                'summary_text': result['summary_text'],
                'criterion_key': criterion_key,
                'dummy_name': st['dummy_name'],
                'dummy_profile': st['dummy_profile'],
                'channels': dict(st['channels']),
                'neg_flags': {},
                'summary_format_version': result.get('summary_format_version') or SUMMARY_FORMAT_VERSION,
            }
            preferred_graph_key = self._default_graph_key('tibia_index')
            st['graph_key'] = preferred_graph_key
            st['graph_uid'] = self._injury_graph_uid(slot, preferred_graph_key)
            st['tibia_saved_payload']['graph_key'] = st['graph_key']
            st['tibia_saved_payload']['graph_uid'] = st['graph_uid']
            self._apply_summary_text(result['summary_text'])
            self._save_section_payload(
                {
                    'type': 'injury_calculation',
                    'section': 'TIBIA',
                    'slot': slot,
                    'dummy_position': slot,
                    'result_uid': st['result_uid'],
                    'graph_uid': st.get('graph_uid'),
                    'message': 'Tibia injury calculated',
                    'display_message': 'Tibia injury calculated successfully',
                }
            )
            self.show_tibia_graph(preferred_graph_key, slot=slot)
        except Exception as exc:
            messagebox.showwarning('경고', str(exc))

    def show_knee_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('knee_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('경고', '먼저 KNEE 계산을 실행하세요.')
            return
        self.ax.clear()
        t = np.asarray(metrics['time'], dtype=float)
        left = np.asarray(metrics.get('left_slider', []), dtype=float)
        right = np.asarray(metrics.get('right_slider', []), dtype=float)
        for label, arr, width in (('LEFT KNEE SLIDER', left, 1.4), ('RIGHT KNEE SLIDER', right, 1.4)):
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)
        self.ax.set_title(f"INJURY - KNEE ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Knee Slider ({metrics.get('plot_unit') or 'mm'})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Knee_Slider_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.slot_states[slot]['graph_key'] = 'combined'
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, 'combined')
        self._select_graph_tab('combined')
        if not silent:
            self._record_graph_selection(slot, 'combined')

    def show_femur_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('femur_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('\uacbd\uace0', '\uba3c\uc800 FEMUR \uacc4\uc0b0\uc744 \uc2e4\ud589\ud574\uc8fc\uc138\uc694.')
            return
        if mode == 'left':
            self._plot_femur_side(metrics, slot, 'left')
        elif mode == 'right':
            self._plot_femur_side(metrics, slot, 'right')
        else:
            self._plot_femur_combined(metrics, slot)
        self.slot_states[slot]['graph_key'] = mode
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, mode)
        self._select_graph_tab(mode)
        if not silent:
            self._record_graph_selection(slot, mode)

    def show_iliac_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('iliac_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('경고', '먼저 ILIAC 계산을 실행하세요.')
            return
        if mode == 'moment':
            self._plot_iliac_moment(metrics, slot)
        elif mode == 'crossplot':
            self._plot_iliac_crossplot(metrics, slot)
        else:
            self._plot_iliac_force(metrics, slot)
            mode = 'force'
        self.slot_states[slot]['graph_key'] = mode
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, mode)
        self._select_graph_tab(mode)
        if not silent:
            self._record_graph_selection(slot, mode)

    def show_tibia_graph(self, mode, slot=None, silent=False):
        slot = slot or self._active_slot()
        metrics = (self.slot_states.get(slot) or {}).get('tibia_metrics')
        if not metrics:
            if not silent:
                messagebox.showwarning('경고', '먼저 TIBIA 계산을 실행하세요.')
            return
        if mode == 'axial_force':
            self._plot_tibia_axial_force(metrics, slot)
        elif mode == 'moment_resultant':
            self._plot_tibia_moment_resultant(metrics, slot)
        else:
            self._plot_tibia_index(metrics, slot)
            mode = 'tibia_index'
        self.slot_states[slot]['graph_key'] = mode
        self.slot_states[slot]['graph_uid'] = self._injury_graph_uid(slot, mode)
        self._select_graph_tab(mode)
        if not silent:
            self._record_graph_selection(slot, mode)

    def _plot_iliac_force(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        for label, arr, width in (
            ('LEFT Fx', np.asarray(metrics.get('left_fx_n', []), dtype=float), 1.4),
            ('RIGHT Fx', np.asarray(metrics.get('right_fx_n', []), dtype=float), 1.4),
            ('LEFT √(Fx²+My²)', np.asarray(metrics.get('left_fx_my_resultant', []), dtype=float), 1.2),
            ('RIGHT √(Fx²+My²)', np.asarray(metrics.get('right_fx_my_resultant', []), dtype=float), 1.2),
        ):
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)
        self.ax.set_title(f"INJURY - ILIAC FORCE ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Force / Combined ({metrics.get('plot_force_unit') or 'N'})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Iliac_Force_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_tibia_index(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        curves = (
            ('LEFT UPPER TI', np.asarray(metrics.get('left_upper', {}).get('tibia_index', []), dtype=float)),
            ('LEFT LOWER TI', np.asarray(metrics.get('left_lower', {}).get('tibia_index', []), dtype=float)),
            ('RIGHT UPPER TI', np.asarray(metrics.get('right_upper', {}).get('tibia_index', []), dtype=float)),
            ('RIGHT LOWER TI', np.asarray(metrics.get('right_lower', {}).get('tibia_index', []), dtype=float)),
        )
        for label, arr in curves:
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.3, label=label)
        self.ax.axhline(float(metrics.get('ti_reference_line') or 1.0), color='#dc2626', linestyle='--', linewidth=1.0, label='TI Ref')
        self.ax.axhline(float(metrics.get('ti_secondary_line') or 1.3), color='#f59e0b', linestyle=':', linewidth=1.0, label='TI Secondary')
        self.ax.set_title(f"INJURY - TIBIA INDEX ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Tibia Index')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Tibia_Index_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_tibia_axial_force(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        curves = (
            ('LEFT UPPER Fz', -np.asarray(metrics.get('left_upper', {}).get('compressive_force_n', []), dtype=float) / 1000.0),
            ('LEFT LOWER Fz', -np.asarray(metrics.get('left_lower', {}).get('compressive_force_n', []), dtype=float) / 1000.0),
            ('RIGHT UPPER Fz', -np.asarray(metrics.get('right_upper', {}).get('compressive_force_n', []), dtype=float) / 1000.0),
            ('RIGHT LOWER Fz', -np.asarray(metrics.get('right_lower', {}).get('compressive_force_n', []), dtype=float) / 1000.0),
        )
        for label, arr in curves:
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.3, label=label)
        self._apply_zero_centered_kn_ylim(*(arr for _label, arr in curves))
        self.ax.set_title(f"INJURY - TIBIA AXIAL FORCE ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Compression Force (kN)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Tibia_Axial_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_tibia_moment_resultant(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        curves = (
            ('LEFT UPPER MR', np.asarray(metrics.get('left_upper', {}).get('moment_resultant_nm', []), dtype=float)),
            ('LEFT LOWER MR', np.asarray(metrics.get('left_lower', {}).get('moment_resultant_nm', []), dtype=float)),
            ('RIGHT UPPER MR', np.asarray(metrics.get('right_upper', {}).get('moment_resultant_nm', []), dtype=float)),
            ('RIGHT LOWER MR', np.asarray(metrics.get('right_lower', {}).get('moment_resultant_nm', []), dtype=float)),
        )
        for label, arr in curves:
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.3, label=label)
        limit = float(metrics.get('moment_crit_nm') or 0.0)
        if limit > 0.0:
            self.ax.axhline(limit, color='#dc2626', linestyle='--', linewidth=1.0, label='MR Critical')
        self.ax.set_title(f"INJURY - TIBIA MOMENT ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Moment Resultant (Nm)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Tibia_Moment_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_iliac_moment(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        self.ax.clear()
        for label, arr in (
            ('LEFT My', np.asarray(metrics.get('left_my_nm', []), dtype=float)),
            ('RIGHT My', np.asarray(metrics.get('right_my_nm', []), dtype=float)),
        ):
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.4, label=label)
        self.ax.set_title(f"INJURY - ILIAC MOMENT ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel(f"Moment ({metrics.get('plot_moment_unit') or 'Nm'})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Iliac_Moment_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_iliac_crossplot(self, metrics, slot):
        self.ax.clear()
        left_fx = np.asarray(metrics.get('left_fx_n', []), dtype=float)
        left_my = np.asarray(metrics.get('left_my_nm', []), dtype=float)
        right_fx = np.asarray(metrics.get('right_fx_n', []), dtype=float)
        right_my = np.asarray(metrics.get('right_my_nm', []), dtype=float)
        left_valid = np.isfinite(left_fx) & np.isfinite(left_my)
        right_valid = np.isfinite(right_fx) & np.isfinite(right_my)
        if np.any(left_valid):
            self.ax.plot(left_fx[left_valid], left_my[left_valid], linewidth=1.2, label='LEFT Fx-My')
        if np.any(right_valid):
            self.ax.plot(right_fx[right_valid], right_my[right_valid], linewidth=1.2, label='RIGHT Fx-My')
        self.ax.axhline(0.0, color='#9ca3af', linewidth=0.8)
        self.ax.axvline(0.0, color='#9ca3af', linewidth=0.8)
        self.ax.set_title(f"INJURY - ILIAC Fx-My ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(f"Fx ({metrics.get('plot_force_unit') or 'N'})")
        self.ax.set_ylabel(f"My ({metrics.get('plot_moment_unit') or 'Nm'})")
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Iliac_FxMy_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_femur_side(self, metrics, slot, side):
        t = np.asarray(metrics['time'], dtype=float)
        arr_kn = np.asarray(metrics.get(f'{side}_force_n', []), dtype=float) / 1000.0
        self.ax.clear()
        valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr_kn)
        if np.any(valid):
            self.ax.plot(t_plot[valid], v_plot[valid], linewidth=1.4, label=f'{side.upper()} FEMUR')
        self._apply_zero_centered_kn_ylim(arr_kn)
        self.ax.set_title(f"INJURY - FEMUR ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Force (kN)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Femur_{side.capitalize()}_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _plot_femur_combined(self, metrics, slot):
        t = np.asarray(metrics['time'], dtype=float)
        left_kn = np.asarray(metrics.get('left_force_n', []), dtype=float) / 1000.0
        right_kn = np.asarray(metrics.get('right_force_n', []), dtype=float) / 1000.0
        self.ax.clear()
        for label, arr, width in (('LEFT FEMUR', left_kn, 1.3), ('RIGHT FEMUR', right_kn, 1.3)):
            valid, t_plot, v_plot = self._time_value_valid_mask_ms(t, arr)
            if np.any(valid):
                self.ax.plot(t_plot[valid], v_plot[valid], linewidth=width, label=label)
        self._apply_zero_centered_kn_ylim(left_kn, right_kn)
        self.ax.set_title(f"INJURY - FEMUR ({self._graph_subject_label(slot)})")
        self.ax.set_xlabel(self._x_axis_label())
        self.ax.set_ylabel('Force (kN)')
        self.ax.grid(True)
        self.ax.legend(loc='best', fontsize=9)
        self.last_plot_title = f'{slot}_Femur_Combined_graph'
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def save_current_graph(self):
        initial = self.last_plot_title or 'injury_graph'
        path = filedialog.asksaveasfilename(
            title='그래프 저장',
            defaultextension='.png',
            initialfile=initial + '.png',
            filetypes=[('PNG image', '*.png'), ('JPEG image', '*.jpg'), ('All files', '*.*')],
        )
        if not path:
            return
        try:
            self.figure.savefig(path, dpi=150, bbox_inches='tight')
            if hasattr(self.workbench, 'add_history_entry'):
                self._log_history(f'Graph saved: {os.path.basename(path)}', event_type='graph_saved', slot=self._active_slot(), graph_uid=(self.slot_states.get(self._active_slot()) or {}).get('graph_uid'), persist=True)
            messagebox.showinfo('완료', '그래프를 저장했습니다.')
        except Exception as exc:
            messagebox.showerror('오류', f'그래프 저장 중 오류가 발생했습니다.\n{exc}')
