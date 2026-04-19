import os
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.services.preprocessing.offset_preview import (
    copy_offset_after_preview_from_metadata,
    copy_offset_preview_from_metadata,
    offset_preview_metadata,
)
from app.services.preprocessing.service import OFFSET_SAMPLE_OPTIONS, apply_offset, find_time0_row, get_numeric_channels, get_offset_sample_rows, get_time_numeric


class OffsetPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        self.sample_var = tk.StringVar(value=("1000" if 1000 in OFFSET_SAMPLE_OPTIONS else str(OFFSET_SAMPLE_OPTIONS[0])))
        self.preview_channel_var = tk.StringVar()
        self.time0_info_var = tk.StringVar(value="Time0: -")
        self.info_var = tk.StringVar(value="데이터를 로드한 뒤 페이지를 열어주세요.")
        self.before_df = None
        self.after_df = None
        self.show_before_var = tk.BooleanVar(value=True)
        self._display_to_channel = {}
        self._build_ui()

    def _metadata_before_df(self):
        return copy_offset_preview_from_metadata(getattr(self.workbench, "dataset_metadata", {}) or {})

    def _metadata_after_df(self):
        return copy_offset_after_preview_from_metadata(getattr(self.workbench, "dataset_metadata", {}) or {})

    def _ensure_before_df_loaded(self):
        if self.before_df is not None:
            return
        self.before_df = self._metadata_before_df()

    def _ensure_after_df_loaded(self):
        if self.after_df is not None:
            return
        self.after_df = self._metadata_after_df()

    def _build_ui(self):
        header = tk.Frame(self, bg="#ffffff")
        header.pack(fill=tk.X, padx=16, pady=(16, 8))

        tk.Label(header, text="DATA OFFSET", font=("Arial", 15, "bold"), bg="#ffffff").pack(side=tk.LEFT)

        body = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#ffffff", bd=0)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        left = tk.Frame(body, bg="#ffffff", width=380)
        left.pack_propagate(False)
        body.add(left, minsize=320)

        right = tk.Frame(body, bg="#ffffff")
        body.add(right, stretch="always", minsize=420)

        info_box = tk.LabelFrame(left, text="Offset 설정", bg="#ffffff")
        info_box.pack(fill=tk.X, pady=(0, 10))

        top_actions = tk.Frame(info_box, bg="#ffffff")
        top_actions.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Button(top_actions, text="APPLY OFFSET", command=self.apply_offset_to_all_channels).pack(side=tk.RIGHT)

        row1 = tk.Frame(info_box, bg="#ffffff")
        row1.pack(fill=tk.X, padx=10, pady=(8, 6))
        tk.Label(row1, text="데이터 시작 ~ Time0 기준 샘플 수", bg="#ffffff").pack(anchor="w")
        sample_combo = ttk.Combobox(row1, width=16, state="readonly", textvariable=self.sample_var, values=[str(v) for v in OFFSET_SAMPLE_OPTIONS])
        sample_combo.pack(anchor="w", pady=(4, 0))
        sample_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_plot())

        row2 = tk.Frame(info_box, bg="#ffffff")
        row2.pack(fill=tk.X, padx=10, pady=6)
        tk.Label(row2, text="확인용 채널", bg="#ffffff").pack(anchor="w")
        self.channel_combo = ttk.Combobox(row2, width=34, state="readonly", textvariable=self.preview_channel_var)
        self.channel_combo.pack(anchor="w", pady=(4, 0), fill=tk.X)
        self.channel_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_plot())

        tk.Label(info_box, textvariable=self.time0_info_var, justify="left", bg="#ffffff", fg="#333333").pack(fill=tk.X, padx=10, pady=6)

        row3 = tk.Frame(info_box, bg="#ffffff")
        row3.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Checkbutton(
            row3,
            text="이전 그래프 함께 보기",
            variable=self.show_before_var,
            command=self.refresh_plot,
            bg="#ffffff",
            activebackground="#ffffff",
        ).pack(anchor="w")

        tk.Label(
            info_box,
            text="※ 확인용 채널은 확인 전용입니다. Offset은 Time 채널을 제외한 모든 채널에 적용되며, Mean Offset Correction 으로 진행합니다.",
            justify="left",
            bg="#ffffff",
            fg="#666666",
            wraplength=340,
        ).pack(fill=tk.X, padx=10, pady=(0, 10))

        summary_box = tk.LabelFrame(left, text="상태", bg="#ffffff")
        summary_box.pack(fill=tk.X)
        tk.Label(summary_box, textvariable=self.info_var, justify="left", anchor="w", bg="#ffffff", fg="#444444", wraplength=340).pack(fill=tk.X, padx=10, pady=10)

        self.figure = Figure(figsize=(8.0, 5.2), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("DATA OFFSET")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _channel_display_map(self, channels):
        viewer = self.workbench.viewer
        mapping = {}
        used = set()
        for ch in channels:
            desc = (viewer.get_channel_display_name(ch) or '').strip()
            display = f"{ch} | {desc}" if desc and desc != str(ch) else str(ch)
            if display in used:
                display = f"{display} [{len(used)+1}]"
            used.add(display)
            mapping[display] = ch
        return mapping

    def _selected_channel(self):
        return self._display_to_channel.get(self.preview_channel_var.get(), self.preview_channel_var.get())


    def reset_session_state(self):
        self.before_df = None
        self.after_df = None
        self._display_to_channel = {}
        self.preview_channel_var.set('')
        self.time0_info_var.set('Time0: -')
        self.info_var.set('데이터를 로드한 뒤 페이지를 열어주세요.')
        self.show_before_var.set(True)
        self.ax.clear()
        self.ax.set_title("DATA OFFSET")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self.canvas.draw_idle()

    def on_show(self):
        self._ensure_before_df_loaded()
        self._ensure_after_df_loaded()
        self.refresh_channels(force_default=False)
        self.refresh_plot()

    def refresh_channels(self, force_default=False):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            self.channel_combo["values"] = ()
            self.preview_channel_var.set("")
            self.time0_info_var.set("Time0: -")
            self.info_var.set("데이터가 없습니다.")
            self.refresh_plot()
            return

        channels = get_numeric_channels(viewer.df, viewer.time_column)
        self._display_to_channel = self._channel_display_map(channels)
        display_values = list(self._display_to_channel.keys())
        self.channel_combo["values"] = display_values

        current_raw = self._selected_channel().strip()
        current_display = next((d for d, ch in self._display_to_channel.items() if ch == current_raw), "")
        if force_default:
            self.preview_channel_var.set(display_values[0] if display_values else "")
        elif current_display:
            self.preview_channel_var.set(current_display)
        elif display_values:
            self.preview_channel_var.set(display_values[0])
        else:
            self.preview_channel_var.set("")

        time0_row = find_time0_row(viewer.df, viewer.time_column)
        if time0_row is None:
            self.time0_info_var.set("Time0: 찾지 못함")
        else:
            time_arr = get_time_numeric(viewer.df, viewer.time_column)
            time0_t = time_arr[time0_row] if 0 <= time0_row < len(time_arr) else np.nan
            self.time0_info_var.set(f"Time0 row: {time0_row}\nTime0 time: {time0_t:.9g} s")

        self.info_var.set(
            f"Offset 대상: Time 제외 숫자 채널 {len(channels)}개\n"
            f"현재 작업 기준: {self.workbench.current_file_path or self.workbench.source_file_label or '-'}"
        )

    def refresh_plot(self):
        viewer = self.workbench.viewer
        self.ax.clear()
        self.ax.set_title("DATA OFFSET")
        self.ax.set_xlabel(viewer.get_x_axis_label() if getattr(viewer, "df", None) is not None else "Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)

        channel = self._selected_channel()
        if viewer.df is None or viewer.time_column is None or not channel:
            self.canvas.draw_idle()
            return

        after_df = self.after_df if self.after_df is not None and channel in self.after_df.columns else viewer.df
        x_all = get_time_numeric(after_df, viewer.time_column)

        if self.show_before_var.get() and self.before_df is not None and channel in self.before_df.columns:
            x_before = get_time_numeric(self.before_df, viewer.time_column)
            y_before = pd.to_numeric(self.before_df[channel], errors="coerce").to_numpy(dtype=float)
            valid_before = np.isfinite(x_before) & np.isfinite(y_before)
            if np.any(valid_before):
                self.ax.plot(
                    x_before[valid_before],
                    y_before[valid_before],
                    linewidth=1.0,
                    color="#00ff5e",
		    alpha=0.5,
                    linestyle=":",
                    zorder=4,
                    label=f"Before Offset: {channel}",
                )

        time0_row = find_time0_row(viewer.df, viewer.time_column)
        if time0_row is not None and 0 <= time0_row < len(x_all) and np.isfinite(x_all[time0_row]):
            time0_t = float(x_all[time0_row])
            try:
                sample_count = int(self.sample_var.get())
            except Exception:
                sample_count = OFFSET_SAMPLE_OPTIONS[0]
            sample_rows = get_offset_sample_rows(viewer.df, viewer.time_column, sample_count, time0_row=time0_row, include_time0=True)
            if sample_rows.size > 0:
                t0 = float(x_all[sample_rows[0]])
                t1 = float(x_all[sample_rows[-1]])
                self.ax.axvspan(t0, t1, alpha=0.18, color="#93c5fd", zorder=2, label="Offset Sample Range")
            self.ax.axvline(time0_t, linestyle="-", linewidth=1.0, color="#444444", zorder=3, label="Time0")

        y_after = pd.to_numeric(after_df[channel], errors="coerce").to_numpy(dtype=float)
        valid_after = np.isfinite(x_all) & np.isfinite(y_after)
        if np.any(valid_after):
            self.ax.plot(
                x_all[valid_after],
                y_after[valid_after],
                linewidth=1.1,
                zorder=1,
                label=f"After Offset: {channel}",
            )

        if self.ax.lines or self.ax.collections or self.ax.patches:
            self.ax.relim()
            self.ax.autoscale_view()
            self.ax.legend(loc="best", fontsize=9)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def apply_offset_to_all_channels(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning("경고", "먼저 DAT 데이터를 로드하세요.")
            return

        try:
            sample_count = int(self.sample_var.get())
        except Exception:
            messagebox.showwarning("경고", "샘플 수를 확인하세요.")
            return

        channels = get_numeric_channels(viewer.df, viewer.time_column)
        if not channels:
            messagebox.showwarning("경고", "오프셋 가능한 숫자 채널이 없습니다.")
            return

        time0_row = find_time0_row(viewer.df, viewer.time_column)
        if time0_row is None:
            messagebox.showwarning("경고", "Time0를 찾지 못했습니다.")
            return

        self.before_df = viewer.df.copy(deep=True)
        out, offsets = apply_offset(viewer.df, viewer.time_column, channels, sample_count, time0_row=time0_row)
        if not offsets:
            messagebox.showwarning("경고", "적용 가능한 채널이 없거나 샘플 구간이 부족합니다.")
            return
        self.after_df = out.copy(deep=True)

        summary = ", ".join(f"{viewer.get_channel_display_name(ch)}={val:.6g}" for ch, val in list(offsets.items())[:6])
        if len(offsets) > 6:
            summary += " ..."
        metadata_override = offset_preview_metadata(self.before_df, self.after_df)
        saved_path = self.workbench.apply_processed_dataframe(
            out,
            {
                'type': 'offset',
                'message': f"Offset applied: all numeric channels, first {sample_count} samples from data start to Time0 | {summary}",
                'display_message': f"Offset applied: all numeric channels, first {sample_count} samples from data start to Time0",
            },
            op_suffix="_O",
            metadata_override=metadata_override,
            update_pre_filter_reference=True,
        )
        self.refresh_channels()
        self.refresh_plot()

        self.info_var.set(
            f"Offset 완료: {len(offsets)}개 채널\n"
            f"샘플 수: {sample_count}"
        )
        messagebox.showinfo("완료", "Offset이 작업 데이터에 반영되었습니다.")
