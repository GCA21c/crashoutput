import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from app.services.preprocessing.service import trim_dataframe


class TrimmingPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        self.preview_channel_var = tk.StringVar()
        self.start_var = tk.StringVar(value="0")
        self.end_var = tk.StringVar(value="0.3")
        self.duration_var = tk.StringVar(value="선택 구간: -")
        self.span = None
        self._entry_update_job = None
        self._suspend_entry_trace = False
        self._display_to_channel = {}
        self._build_ui()
        self.start_var.trace_add("write", self._on_entry_changed)
        self.end_var.trace_add("write", self._on_entry_changed)

    def _build_ui(self):
        header = tk.Frame(self, bg="#ffffff")
        header.pack(fill=tk.X, padx=16, pady=(16, 8))

        tk.Label(header, text="DATA TRIMMING", font=("Arial", 15, "bold"), bg="#ffffff").pack(side=tk.LEFT)

        controls = tk.Frame(self, bg="#ffffff")
        controls.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Label(controls, text="기준 그래프 채널:", bg="#ffffff").pack(side=tk.LEFT)
        self.channel_combo = ttk.Combobox(controls, width=35, state="readonly", textvariable=self.preview_channel_var)
        self.channel_combo.pack(side=tk.LEFT, padx=(6, 14))
        self.channel_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_plot())

        tk.Label(controls, text="Start Time:", bg="#ffffff").pack(side=tk.LEFT)
        tk.Entry(controls, textvariable=self.start_var, width=12).pack(side=tk.LEFT, padx=(6, 10))
        tk.Label(controls, text="End Time:", bg="#ffffff").pack(side=tk.LEFT)
        tk.Entry(controls, textvariable=self.end_var, width=12).pack(side=tk.LEFT, padx=(6, 10))
        tk.Label(controls, textvariable=self.duration_var, bg="#ffffff", fg="#333333").pack(side=tk.LEFT, padx=(8, 10))
        tk.Button(controls, text="TRIMMING!", command=self.apply_trim).pack(side=tk.LEFT)

        body = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#ffffff", bd=0)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        left = tk.LabelFrame(body, text="Trim 설정", bg="#ffffff", width=340)
        left.pack_propagate(False)
        body.add(left, minsize=300)

        tk.Label(
            left,
            text="Start/End Time을 직접 입력하면 선택 구간이 그래프에 바로 반영됩니다. 적용 시 입력한 시간 범위가 전체 채널에 동일하게 적용됩니다.",
            justify="left",
            anchor="w",
            bg="#ffffff",
            fg="#555555",
            wraplength=300,
        ).pack(fill=tk.X, padx=10, pady=(10, 8))
        tk.Label(left, textvariable=self.duration_var, bg="#ffffff", anchor="w", justify="left", fg="#333333").pack(fill=tk.X, padx=10, pady=(0, 10))

        right = tk.Frame(body, bg="#ffffff")
        body.add(right, stretch="always", minsize=420)

        self.figure = Figure(figsize=(8.2, 5.2), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("DATA TRIMMING")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


    def reset_session_state(self):
        self.preview_channel_var.set('')
        self.start_var.set('0')
        self.end_var.set('0.3')
        self.duration_var.set('선택 구간: -')
        self._display_to_channel = {}
        self.span = None
        self.ax.clear()
        self.ax.set_title("DATA TRIMMING")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self.canvas.draw_idle()
        try:
            self.channel_combo['values'] = ()
        except Exception:
            pass

    def on_show(self):
        self.refresh_channels()
        self.refresh_plot()

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

    def refresh_channels(self):
        viewer = self.workbench.viewer
        if viewer.df is None:
            self._display_to_channel = {}
            self.channel_combo["values"] = ()
            return
        channels = viewer.get_numeric_channel_names(exclude_time=True)
        self._display_to_channel = self._channel_display_map(channels)
        display_values = list(self._display_to_channel.keys())
        self.channel_combo["values"] = display_values

        # 기준 그래프 채널은 항상 목록의 첫 번째 채널을 기본값으로 사용한다.
        # 기존에는 Viewer의 현재 선택 채널(get_preferred_preview_channel)을 우선 사용해서
        # 다른 모듈에서 마지막으로 보던 채널이 남아 보일 수 있었다.
        current_raw = self._selected_channel()
        current_display = next((d for d, ch in self._display_to_channel.items() if ch == current_raw), '')

        if current_display and current_display in display_values:
            self.preview_channel_var.set(current_display)
        elif display_values:
            self.preview_channel_var.set(display_values[0])

    def _set_span(self, start_time, end_time, update_entries=True):
        if start_time is None or end_time is None:
            self.span = None
            self.duration_var.set("선택 구간: -")
            return
        start_time = float(start_time)
        end_time = float(end_time)
        if end_time < start_time:
            start_time, end_time = end_time, start_time
        self.span = (start_time, end_time)
        if update_entries:
            self._suspend_entry_trace = True
            try:
                self.start_var.set(f"{start_time:.6g}")
                self.end_var.set(f"{end_time:.6g}")
            finally:
                self._suspend_entry_trace = False
        self.duration_var.set(f"선택 구간: {end_time - start_time:.6g} s")

    def _on_entry_changed(self, *_):
        if self._suspend_entry_trace:
            return
        if self._entry_update_job is not None:
            self.after_cancel(self._entry_update_job)
        self._entry_update_job = self.after(180, self._apply_entry_preview_silent)

    def _apply_entry_preview_silent(self):
        self._entry_update_job = None
        try:
            start_time = float(self.start_var.get())
            end_time = float(self.end_var.get())
        except Exception:
            return
        self._set_span(start_time, end_time, update_entries=False)
        self.refresh_plot(redraw_only=True)

    def on_span_selected(self, xmin, xmax):
        if xmin is None or xmax is None or abs(xmax - xmin) < 1e-15:
            return
        self._set_span(xmin, xmax, update_entries=True)
        self.refresh_plot(redraw_only=True)

    def apply_entry_preview(self):
        try:
            start_time = float(self.start_var.get())
            end_time = float(self.end_var.get())
        except Exception:
            messagebox.showwarning("경고", "Start/End Time 값을 숫자로 입력하세요.")
            return
        self._set_span(start_time, end_time, update_entries=False)
        self.refresh_plot(redraw_only=True)

    def refresh_plot(self, redraw_only=False):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            self.ax.clear()
            self.ax.set_title("데이터를 먼저 로드하세요")
            self.ax.grid(True)
            self.canvas.draw_idle()
            return

        channel = self._selected_channel()
        if not channel:
            self.refresh_channels()
            channel = self._selected_channel()
        if not channel:
            return

        x_all = viewer.get_numeric_column(viewer.time_column)
        y_all = viewer.get_numeric_column(channel)
        valid = np.isfinite(x_all) & np.isfinite(y_all)
        if not np.any(valid):
            return

        old_xlim = self.ax.get_xlim() if redraw_only else None
        old_ylim = self.ax.get_ylim() if redraw_only else None
        self.ax.clear()
        self.ax.plot(x_all[valid], y_all[valid], linewidth=1.0)
        self.ax.set_title("DATA TRIMMING")
        self.ax.set_xlabel(viewer.get_x_axis_label() if getattr(viewer, "df", None) is not None else "Time")
        self.ax.set_ylabel(viewer.get_y_axis_label(channel))
        self.ax.grid(True)

        if self.span is None:
            try:
                start_default = float(self.start_var.get())
                end_default = float(self.end_var.get())
                self._set_span(start_default, end_default, update_entries=False)
            except Exception:
                self._set_span(float(x_all[valid][0]), float(x_all[valid][-1]), update_entries=True)
        if self.span is not None:
            self.ax.axvspan(self.span[0], self.span[1], alpha=0.2)

        if redraw_only and old_xlim is not None and old_ylim is not None:
            self.ax.set_xlim(old_xlim)
            self.ax.set_ylim(old_ylim)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def apply_trim(self):
        viewer = self.workbench.viewer
        if viewer.df is None or viewer.time_column is None:
            messagebox.showwarning("경고", "먼저 DAT 데이터를 로드하세요.")
            return
        try:
            start_time = float(self.start_var.get())
            end_time = float(self.end_var.get())
        except Exception:
            messagebox.showwarning("경고", "Start/End Time 값을 숫자로 입력하세요.")
            return

        out = trim_dataframe(viewer.df, viewer.time_column, start_time, end_time)
        if out.empty:
            messagebox.showwarning("경고", "트리밍 결과가 비어 있습니다.")
            return

        metadata_override = {
            "time_column": viewer.time_column,
            "units": dict(getattr(viewer, "external_units", {}) or {}),
            "descriptions": dict(getattr(viewer, "external_descriptions", {}) or {}),
        }
        self.workbench.apply_processed_dataframe(
            out,
            f"Trim applied: {min(start_time, end_time):.6g} ~ {max(start_time, end_time):.6g} s",
            op_suffix="_T",
            metadata_override=metadata_override,
        )
        messagebox.showinfo("완료", "선택 구간으로 데이터가 트리밍되었습니다.")
        self.refresh_channels()
        self.refresh_plot()
