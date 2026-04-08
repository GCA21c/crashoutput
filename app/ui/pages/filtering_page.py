import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.core.isocode import rewrite_filter_code_in_text
from app.services.preprocessing.service import FILTER_OPTIONS, apply_filtering_with_derivatives, get_numeric_channels, make_channel_search_text


FILTER_COLOR_STYLES = {
    "CFC 60": {
        "bg": "#E8F4FF",
        "fg": "#0F172A",
        "selectbackground": "#93C5FD",
        "selectforeground": "#0F172A",
    },
    "CFC 180": {
        "bg": "#ECFDF3",
        "fg": "#14532D",
        "selectbackground": "#86EFAC",
        "selectforeground": "#14532D",
    },
    "CFC 600": {
        "bg": "#FFF7E6",
        "fg": "#7C2D12",
        "selectbackground": "#FCD34D",
        "selectforeground": "#7C2D12",
    },
    "CFC 1000": {
        "bg": "#FDF2F8",
        "fg": "#831843",
        "selectbackground": "#F9A8D4",
        "selectforeground": "#831843",
    },
}


class FilteringPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        self.search_var = tk.StringVar()
        self.cfc_var = tk.StringVar(value=FILTER_OPTIONS[1])
        self.info_var = tk.StringVar(value="데이터를 로드한 뒤 페이지를 열어주세요.")
        self.display_to_channel = {}
        self.channel_to_display = {}
        self.visible_display_items = []
        self.base_df = None
        self.pending_df = None
        self.pending_filter_labels = {}
        self.pending_source_path = None
        self.pending_descriptions = {}
        self.pending_units = {}
        self.pending_derived_channels = {}
        self.pending_channel_filter_colors = {}
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self, bg="#ffffff")
        header.pack(fill=tk.X, padx=16, pady=(16, 8))
        tk.Label(header, text="DATA FILTERING", font=("Arial", 15, "bold"), bg="#ffffff").pack(side=tk.LEFT)

        desc = tk.Label(
            self,
            text="왼쪽에서 채널을 여러 개 선택한 뒤 CFC를 적용하세요. 적용 결과는 즉시 미리보기에 반영되고, [확정 적용]을 눌러야 작업 데이터에 반영됩니다.",
            bg="#ffffff", anchor="w"
        )
        desc.pack(fill=tk.X, padx=16)

        tools = tk.LabelFrame(self, text="Filtering Control", bg="#ffffff")
        tools.pack(fill=tk.X, padx=16, pady=(8, 6))

        top = tk.Frame(tools, bg="#ffffff")
        top.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(top, text="검색", bg="#ffffff").pack(side=tk.LEFT)
        search_entry = tk.Entry(top, textvariable=self.search_var, width=24)
        search_entry.pack(side=tk.LEFT, padx=(6, 14))
        self.search_var.trace_add("write", lambda *_: self.refresh_channels(keep_selection=True))

        tk.Label(top, text="CFC", bg="#ffffff").pack(side=tk.LEFT)
        self.cfc_combo = ttk.Combobox(top, width=12, state="readonly", textvariable=self.cfc_var, values=FILTER_OPTIONS[1:])
        self.cfc_combo.pack(side=tk.LEFT, padx=(6, 8))
        tk.Button(top, text="선택 채널에 적용", command=self.apply_filters).pack(side=tk.LEFT)
        tk.Button(top, text="선택 채널 취소", command=self.cancel_selected_filters).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="FILTERING!", command=self.save_filters).pack(side=tk.LEFT, padx=(8, 0))

        preset = tk.Frame(tools, bg="#ffffff")
        preset.pack(fill=tk.X, padx=10, pady=(0, 10))
        tk.Label(preset, text="Quick Preset", bg="#ffffff").pack(side=tk.LEFT)
        for label in FILTER_OPTIONS[1:]:
            tk.Button(preset, text=label, command=lambda v=label: self._set_preset(v)).pack(side=tk.LEFT, padx=(6, 0))

        body = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#ffffff", bd=0)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=10)

        left_panel = tk.LabelFrame(body, text="채널 목록", bg="#ffffff", width=420)
        left_panel.pack_propagate(False)
        body.add(left_panel, minsize=320)

        self.channel_listbox = tk.Listbox(left_panel, selectmode=tk.EXTENDED, exportselection=False)
        self.channel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        lb_scroll = ttk.Scrollbar(left_panel, orient="vertical", command=self.channel_listbox.yview)
        lb_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8, padx=(0, 8))
        self.channel_listbox.configure(yscrollcommand=lb_scroll.set)
        self.channel_listbox.bind("<<ListboxSelect>>", lambda e: self.refresh_plot())

        right_panel = tk.Frame(body, bg="#ffffff")
        body.add(right_panel, stretch="always", minsize=420)

        self.figure = Figure(figsize=(8.0, 5.2), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("FILTERING CHANNEL")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self.canvas = FigureCanvasTkAgg(self.figure, master=right_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tk.Label(self, textvariable=self.info_var, bg="#ffffff", anchor="w", fg="#444444").pack(fill=tk.X, padx=16, pady=(0, 12))

    def _set_preset(self, label):
        self.cfc_var.set(label)


    def reset_session_state(self):
        self.search_var.set('')
        self.cfc_var.set(FILTER_OPTIONS[1])
        self.info_var.set("데이터를 로드한 뒤 페이지를 열어주세요.")
        self.display_to_channel.clear()
        self.channel_to_display.clear()
        self.visible_display_items = []
        self.base_df = None
        self.pending_df = None
        self.pending_filter_labels = {}
        self.pending_source_path = None
        self.pending_descriptions = {}
        self.pending_units = {}
        self.pending_derived_channels = {}
        self.pending_channel_filter_colors = {}
        self.channel_listbox.delete(0, tk.END)
        self.ax.clear()
        self.ax.set_title("FILTERING CHANNEL")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self.canvas.draw_idle()

    def on_show(self):
        self._sync_pending_if_needed(force=False)
        self.refresh_channels()
        self.refresh_plot()

    def _sync_pending_if_needed(self, force=False):
        viewer = self.workbench.viewer
        source_path = self.workbench.current_file_path or self.workbench.source_file_label
        if force or self.pending_df is None or self.pending_source_path != source_path:
            if viewer.df is None:
                self.base_df = None
                self.pending_df = None
                self.pending_filter_labels = {}
                self.pending_descriptions = {}
                self.pending_units = {}
                self.pending_derived_channels = {}
                self.pending_channel_filter_colors = {}
                self.pending_source_path = source_path
            else:
                self.base_df = viewer.df.copy(deep=True)
                self.pending_df = viewer.df.copy(deep=True)
                self.pending_filter_labels = dict(self.workbench.channel_filter_labels)
                self.pending_descriptions = dict(getattr(viewer, "external_descriptions", {}) or {})
                self.pending_units = dict(getattr(viewer, "external_units", {}) or {})
                self.pending_derived_channels = dict((self.workbench.dataset_metadata or {}).get("derived_channels") or {})
                self.pending_channel_filter_colors = dict((self.workbench.dataset_metadata or {}).get("channel_filter_colors") or {})
                self.pending_source_path = source_path

    def _get_active_df(self):
        return self.pending_df if self.pending_df is not None else self.workbench.viewer.df

    def _get_active_labels(self):
        return self.pending_filter_labels if self.pending_df is not None else self.workbench.channel_filter_labels

    def _display_name(self, viewer, channel):
        label = self._get_active_labels().get(channel, "Raw")
        desc = self.pending_descriptions.get(channel) or viewer.get_channel_display_name(channel)
        return f"{desc}   [{channel}]   [{label}]"

    def _selected_filter_label(self, channels):
        if not channels:
            return "Raw"
        labels = [str(self._get_active_labels().get(ch, "Raw") or "Raw") for ch in channels]
        first = labels[0]
        return first if all(lbl == first for lbl in labels) else "Mixed"

    def _plot_title_for_channels(self, channels):
        if not channels:
            return "FILTERING CHANNEL"
        label = self._selected_filter_label(channels)
        if len(channels) == 1:
            return f"{channels[0]} [{label}]"
        return f"Multiple channels ({len(channels)}) [{label}]"


    def _apply_listbox_item_style(self, index, channel):
        label = str(self.pending_channel_filter_colors.get(channel) or self._get_active_labels().get(channel, "Raw") or "Raw").strip()
        style = FILTER_COLOR_STYLES.get(label)
        if style:
            self.channel_listbox.itemconfig(index, **style)
        else:
            self.channel_listbox.itemconfig(
                index,
                bg="#ffffff",
                fg="#111111",
                selectbackground="#2563eb",
                selectforeground="#ffffff",
            )

    def _selected_channels(self):
        selected = []
        for idx in self.channel_listbox.curselection():
            if 0 <= idx < len(self.visible_display_items):
                display = self.visible_display_items[idx]
                channel = self.display_to_channel.get(display)
                if channel:
                    selected.append(channel)
        return selected

    def refresh_channels(self, keep_selection=False):
        self._sync_pending_if_needed(force=False)
        viewer = self.workbench.viewer
        active_df = self._get_active_df()
        previous_channels = self._selected_channels() if keep_selection else []

        self.channel_listbox.delete(0, tk.END)
        self.display_to_channel.clear()
        self.channel_to_display.clear()
        self.visible_display_items = []

        if active_df is None or viewer.time_column is None:
            self.info_var.set("데이터가 없습니다.")
            self.refresh_plot()
            return

        channels = get_numeric_channels(active_df, viewer.time_column)
        pattern = self.search_var.get().strip().lower()
        for channel in channels:
            if pattern and pattern not in make_channel_search_text(viewer, channel):
                continue
            display = self._display_name(viewer, channel)
            self.channel_to_display[channel] = display
            self.display_to_channel[display] = channel
            self.visible_display_items.append(display)
            self.channel_listbox.insert(tk.END, display)
            self._apply_listbox_item_style(self.channel_listbox.size() - 1, channel)

        if keep_selection and previous_channels:
            for ch in previous_channels:
                display = self.channel_to_display.get(ch)
                if display in self.visible_display_items:
                    idx = self.visible_display_items.index(display)
                    self.channel_listbox.selection_set(idx)

        total = len(channels)
        filtered = len(self.visible_display_items)
        pending_count = sum(1 for v in self._get_active_labels().values() if v != "Raw")
        self.info_var.set(f"총 {total}개 채널 / 표시 {filtered}개 | 선택 {len(self._selected_channels())}개 | 적용 대기 {pending_count}개 | SAE J211 CFC")
        self.refresh_plot()

    def refresh_plot(self):
        viewer = self.workbench.viewer
        self.ax.clear()
        self.ax.set_xlabel(viewer.get_x_axis_label() if getattr(viewer, "df", None) is not None else "Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)

        active_df = self._get_active_df()
        if active_df is None or viewer.time_column is None:
            self.ax.set_title("FILTERING CHANNEL")
            self.canvas.draw_idle()
            return

        selected_channels = self._selected_channels()
        self.ax.set_title(self._plot_title_for_channels(selected_channels))
        x = pd.to_numeric(active_df[viewer.time_column], errors="coerce").to_numpy(dtype=float)
        plotted = 0
        for channel in selected_channels:
            y = pd.to_numeric(active_df[channel], errors="coerce").to_numpy(dtype=float)
            valid = np.isfinite(x) & np.isfinite(y)
            if not np.any(valid):
                continue
            label = f"{channel} [{self._get_active_labels().get(channel, 'Raw')}]"
            self.ax.plot(x[valid], y[valid], linewidth=1.0, label=label)
            plotted += 1

        if plotted > 0:
            self.ax.relim()
            self.ax.autoscale_view()
            self.ax.legend(loc="best", fontsize=8)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def apply_filters(self):
        viewer = self.workbench.viewer
        self._sync_pending_if_needed(force=False)
        if self.pending_df is None or viewer.time_column is None:
            messagebox.showwarning("경고", "먼저 DAT 데이터를 로드하세요.")
            return

        selected_channels = self._selected_channels()
        if not selected_channels:
            messagebox.showwarning("경고", "왼쪽 목록에서 필터링할 채널을 선택하세요.")
            return

        filter_label = self.cfc_var.get().strip() or FILTER_OPTIONS[1]
        channel_to_filter = {channel: filter_label for channel in selected_channels}
        original_df = getattr(self.workbench, 'original_df', None)
        original_time_column = (
            getattr(self.workbench, 'original_metadata', {}) or {}
        ).get('time_column') or getattr(self.workbench, 'dataset_metadata', {}).get('time_column') or viewer.time_column
        self.pending_df, meta_updates = apply_filtering_with_derivatives(
            self.pending_df,
            viewer.time_column,
            channel_to_filter,
            descriptions=self.pending_descriptions,
            units=self.pending_units,
            existing_filter_labels=self.pending_filter_labels,
            existing_derived_channels=self.pending_derived_channels,
            original_df=original_df,
            original_time_column=original_time_column,
        )
        self.pending_descriptions = dict(meta_updates.get('descriptions') or {})
        self.pending_units = dict(meta_updates.get('units') or {})
        self.pending_filter_labels = dict(meta_updates.get('channel_filter_labels') or {})
        self.pending_derived_channels = dict(meta_updates.get('derived_channels') or {})

        for channel in selected_channels:
            self.pending_filter_labels[channel] = filter_label
            self.pending_channel_filter_colors[channel] = filter_label

        self.refresh_channels(keep_selection=True)
        self.refresh_plot()
        self.info_var.set(f"{len(selected_channels)}개 채널에 {filter_label} 적용 완료. [FILTERING!]을 누르면 작업 데이터에 반영됩니다.")

    def cancel_selected_filters(self):
        self._sync_pending_if_needed(force=False)
        viewer = self.workbench.viewer
        if self.pending_df is None or self.base_df is None or viewer.time_column is None:
            return

        selected_channels = self._selected_channels()
        if not selected_channels:
            messagebox.showwarning("경고", "취소할 채널을 먼저 선택하세요.")
            return

        derived_to_remove = []
        for dch, meta in list(self.pending_derived_channels.items()):
            if str(meta.get('source_channel')) in selected_channels and str(meta.get('purpose') or '').endswith('_injury'):
                derived_to_remove.append(dch)

        for channel in selected_channels:
            if channel in self.base_df.columns and channel in self.pending_df.columns:
                self.pending_df[channel] = self.base_df[channel].copy()
            self.pending_filter_labels[channel] = "Raw"
            self.pending_channel_filter_colors.pop(channel, None)

        for dch in derived_to_remove:
            if dch in self.pending_df.columns:
                self.pending_df.drop(columns=[dch], inplace=True)
            self.pending_filter_labels.pop(dch, None)
            self.pending_channel_filter_colors.pop(dch, None)
            self.pending_descriptions.pop(dch, None)
            self.pending_units.pop(dch, None)
            self.pending_derived_channels.pop(dch, None)

        self.refresh_channels(keep_selection=True)
        self.refresh_plot()
        self.info_var.set(f"{len(selected_channels)}개 채널을 Raw 상태로 되돌렸습니다. 아직 확정 전 미리보기 상태입니다.")

    def _rename_metadata_keys(self, mapping, rename_map):
        data = dict(mapping or {})
        if not rename_map:
            return data
        out = {}
        for key, value in data.items():
            out[rename_map.get(key, key)] = value
        return out

    def _apply_isocode_filter_suffixes_for_commit(self, dataframe, descriptions, units, filter_labels, channel_filter_colors, derived_channels):
        rename_map = {}
        raw_map = dict((self.workbench.dataset_metadata or {}).get('isocode_raw_map') or {})
        columns = list(getattr(dataframe, 'columns', []))
        for channel in columns:
            filter_label = str((filter_labels or {}).get(channel) or 'Raw').strip() or 'Raw'
            if filter_label == 'Raw':
                continue
            raw_code = str(raw_map.get(channel) or '').strip().upper()
            renamed = rewrite_filter_code_in_text(channel, filter_label, raw_code=raw_code)
            if renamed and renamed != channel:
                rename_map[channel] = renamed
        if rename_map:
            dataframe = dataframe.rename(columns=rename_map)
            descriptions = self._rename_metadata_keys(descriptions, rename_map)
            units = self._rename_metadata_keys(units, rename_map)
            filter_labels = self._rename_metadata_keys(filter_labels, rename_map)
            channel_filter_colors = self._rename_metadata_keys(channel_filter_colors, rename_map)
            derived_channels = self._rename_metadata_keys(derived_channels, rename_map)
        return dataframe, descriptions, units, filter_labels, channel_filter_colors, derived_channels, rename_map

    def save_filters(self):
        self._sync_pending_if_needed(force=False)
        if self.pending_df is None:
            messagebox.showwarning("경고", "확정할 필터 결과가 없습니다.")
            return

        pending_count = sum(1 for v in self.pending_filter_labels.values() if v != "Raw")
        if pending_count == 0:
            messagebox.showinfo("안내", "적용된 필터가 없습니다.")
            return

        final_df, final_desc, final_units, final_labels, final_colors, final_derived, rename_map = self._apply_isocode_filter_suffixes_for_commit(
            self.pending_df,
            self.pending_descriptions,
            self.pending_units,
            self.pending_filter_labels,
            self.pending_channel_filter_colors,
            self.pending_derived_channels,
        )

        self.workbench.channel_filter_labels = dict(final_labels)
        summary_items = [f"{ch}={label}" for ch, label in final_labels.items() if label != "Raw"]
        summary = ", ".join(summary_items[:6])
        if len(summary_items) > 6:
            summary += " ..."

        metadata_override = {
            'descriptions': dict(final_desc),
            'units': dict(final_units),
            'channel_filter_labels': dict(final_labels),
            'channel_filter_colors': dict(final_colors),
            'derived_channels': dict(final_derived),
        }
        saved_path = self.workbench.apply_processed_dataframe(
            final_df,
            {
                'type': 'filtering',
                'message': f"Filtering applied: {summary}",
                'display_message': f"Filtering applied: {pending_count} channel(s)",
            },
            op_suffix="_F",
            metadata_override=metadata_override,
        )
        self._sync_pending_if_needed(force=True)
        self.refresh_channels()
        self.refresh_plot()

        messagebox.showinfo("완료", "필터링 결과가 작업 데이터에 반영되었습니다.")
