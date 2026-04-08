import bisect
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import tkinter.font as tkfont

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib import rcParams
from matplotlib.ticker import MultipleLocator, MaxNLocator, FuncFormatter
from matplotlib.widgets import SpanSelector
from app.services.io.dat_loader import DatLoadError, load_dat_file
from app.services.io.csv_loader import CsvLoadError, load_csv_file, load_csv_preview
from app.services.preprocessing.service import _apply_cfc_filter_segment as cfc_filter_segment
from app.services.preprocessing.service import _get_sample_rate as cfc_get_sample_rate

from app.core.io.dataset_store import DATASET_EXT, DatasetStoreError, load_dataset_pickle


class RowHideDialog(tk.Toplevel):
    def __init__(self, parent, df, preview_count=30):
        super().__init__(parent)
        self.title("숨길 행 선택")
        self.geometry("800x650")
        self.resizable(True, True)

        self.result = None
        self.preview_count = min(preview_count, len(df))
        self.hide_vars = []

        info_frame = tk.Frame(self)
        info_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            info_frame,
            text=f"처음 {self.preview_count}개 행을 표시합니다.",
            fg="blue"
        ).pack(anchor="w")

        tk.Label(
            info_frame,
            text="각 행의 내용 1~3번째 확인 후 숨길 행을 체크하시오.",
            fg="blue"
        ).pack(anchor="w", pady=(2, 0))

        list_frame = tk.LabelFrame(self, text=f"행 목록 (처음 {self.preview_count}개)")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(list_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.check_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.check_frame, anchor="nw")

        self.check_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        preview_df = df.head(self.preview_count).replace({np.nan: ""})
        preview_arr = preview_df.astype(str).to_numpy()

        for i in range(self.preview_count):
            row_values = preview_arr[i]
            preview_text = " | ".join(row_values[:3])

            var = tk.BooleanVar(value=False)
            self.hide_vars.append(var)

            chk = tk.Checkbutton(
                self.check_frame,
                text=f"{i}: {preview_text}",
                variable=var,
                anchor="w",
                justify="left"
            )
            chk.pack(fill=tk.X, anchor="w", padx=5, pady=2)

            chk.bind("<MouseWheel>", self._on_mousewheel_windows)
            chk.bind("<Button-4>", self._on_mousewheel_linux)
            chk.bind("<Button-5>", self._on_mousewheel_linux)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel_windows)
        self.canvas.bind("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind("<Button-5>", self._on_mousewheel_linux)
        self.check_frame.bind("<MouseWheel>", self._on_mousewheel_windows)
        self.check_frame.bind("<Button-4>", self._on_mousewheel_linux)
        self.check_frame.bind("<Button-5>", self._on_mousewheel_linux)

        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(button_frame, text="전체 해제", command=self.clear_all).pack(side=tk.LEFT)
        tk.Button(button_frame, text="전체 선택", command=self.select_all).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="확인", command=self.on_ok).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="취소", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

    def _on_mousewheel_windows(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        return "break"

    def clear_all(self):
        for var in self.hide_vars:
            var.set(False)

    def select_all(self):
        for var in self.hide_vars:
            var.set(True)

    def on_ok(self):
        self.result = {"hidden_rows": [i for i, var in enumerate(self.hide_vars) if var.get()]}
        self.destroy()


class FastCanvasTable(tk.Frame):
    def __init__(
        self,
        parent,
        header_click_callback=None,
        row_click_callback=None,
        cell_click_callback=None,
        header_checkbox_toggle_callback=None
    ):
        super().__init__(parent)
        self.header_click_callback = header_click_callback
        self.row_click_callback = row_click_callback
        self.cell_click_callback = cell_click_callback
        self.header_checkbox_toggle_callback = header_checkbox_toggle_callback

        self.columns = []
        self.data = None
        self.total_rows = 0
        self.total_cols = 0
        self.row_labels = []

        self.default_col_width = 120
        self.max_col_width = 220
        self.row_height = 20
        self.header_height = 38
        self.row_header_width = 60
        self.pad_x = 6
        self.font = ("Arial", 9)
        self.header_font = ("Arial", 9, "bold")

        self.selected_column = None
        self.selected_row = None
        self.selected_cell = None
        self.selection_anchor = None
        self.selection_range = None
        self.row_labels = []
        self._is_drag_selecting = False
        self._drag_started_cell = None

        self.col_widths = []
        self.col_starts = [0]
        self.row_heights = []
        self.row_starts = [0]
        self.total_width = 0
        self.total_height = 0

        self._render_job = None
        self._last_view = None

        self.multi_checked_columns = set()
        self.checkbox_size = 12
        self.checkbox_margin_right = 6

        self.min_col_width = 60
        self.min_row_height = 18
        self.max_row_height = 60
        self._resize_hotspot = 4
        self._col_resize_index = None
        self._col_resize_start_x = None
        self._col_resize_start_width = None

        self._build_ui()

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.corner_canvas = tk.Canvas(
            self,
            width=self.row_header_width,
            height=self.header_height,
            bg="#e9e9e9",
            highlightthickness=0
        )
        self.corner_canvas.grid(row=0, column=0, sticky="nsew")

        self.header_canvas = tk.Canvas(
            self,
            height=self.header_height,
            bg="#f0f0f0",
            highlightthickness=0
        )
        self.header_canvas.grid(row=0, column=1, sticky="ew")

        self.row_canvas = tk.Canvas(
            self,
            width=self.row_header_width,
            bg="#f7f7f7",
            highlightthickness=0
        )
        self.row_canvas.grid(row=1, column=0, sticky="ns")

        self.body_canvas = tk.Canvas(
            self,
            bg="white",
            highlightthickness=1,
            highlightbackground="#cfcfcf",
            takefocus=1
        )
        self.body_canvas.grid(row=1, column=1, sticky="nsew")

        self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.on_vscroll)
        self.v_scroll.grid(row=1, column=2, sticky="ns")

        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.on_hscroll)
        self.h_scroll.grid(row=2, column=1, sticky="ew")

        self.body_canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.header_canvas.configure(xscrollcommand=self.h_scroll.set)
        self.row_canvas.configure(yscrollcommand=self.v_scroll.set)

        self.body_canvas.bind("<Configure>", self.on_resize)
        self.header_canvas.bind("<Configure>", self.on_resize)
        self.row_canvas.bind("<Configure>", self.on_resize)

        self.body_canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.body_canvas.bind("<Button-4>", self.on_mousewheel_linux)
        self.body_canvas.bind("<Button-5>", self.on_mousewheel_linux)
        self.row_canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.row_canvas.bind("<Button-4>", self.on_mousewheel_linux)
        self.row_canvas.bind("<Button-5>", self.on_mousewheel_linux)

        self.body_canvas.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)
        self.body_canvas.bind("<Shift-Button-4>", self.on_shift_mousewheel_linux)
        self.body_canvas.bind("<Shift-Button-5>", self.on_shift_mousewheel_linux)
        self.header_canvas.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)
        self.header_canvas.bind("<Shift-Button-4>", self.on_shift_mousewheel_linux)
        self.header_canvas.bind("<Shift-Button-5>", self.on_shift_mousewheel_linux)

        self.header_canvas.bind("<Button-1>", self.on_header_click)
        self.header_canvas.bind("<B1-Motion>", self.on_header_drag)
        self.header_canvas.bind("<ButtonRelease-1>", self.on_header_release)
        self.header_canvas.bind("<Double-Button-1>", self.on_header_double_click)
        self.header_canvas.bind("<Motion>", self.on_header_motion)
        self.header_canvas.bind("<Leave>", self.on_header_leave)
        self.row_canvas.bind("<Button-1>", self.on_row_click)
        self.body_canvas.bind("<Button-1>", self.on_cell_click)
        self.body_canvas.bind("<B1-Motion>", self.on_cell_drag)
        self.body_canvas.bind("<ButtonRelease-1>", self.on_cell_release)
        self.body_canvas.bind("<Control-c>", self.copy_selection)
        self.body_canvas.bind("<Control-C>", self.copy_selection)

        self.body_canvas.bind("<Key>", self.on_key_press)
        self.body_canvas.bind("<FocusIn>", self.on_focus_in)
        self.body_canvas.bind("<FocusOut>", self.on_focus_out)

        self._cell_font = tkfont.Font(font=self.font)
        self._header_font = tkfont.Font(font=self.header_font)

    def set_data(self, columns, display_data, row_labels=None):
        self.columns = list(columns)
        self.data = display_data
        self.total_rows = 0 if display_data is None else len(display_data)
        self.total_cols = len(self.columns)
        self.row_labels = list(row_labels) if row_labels is not None else [str(i) for i in range(self.total_rows)]
        if len(self.row_labels) < self.total_rows:
            self.row_labels.extend(str(i) for i in range(len(self.row_labels), self.total_rows))

        self.selected_column = None
        self.selected_row = None
        self.selected_cell = None
        self.multi_checked_columns = set()

        self._prepare_columns()
        self._prepare_rows()
        self._update_scrollregion(reset_view=True)
        self.schedule_render(force=True)

    def set_multi_checked_columns(self, columns):
        self.multi_checked_columns = set(columns or [])
        self.schedule_render(force=True)

    def _prepare_columns(self):
        self.col_widths = []
        for col in self.columns:
            name = str(col).strip().lower()
            width = self.default_col_width
            if name == "time":
                width = 90
            elif len(str(col)) >= 18:
                width = 150
            self.col_widths.append(min(width, self.max_col_width))

        self.col_starts = [0]
        running = 0
        for width in self.col_widths:
            running += width
            self.col_starts.append(running)
        self.total_width = running

    def _prepare_rows(self):
        self.row_heights = [self.row_height for _ in range(self.total_rows)]
        self._rebuild_row_geometry()

    def _rebuild_column_geometry(self):
        self.col_starts = [0]
        running = 0
        for width in self.col_widths:
            running += width
            self.col_starts.append(running)
        self.total_width = running

    def _rebuild_row_geometry(self):
        self.row_starts = [0]
        running = 0
        for height in self.row_heights:
            running += height
            self.row_starts.append(running)
        self.total_height = running

    def _get_header_resize_col(self, x):
        if self.total_cols == 0:
            return None
        x = self.header_canvas.canvasx(x)
        for idx in range(self.total_cols - 1):
            boundary = self.col_starts[idx + 1]
            if abs(x - boundary) <= self._resize_hotspot:
                return idx
        return None

    def _get_row_at_y(self, y):
        if self.total_rows <= 0:
            return None
        y = self.row_canvas.canvasy(y)
        idx = bisect.bisect_right(self.row_starts, y) - 1
        return idx if 0 <= idx < self.total_rows else None

    def _get_row_resize_index(self, y):
        return None

    def _is_row_resize_zone(self, y):
        return False

    def on_header_motion(self, event):
        if self._col_resize_index is not None:
            self.header_canvas.configure(cursor='sb_h_double_arrow')
            return
        self.header_canvas.configure(cursor='sb_h_double_arrow' if self._get_header_resize_col(event.x) is not None else '')

    def on_header_leave(self, event):
        if self._col_resize_index is None:
            self.header_canvas.configure(cursor='')

    def on_header_drag(self, event):
        if self._col_resize_index is None:
            return
        x = self.header_canvas.canvasx(event.x)
        delta = x - self._col_resize_start_x
        new_width = max(self.min_col_width, min(self.max_col_width, int(self._col_resize_start_width + delta)))
        if new_width != self.col_widths[self._col_resize_index]:
            self.col_widths[self._col_resize_index] = new_width
            self._rebuild_column_geometry()
            self._update_scrollregion(reset_view=False)
            self.schedule_render(force=True)

    def on_header_release(self, event):
        self._col_resize_index = None
        self._col_resize_start_x = None
        self._col_resize_start_width = None
        self.header_canvas.configure(cursor='')

    def on_header_double_click(self, event):
        resize_col = self._get_header_resize_col(event.x)
        if resize_col is not None:
            self.auto_fit_column(resize_col)
            return "break"

    def on_row_header_double_click(self, event):
        return None

    def on_row_header_motion(self, event):
        self.row_canvas.configure(cursor='')

    def on_row_header_leave(self, event):
        self.row_canvas.configure(cursor='')

    def on_row_header_drag(self, event):
        return None

    def on_row_header_release(self, event):
        self.row_canvas.configure(cursor='')

    def clear(self):
        self.columns = []
        self.data = None
        self.total_rows = 0
        self.total_cols = 0
        self.col_widths = []
        self.col_starts = [0]
        self.row_heights = []
        self.row_starts = [0]
        self.total_width = 0
        self.total_height = 0
        self.selected_column = None
        self.selected_row = None
        self.selected_cell = None
        self.selection_anchor = None
        self.selection_range = None
        self._is_drag_selecting = False
        self._drag_started_cell = None
        self._last_view = None

        self.corner_canvas.delete("all")
        self.header_canvas.delete("all")
        self.row_canvas.delete("all")
        self.body_canvas.delete("all")
        self._update_scrollregion(reset_view=True)

    def set_selected_column(self, column_name):
        self.selected_column = column_name
        self.schedule_render(force=True)

    def set_selected_row(self, row_idx):
        self.selected_row = row_idx
        self.schedule_render(force=True)

    def set_selected_cell(self, row_idx, col_idx):
        self.selected_cell = (row_idx, col_idx)
        self.selection_anchor = (row_idx, col_idx)
        self.selection_range = ((row_idx, row_idx), (col_idx, col_idx))
        self._is_drag_selecting = False
        self.selected_row = row_idx
        if 0 <= col_idx < len(self.columns):
            self.selected_column = self.columns[col_idx]
        self.ensure_cell_visible(row_idx, col_idx)
        self.schedule_render(force=True)

    def ensure_cell_visible(self, row_idx, col_idx):
        if self.total_rows == 0 or self.total_cols == 0:
            return

        view_w = max(1, self.body_canvas.winfo_width())
        view_h = max(1, self.body_canvas.winfo_height())

        x0 = self.body_canvas.canvasx(0)
        y0 = self.body_canvas.canvasy(0)
        x1 = x0 + view_w
        y1 = y0 + view_h

        cell_x0 = self.col_starts[col_idx]
        cell_x1 = self.col_starts[col_idx + 1]
        cell_y0 = self.row_starts[row_idx]
        cell_y1 = self.row_starts[row_idx + 1]

        margin_x = 20
        margin_y = 20

        if cell_x0 < x0 + margin_x:
            new_x = max(0, cell_x0 - margin_x)
            self.body_canvas.xview_moveto(new_x / max(1, self.total_width))
            self.header_canvas.xview_moveto(self.body_canvas.xview()[0])
        elif cell_x1 > x1 - margin_x:
            new_x = min(max(0, self.total_width - view_w), cell_x1 - view_w + margin_x)
            self.body_canvas.xview_moveto(new_x / max(1, self.total_width))
            self.header_canvas.xview_moveto(self.body_canvas.xview()[0])

        if cell_y0 < y0 + margin_y:
            new_y = max(0, cell_y0 - margin_y)
            self.body_canvas.yview_moveto(new_y / max(1, self.total_height))
            self.row_canvas.yview_moveto(self.body_canvas.yview()[0])
        elif cell_y1 > y1 - margin_y:
            new_y = min(max(0, self.total_height - view_h), cell_y1 - view_h + margin_y)
            self.body_canvas.yview_moveto(new_y / max(1, self.total_height))
            self.row_canvas.yview_moveto(self.body_canvas.yview()[0])

    def _update_scrollregion(self, reset_view=False):
        self.body_canvas.configure(scrollregion=(0, 0, max(1, self.total_width), max(1, self.total_height)))
        self.header_canvas.configure(scrollregion=(0, 0, max(1, self.total_width), self.header_height))
        self.row_canvas.configure(scrollregion=(0, 0, self.row_header_width, max(1, self.total_height)))

        if reset_view:
            self.body_canvas.xview_moveto(0)
            self.body_canvas.yview_moveto(0)
            self.header_canvas.xview_moveto(0)
            self.row_canvas.yview_moveto(0)

    def on_vscroll(self, *args):
        self.body_canvas.yview(*args)
        self.row_canvas.yview(*args)
        self.schedule_render()

    def on_hscroll(self, *args):
        self.body_canvas.xview(*args)
        self.header_canvas.xview(*args)
        self.schedule_render()

    def on_mousewheel(self, event):
        if self.total_rows <= 0:
            return "break"
        step = int(-event.delta / 120)
        if step == 0:
            step = 1 if event.delta < 0 else -1
        self.body_canvas.yview_scroll(step, "units")
        self.row_canvas.yview_moveto(self.body_canvas.yview()[0])
        self.schedule_render()
        return "break"

    def on_mousewheel_linux(self, event):
        if self.total_rows <= 0:
            return "break"
        if event.num == 4:
            self.body_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.body_canvas.yview_scroll(1, "units")
        self.row_canvas.yview_moveto(self.body_canvas.yview()[0])
        self.schedule_render()
        return "break"

    def on_shift_mousewheel(self, event):
        step = int(-event.delta / 120)
        if step == 0:
            step = 1 if event.delta < 0 else -1
        self.body_canvas.xview_scroll(step * 2, "units")
        self.header_canvas.xview_moveto(self.body_canvas.xview()[0])
        self.schedule_render()
        return "break"

    def on_shift_mousewheel_linux(self, event):
        if event.num == 4:
            self.body_canvas.xview_scroll(-2, "units")
        elif event.num == 5:
            self.body_canvas.xview_scroll(2, "units")
        self.header_canvas.xview_moveto(self.body_canvas.xview()[0])
        self.schedule_render()
        return "break"

    def on_resize(self, event):
        self.schedule_render(force=True)

    def schedule_render(self, force=False):
        if force:
            if self._render_job is not None:
                self.after_cancel(self._render_job)
                self._render_job = None
            self.render(force=True)
            return
        if self._render_job is None:
            self._render_job = self.after(1, self._do_render)

    def _do_render(self):
        self._render_job = None
        self.render(force=False)

    def _get_visible_range(self):
        if self.total_cols == 0:
            return None

        x0 = int(self.body_canvas.canvasx(0))
        y0 = int(self.body_canvas.canvasy(0))
        view_w = max(1, self.body_canvas.winfo_width())
        view_h = max(1, self.body_canvas.winfo_height())
        x1 = x0 + view_w
        y1 = y0 + view_h

        first_col = max(0, bisect.bisect_right(self.col_starts, x0) - 1)
        last_col = min(self.total_cols, bisect.bisect_left(self.col_starts, x1) + 1)
        first_row = max(0, bisect.bisect_right(self.row_starts, y0) - 1)
        last_row = min(self.total_rows, bisect.bisect_left(self.row_starts, y1) + 2)

        return x0, y0, view_w, view_h, first_col, last_col, first_row, last_row

    def render(self, force=False):
        self.corner_canvas.delete("all")
        self.corner_canvas.create_rectangle(
            0, 0, self.row_header_width, self.header_height,
            fill="#e9e9e9", outline="#bdbdbd"
        )
        self.corner_canvas.create_text(
            self.row_header_width / 2, self.header_height / 2,
            text="Row", font=self.header_font
        )

        if self.data is None or self.total_cols == 0:
            self.header_canvas.delete("all")
            self.row_canvas.delete("all")
            self.body_canvas.delete("all")
            return

        view = self._get_visible_range()
        if view is None:
            return

        if not force and view == self._last_view:
            return
        self._last_view = view

        _, _, _, _, first_col, last_col, first_row, last_row = view

        self.header_canvas.delete("all")
        self.row_canvas.delete("all")
        self.body_canvas.delete("all")

        for col in range(first_col, last_col):
            col_x = self.col_starts[col]
            width = self.col_widths[col]
            column_name = self.columns[col]

            is_selected_col = column_name == self.selected_column
            is_multi_checked = column_name in self.multi_checked_columns
            fill = "#dbeafe" if is_selected_col else "#f0f0f0"

            self.header_canvas.create_rectangle(
                col_x, 0, col_x + width, self.header_height,
                fill=fill, outline="#bdbdbd"
            )

            text_y = self.header_height / 2
            checkbox_x0 = col_x + width - self.checkbox_margin_right - self.checkbox_size
            checkbox_y0 = (self.header_height - self.checkbox_size) / 2
            checkbox_x1 = checkbox_x0 + self.checkbox_size
            checkbox_y1 = checkbox_y0 + self.checkbox_size

            self.header_canvas.create_text(
                col_x + self.pad_x,
                text_y,
                text=str(column_name),
                anchor="w",
                font=self.header_font
            )

            self.header_canvas.create_rectangle(
                checkbox_x0, checkbox_y0, checkbox_x1, checkbox_y1,
                fill="#ffffff", outline="#666666", width=1
            )
            if is_multi_checked:
                self.header_canvas.create_line(
                    checkbox_x0 + 2, checkbox_y0 + self.checkbox_size * 0.55,
                    checkbox_x0 + self.checkbox_size * 0.42, checkbox_y1 - 2,
                    checkbox_x1 - 2, checkbox_y0 + 2,
                    fill="#2563eb", width=2, smooth=False
                )

        even_fill = "#ffffff"
        odd_fill = "#fbfbfb"
        row_selected_fill = "#eaf3ff"
        col_selected_fill = "#f4f9ff"
        cell_selected_fill = "#ffe58f"

        for row in range(first_row, last_row):
            row_y = self.row_starts[row]
            row_h = self.row_heights[row]
            row_is_selected = (row == self.selected_row)

            row_header_fill = "#dbeafe" if row_is_selected else "#f7f7f7"
            self.row_canvas.create_rectangle(
                0, row_y, self.row_header_width, row_y + row_h,
                fill=row_header_fill, outline="#d0d0d0"
            )
            self.row_canvas.create_text(
                self.row_header_width - 8,
                row_y + row_h / 2,
                text=self.row_labels[row] if row < len(self.row_labels) else str(row),
                anchor="e",
                font=self.font
            )

            row_values = self.data[row]

            for col in range(first_col, last_col):
                col_x = self.col_starts[col]
                width = self.col_widths[col]

                fill = even_fill if (row % 2 == 0) else odd_fill
                if self.columns[col] == self.selected_column:
                    fill = col_selected_fill
                if row_is_selected:
                    fill = row_selected_fill
                if self.selection_range is not None:
                    (r0, r1), (c0, c1) = self.selection_range
                    if r0 <= row <= r1 and c0 <= col <= c1:
                        fill = cell_selected_fill
                elif self.selected_cell == (row, col):
                    fill = cell_selected_fill

                self.body_canvas.create_rectangle(
                    col_x, row_y, col_x + width, row_y + row_h,
                    fill=fill, outline="#e0e0e0"
                )

                if self.selection_range is not None:
                    (r0, r1), (c0, c1) = self.selection_range
                    if r0 <= row <= r1 and c0 <= col <= c1:
                        outline_w = 2 if (row in (r0, r1) or col in (c0, c1)) else 1
                        outline_c = "#d97706" if outline_w == 2 else "#f5c77a"
                        self.body_canvas.create_rectangle(
                            col_x + 1, row_y + 1, col_x + width - 1, row_y + row_h - 1,
                            outline=outline_c, width=outline_w
                        )
                elif self.selected_cell == (row, col):
                    self.body_canvas.create_rectangle(
                        col_x + 1, row_y + 1, col_x + width - 1, row_y + row_h - 1,
                        outline="#d97706", width=2
                    )

                text = row_values[col]
                if len(text) > 80:
                    text = text[:77] + "..."

                self.body_canvas.create_text(
                    col_x + self.pad_x,
                    row_y + row_h / 2,
                    text=text,
                    anchor="w",
                    font=self.font
                )

    def _visible_row_indices(self, limit=300):
        view = self._get_visible_range()
        if view is None:
            return []
        first_row = view[6]
        last_row = min(view[7], first_row + max(1, int(limit)))
        return list(range(first_row, last_row))

    def auto_fit_column(self, col_idx, row_limit=300):
        if not (0 <= col_idx < self.total_cols):
            return
        width = self._header_font.measure(str(self.columns[col_idx])) + 18 + self.checkbox_size + self.checkbox_margin_right
        for row in self._visible_row_indices(limit=row_limit):
            try:
                text = str(self.data[row][col_idx])
            except Exception:
                text = ''
            if len(text) > 120:
                text = text[:120]
            width = max(width, self._cell_font.measure(text) + self.pad_x * 2)
        width = max(self.min_col_width, min(self.max_col_width, int(width)))
        if width != self.col_widths[col_idx]:
            self.col_widths[col_idx] = width
            self._rebuild_column_geometry()
            self._update_scrollregion(reset_view=False)
            self.schedule_render(force=True)

    def auto_fit_row(self, row_idx, col_limit=12):
        if not (0 <= row_idx < self.total_rows):
            return
        sample_cols = range(min(self.total_cols, max(1, int(col_limit))))
        lines = 1
        for col in sample_cols:
            try:
                text = str(self.data[row_idx][col])
            except Exception:
                text = ''
            text = text[:200]
            col_w = max(20, self.col_widths[col] - self.pad_x * 2)
            measured = max(1, self._cell_font.measure(text)) if text else 1
            needed = max(1, int(np.ceil(measured / max(1, col_w))))
            lines = max(lines, min(3, needed))
        new_height = max(self.min_row_height, min(self.max_row_height, int(self._cell_font.metrics('linespace') * lines + 8)))
        if new_height != self.row_heights[row_idx]:
            self.row_heights[row_idx] = new_height
            self._rebuild_row_geometry()
            self._update_scrollregion(reset_view=False)
            self.schedule_render(force=True)

    def on_focus_in(self, event):
        self.body_canvas.configure(highlightbackground="#4a90e2")

    def on_focus_out(self, event):
        self.body_canvas.configure(highlightbackground="#cfcfcf")

    def on_header_click(self, event):
        if self.total_cols == 0:
            return

        resize_col = self._get_header_resize_col(event.x)
        if resize_col is not None:
            self._col_resize_index = resize_col
            self._col_resize_start_x = self.header_canvas.canvasx(event.x)
            self._col_resize_start_width = self.col_widths[resize_col]
            self.header_canvas.configure(cursor='sb_h_double_arrow')
            return

        self.body_canvas.focus_set()

        x = self.header_canvas.canvasx(event.x)
        y = self.header_canvas.canvasy(event.y)
        col = max(0, bisect.bisect_right(self.col_starts, x) - 1)

        if 0 <= col < self.total_cols:
            column_name = self.columns[col]
            width = self.col_widths[col]
            col_x = self.col_starts[col]
            checkbox_x0 = col_x + width - self.checkbox_margin_right - self.checkbox_size
            checkbox_y0 = (self.header_height - self.checkbox_size) / 2
            checkbox_x1 = checkbox_x0 + self.checkbox_size
            checkbox_y1 = checkbox_y0 + self.checkbox_size

            if checkbox_x0 <= x <= checkbox_x1 and checkbox_y0 <= y <= checkbox_y1:
                if self.header_checkbox_toggle_callback:
                    self.header_checkbox_toggle_callback(column_name)
                return

            self.selected_column = column_name
            self.selected_cell = None
            self.selection_anchor = None
            self.selection_range = None
            self.schedule_render(force=True)

            if self.header_click_callback:
                self.header_click_callback(column_name)

    def on_row_click(self, event):
        if self.total_rows == 0:
            return

        self.body_canvas.focus_set()

        row = self._get_row_at_y(event.y)

        if 0 <= row < self.total_rows:
            self.selected_row = row
            self.selected_cell = None
            self.selection_anchor = None
            self.selection_range = None
            self.schedule_render(force=True)

            if self.row_click_callback:
                self.row_click_callback(row)

    def _event_to_cell(self, event):
        x = self.body_canvas.canvasx(event.x)
        y = self.body_canvas.canvasy(event.y)
        col = max(0, bisect.bisect_right(self.col_starts, x) - 1)
        row = bisect.bisect_right(self.row_starts, y) - 1
        if 0 <= row < self.total_rows and 0 <= col < self.total_cols:
            return row, col
        return None

    def _set_selection_range(self, start_row, start_col, end_row, end_col):
        r0, r1 = sorted((int(start_row), int(end_row)))
        c0, c1 = sorted((int(start_col), int(end_col)))
        self.selection_anchor = (start_row, start_col)
        self.selection_range = ((r0, r1), (c0, c1))
        self.selected_cell = (end_row, end_col)
        self.selected_row = end_row
        self.selected_column = self.columns[end_col]

    def on_cell_click(self, event):
        if self.total_rows == 0 or self.total_cols == 0:
            return

        self.body_canvas.focus_set()
        cell = self._event_to_cell(event)
        if cell is None:
            return

        row, col = cell
        self._is_drag_selecting = True
        self._drag_started_cell = (row, col)
        self._set_selection_range(row, col, row, col)
        self.ensure_cell_visible(row, col)
        self.schedule_render(force=True)

    def on_cell_drag(self, event):
        if not self._is_drag_selecting or self.total_rows == 0 or self.total_cols == 0:
            return
        cell = self._event_to_cell(event)
        if cell is None or self.selection_anchor is None:
            return
        row, col = cell
        anchor_row, anchor_col = self.selection_anchor
        self._set_selection_range(anchor_row, anchor_col, row, col)
        self.ensure_cell_visible(row, col)
        self.schedule_render(force=True)

    def on_cell_release(self, event):
        if not self._is_drag_selecting:
            return
        self._is_drag_selecting = False
        if self.selected_cell is None:
            self._drag_started_cell = None
            return

        row, col = self.selected_cell
        preserved_range = self.selection_range
        drag_start = self._drag_started_cell
        self._drag_started_cell = None

        if self.cell_click_callback:
            self.cell_click_callback(row, col, self.columns[col])

        if preserved_range is not None and drag_start is not None and drag_start != (row, col):
            self.selection_anchor = drag_start
            self.selection_range = preserved_range
            self.selected_cell = (row, col)
            self.selected_row = row
            self.selected_column = self.columns[col]
            self.schedule_render(force=True)

    def copy_selection(self, event=None):
        if self.data is None or self.total_rows == 0 or self.total_cols == 0:
            return "break"
        if self.selection_range is not None:
            (r0, r1), (c0, c1) = self.selection_range
        elif self.selected_cell is not None:
            row, col = self.selected_cell
            r0 = r1 = row
            c0 = c1 = col
        else:
            return "break"

        lines = []
        for row in range(r0, r1 + 1):
            values = [str(self.data[row][col]) for col in range(c0, c1 + 1)]
            lines.append("\t".join(values))
        text = "\n".join(lines)
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
        except Exception:
            pass
        return "break"

    def on_key_press(self, event):
        if self.total_rows == 0 or self.total_cols == 0:
            return "break"

        if self.selected_cell is None:
            row, col = 0, 0
        else:
            row, col = self.selected_cell

        key = event.keysym

        if key == "Up":
            row = max(0, row - 1)
        elif key == "Down":
            row = min(self.total_rows - 1, row + 1)
        elif key == "Left":
            col = max(0, col - 1)
        elif key == "Right":
            col = min(self.total_cols - 1, col + 1)
        elif key == "Home":
            col = 0
        elif key == "End":
            col = self.total_cols - 1
        else:
            return

        self.selected_cell = (row, col)
        self.selection_anchor = (row, col)
        self.selection_range = ((row, row), (col, col))
        self.selected_row = row
        self.selected_column = self.columns[col]
        self.ensure_cell_visible(row, col)
        self.schedule_render(force=True)

        if self.cell_click_callback:
            self.cell_click_callback(row, col, self.columns[col])

        return "break"


class CustomNavigationToolbar(NavigationToolbar2Tk):
    toolitems = [item for item in NavigationToolbar2Tk.toolitems if item[0] != "Subplots"]

    def __init__(self, canvas, window, owner=None, **kwargs):
        self.owner = owner
        self._hzoom_icon = None
        super().__init__(canvas, window, **kwargs)
        self._add_span_zoom_button()

    def _create_hzoom_icon(self, width=24, height=24):
        img = tk.PhotoImage(master=self, width=width, height=height)
        # 투명 배경 위에 가로 영역 선택을 연상시키는 아이콘을 그린다.
        blue = "#1f77b4"
        dark = "#0f4c81"
        y0 = height // 2
        for x in range(5, width - 5):
            img.put(blue, (x, y0))
        for x in range(9, width - 9):
            img.put(blue, (x, y0 - 1))
            img.put(blue, (x, y0 + 1))
        # 좌우 브래킷
        for y in range(6, height - 6):
            img.put(dark, (5, y))
            img.put(dark, (width - 6, y))
        for x in range(5, 10):
            img.put(dark, (x, 6))
            img.put(dark, (x, height - 7))
        for x in range(width - 10, width - 5):
            img.put(dark, (x, 6))
            img.put(dark, (x, height - 7))
        return img

    def _add_span_zoom_button(self):
        button = self._Button("HZoom", None, True, self.toggle_span_zoom)
        zoom_button = self._buttons.get("Zoom")

        # 기존 툴바 아이콘 버튼과 최대한 같은 크기/유형으로 맞춘다.
        icon_w, icon_h = 24, 24
        if zoom_button is not None:
            try:
                zoom_img_name = str(zoom_button.cget("image"))
                if zoom_img_name:
                    icon_w = int(self.tk.call("image", "width", zoom_img_name))
                    icon_h = int(self.tk.call("image", "height", zoom_img_name))
            except Exception:
                pass

        self._hzoom_icon = self._create_hzoom_icon(icon_w, icon_h)
        button.configure(image=self._hzoom_icon, text="")

        if zoom_button is not None:
            for opt in ("padx", "pady", "borderwidth", "offrelief", "overrelief", "indicatoron"):
                try:
                    button.configure(**{opt: zoom_button.cget(opt)})
                except Exception:
                    pass

        button.pack_forget()
        save_button = self._buttons.get("Save")
        if save_button is not None and zoom_button is not None:
            button.pack(side=tk.LEFT, before=save_button)
        elif zoom_button is not None:
            button.pack(side=tk.LEFT, after=zoom_button)
        else:
            button.pack(side=tk.LEFT)

        try:
            from matplotlib.backends._backend_tk import add_tooltip
            add_tooltip(button, "Horizontal span zoom")
        except Exception:
            pass

        self._buttons["HZoom"] = button

    def set_span_zoom_checked(self, checked):
        button = self._buttons.get("HZoom")
        if button is not None and hasattr(button, "var"):
            button.var.set(1 if checked else 0)

    def toggle_span_zoom(self):
        button = self._buttons.get("HZoom")
        checked = bool(button.var.get()) if button is not None and hasattr(button, "var") else False
        if self.owner is not None:
            self.owner.toggle_span_zoom_from_toolbar(checked)

    def pan(self, *args):
        if self.owner is not None:
            self.owner.set_span_zoom_active(False)
        super().pan(*args)

    def zoom(self, *args):
        if self.owner is not None:
            self.owner.set_span_zoom_active(False)
        super().zoom(*args)

    def home(self, *args):
        if self.owner is not None:
            self.owner.reset_graph_view()
        else:
            super().home(*args)


class FastCSVViewerWithGraph:
    def __init__(self, parent, app_root=None):
        self.parent = parent
        self.root = app_root if app_root is not None else parent.winfo_toplevel()

        self.df = None
        self.display_data = None
        self.numeric_cache = {}
        self.columns = []
        self.current_channel = None
        self.time_column = None

        self.units = {}
        self.descriptions = {}

        self.selected_graph_row = None
        self.selected_graph_col = None

        self.current_xlim_full = None
        self.current_ylim_full = None
        self.current_view_xlim = None
        self.current_view_ylim = None

        self.multi_channels = []
        self.channel_colors = {}
        self.plot_color_cycle = rcParams.get("axes.prop_cycle", None)
        if self.plot_color_cycle is not None:
            self.plot_color_cycle = self.plot_color_cycle.by_key().get("color", [])
        if not self.plot_color_cycle:
            self.plot_color_cycle = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]

        self.hover_enabled = tk.BooleanVar(value=False)
        self.marker_display_mode = tk.StringVar(value="point_only")
        self.filter_mode = tk.StringVar(value="Raw")
        self.overlay_raw = tk.BooleanVar(value=False)
        self.external_units = {}
        self.external_descriptions = {}
        self.external_lengths = {}
        self.display_row_offset = 0
        self.loaded_metadata = {}
        self.span_zoom_enabled = tk.BooleanVar(value=False)
        self.span_selector = None
        self.filtered_cache = {}

        self.hover_row = None
        self.hover_annotation = None
        self.hover_point_artist = None
        self.channel_extrema_cache = {}

        self.graph_cid = None
        self.graph_motion_cid = None
        self.graph_release_cid = None
        self.graph_scroll_cid = None
        self.is_graph_dragging = False
        self.graph_drag_motion_skip = 3
        self._graph_drag_motion_counter = 0

        self.zoom_span_artist = None

        self._build_ui()
        self._bind_graph_events()

    def _build_ui(self):
        top_frame = tk.Frame(self.parent)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        open_button = tk.Button(top_frame, text="DATA LOAD(DAT/CSV)", command=self.load_dat)
        open_button.pack(side=tk.LEFT)

        self.file_label = tk.Label(top_frame, text="선택된 파일 없음", anchor="w")
        self.file_label.pack(side=tk.LEFT, padx=10)

        self.channel_label = tk.Label(top_frame, text="선택 채널: 없음", anchor="w")
        self.channel_label.pack(side=tk.RIGHT, padx=10)

        self.main_pane = tk.PanedWindow(self.parent, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 0))

        left_frame = tk.Frame(self.main_pane)
        self.main_pane.add(left_frame, stretch="always", minsize=700)

        multi_top = tk.Frame(left_frame)
        multi_top.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(0, 4))
        tk.Label(multi_top, text="헤더 체크로 멀티 채널 선택").pack(side=tk.LEFT)
        tk.Button(multi_top, text="멀티 해제", command=self.clear_multi_channels).pack(side=tk.RIGHT)


        self.grid_table = FastCanvasTable(
            left_frame,
            header_click_callback=self.on_column_click,
            row_click_callback=self.on_row_click,
            cell_click_callback=self.on_cell_click,
            header_checkbox_toggle_callback=self.on_header_multi_toggle
        )
        self.grid_table.pack(fill=tk.BOTH, expand=True)

        right_frame = tk.Frame(self.main_pane)
        self.main_pane.add(right_frame, minsize=500)

        
        graph_ctrl = tk.Frame(right_frame)
        graph_ctrl.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(4, 4))

        tk.Label(graph_ctrl, text="포인트 찍기:").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Radiobutton(
            graph_ctrl,
            text="포인트",
            value="point_only",
            variable=self.marker_display_mode,
            command=self.on_marker_display_mode_changed
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            graph_ctrl,
            text="포인트+라인",
            value="point_line",
            variable=self.marker_display_mode,
            command=self.on_marker_display_mode_changed
        ).pack(side=tk.LEFT, padx=(2, 10))

        ttk.Checkbutton(
            graph_ctrl,
            text="Cursor Value",
            variable=self.hover_enabled,
            command=self.on_hover_toggle_changed
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(graph_ctrl, text="Filter:").pack(side=tk.LEFT, padx=(8, 4))
        self.filter_combo = ttk.Combobox(
            graph_ctrl,
            width=10,
            state="readonly",
            textvariable=self.filter_mode,
            values=("Raw", "CFC 60", "CFC 180", "CFC 600", "CFC 1000")
        )
        self.filter_combo.pack(side=tk.LEFT)
        self.filter_combo.bind("<<ComboboxSelected>>", self.on_filter_option_changed)

        ttk.Checkbutton(
            graph_ctrl,
            text="Raw 겹쳐보기",
            variable=self.overlay_raw,
            command=self.on_filter_option_changed
        ).pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(graph_ctrl, text="그래프 저장", command=self.save_current_graph).pack(side=tk.RIGHT, padx=(6, 0))
        tk.Button(graph_ctrl, text="새로고침", command=self.refresh_current_graph).pack(side=tk.RIGHT)

        self.figure = Figure(figsize=(6.3, 5.8), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("채널을 선택하세요")
        self.ax.set_xlabel(self.get_x_axis_label())
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self._apply_x_locator()

        self.canvas = FigureCanvasTkAgg(self.figure, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.get_tk_widget().bind("<Left>", self.on_graph_left_key)
        self.canvas.get_tk_widget().bind("<Right>", self.on_graph_right_key)

        toolbar_frame = tk.Frame(right_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        self.toolbar = CustomNavigationToolbar(self.canvas, toolbar_frame, owner=self, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(side=tk.LEFT, fill=tk.X)

        self.toolbar.set_span_zoom_checked(False)

        self.status_var = tk.StringVar(value="준비")
        status_bar = tk.Label(
            self.parent,
            textvariable=self.status_var,
            anchor="w",
            bd=1,
            relief=tk.SUNKEN,
            padx=8,
            pady=3
        )
        self.status_bar = status_bar
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.bind("<Escape>", self.on_escape_key)


    def _format_cursor_number(self, value, decimals=4):
        try:
            value = float(value)
        except Exception:
            return "-"
        if not np.isfinite(value):
            return "-"
        return f"{value:.{decimals}f}"

    def _get_channel_extrema(self, channel_name):
        if not channel_name:
            return None
        if channel_name in self.channel_extrema_cache:
            return self.channel_extrema_cache[channel_name]

        x_all = self.get_numeric_column(self.time_column)
        y_all = self.get_plot_series(channel_name)
        if x_all is None or y_all is None or len(x_all) != len(y_all):
            self.channel_extrema_cache[channel_name] = None
            return None

        finite_mask = np.isfinite(x_all) & np.isfinite(y_all)
        if not np.any(finite_mask):
            self.channel_extrema_cache[channel_name] = None
            return None

        valid_idx = np.flatnonzero(finite_mask)
        valid_y = y_all[finite_mask]
        max_pos = int(np.argmax(valid_y))
        min_pos = int(np.argmin(valid_y))
        max_idx = int(valid_idx[max_pos])
        min_idx = int(valid_idx[min_pos])
        info = {
            "max_value": float(y_all[max_idx]),
            "max_time": float(x_all[max_idx]),
            "min_value": float(y_all[min_idx]),
            "min_time": float(x_all[min_idx]),
        }
        self.channel_extrema_cache[channel_name] = info
        return info

    def refresh_current_graph(self):
        if self.df is None:
            self.clear_graph()
            return

        self.filter_mode.set("Raw")
        self.overlay_raw.set(False)
        self.current_view_xlim = None
        self.current_view_ylim = None
        self.channel_extrema_cache.clear()

        if self.current_channel is not None or self.multi_channels:
            self.plot_channel(selected_row=self.selected_graph_row, preserve_view=False)
        else:
            self.clear_graph()

    def save_current_graph(self):
        initial = self.current_channel or 'viewer_graph'
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
            self.status_var.set(f'그래프 저장 완료: {os.path.basename(path)}')
            messagebox.showinfo('완료', '그래프를 저장했습니다.')
        except Exception as exc:
            messagebox.showerror('오류', f'그래프 저장 중 오류가 발생했습니다.\n{exc}')

    def _bind_graph_events(self):
        self.graph_cid = self.canvas.mpl_connect("button_press_event", self.on_graph_click)
        self.graph_motion_cid = self.canvas.mpl_connect("motion_notify_event", self.on_graph_motion)
        self.graph_release_cid = self.canvas.mpl_connect("button_release_event", self.on_graph_release)
        self.graph_scroll_cid = self.canvas.mpl_connect("scroll_event", self.on_graph_scroll)
        self._init_span_selector()

    def _init_span_selector(self):
        if self.span_selector is None:
            self.span_selector = SpanSelector(
                self.ax,
                self.on_span_select_zoom,
                "horizontal",
                useblit=True,
                props=dict(alpha=0.25, facecolor="#60a5fa", edgecolor="#2563eb"),
                interactive=False,
                drag_from_anywhere=False,
                button=1,
                ignore_event_outside=True
            )
        self.span_selector.set_active(self.span_zoom_enabled.get())

    def _rebuild_span_selector(self):
        active = bool(self.span_zoom_enabled.get())
        if self.span_selector is not None:
            try:
                self.span_selector.disconnect_events()
            except Exception:
                pass
            try:
                self.span_selector.set_visible(False)
            except Exception:
                pass
            self.span_selector = None
        self._init_span_selector()
        if self.span_selector is not None:
            self.span_selector.set_active(active)

    def set_span_zoom_active(self, active):
        active = bool(active)
        self.span_zoom_enabled.set(active)
        if self.span_selector is not None:
            self.span_selector.set_active(active)
        if hasattr(self, "toolbar") and self.toolbar is not None:
            self.toolbar.set_span_zoom_checked(active)

    def toggle_span_zoom_from_toolbar(self, active):
        active = bool(active)
        if active:
            mode = getattr(self.toolbar, "mode", "")
            if mode:
                if "PAN" in str(mode).upper():
                    self.toolbar.pan()
                elif "ZOOM" in str(mode).upper():
                    self.toolbar.zoom()
        self.set_span_zoom_active(active)

    def on_span_select_zoom(self, xmin, xmax):
        if not self.span_zoom_enabled.get():
            return
        if self.current_channel is None and not self.multi_channels:
            return
        if xmin is None or xmax is None:
            return
        if abs(xmax - xmin) < 1e-12:
            return

        x0, x1 = sorted((xmin, xmax))
        cur_y0, cur_y1 = self.ax.get_ylim()
        x0, x1, cur_y0, cur_y1 = self._clamp_view_to_full(x0, x1, cur_y0, cur_y1)
        self.ax.set_xlim(x0, x1)
        self.ax.set_ylim(cur_y0, cur_y1)
        self._apply_x_locator(abs(x1 - x0))
        self.current_view_xlim = self.ax.get_xlim()
        self.current_view_ylim = self.ax.get_ylim()
        self.canvas.draw_idle()
        # 일부 환경에서는 SpanSelector가 1회 동작 후 멈추므로 재생성해 연속 확대를 보장한다.
        self.root.after_idle(self._rebuild_span_selector)

    def find_time_column(self):
        if self.df is None:
            return None

        for col in self.df.columns:
            if str(col).strip().lower() == "time":
                return col
        for col in self.df.columns:
            if "time" in str(col).strip().lower():
                return col
        return self.df.columns[0] if len(self.df.columns) > 0 else None

    def extract_metadata_rows(self):
        self.units = dict(getattr(self, "external_units", {}) or {})
        self.descriptions = dict(getattr(self, "external_descriptions", {}) or {})

        if self.df is None or self.df.empty:
            return

        scan_rows = min(30, len(self.df))

        for i in range(scan_rows):
            first_val = str(self.df.iloc[i, 0]).strip().lower()

            if "engineering" in first_val and "unit" in first_val:
                row = self.df.iloc[i]
                for col, val in zip(self.df.columns, row):
                    txt = str(val).strip()
                    if txt.lower() == "nan":
                        txt = ""
                    if txt:
                        self.units[col] = txt

            if "channel" in first_val and "description" in first_val:
                row = self.df.iloc[i]
                for col, val in zip(self.df.columns, row):
                    txt = str(val).strip()
                    if txt.lower() == "nan":
                        txt = ""
                    if txt:
                        self.descriptions[col] = txt

    def get_x_axis_label(self):
        unit = self.units.get(self.time_column, "").strip() if self.time_column else ""
        return f"Time({unit})" if unit else "Time"

    def _normalize_unit_display(self, unit_text):
        unit = str(unit_text or "").strip()
        if not unit or unit == '-':
            return "Value"
        return unit

    def get_y_axis_label(self, column_name):
        unit = self.units.get(column_name, "").strip()
        return self._normalize_unit_display(unit)

    def get_stored_filter_label(self, column_name):
        metadata = dict(getattr(self, "loaded_metadata", {}) or {})
        labels = dict(metadata.get("channel_filter_labels") or {})
        return str(labels.get(column_name) or "Raw").strip() or "Raw"

    def _normalize_filter_display_label(self, label_text, fallback="Raw"):
        label = str(label_text or "").strip()
        if not label or label == '-':
            return fallback
        upper = label.upper()
        idx = upper.find("CFC")
        if idx >= 0:
            return label[idx:].strip()
        return label

    def _infer_filter_display_label_from_name(self, column_name):
        name = str(column_name or "")
        upper = name.upper()
        idx = upper.rfind("_CFC")
        if idx >= 0:
            suffix = name[idx + 1:].replace('_', ' ').strip()
            parsed = self._normalize_filter_display_label(suffix, fallback="")
            if parsed:
                return parsed
        return ""

    def get_stored_filter_display_label(self, column_name):
        stored_label = self.get_stored_filter_label(column_name)
        metadata = dict(getattr(self, "loaded_metadata", {}) or {})
        derived = dict(metadata.get("derived_channels") or {})
        info = dict(derived.get(column_name) or {})
        required_cfc = self._normalize_filter_display_label(info.get("required_cfc"), fallback="")
        if required_cfc:
            return required_cfc
        display_label = self._normalize_filter_display_label(info.get("display_filter_label"), fallback="")
        if display_label:
            return display_label
        derived_filter = self._normalize_filter_display_label(info.get("filter_label"), fallback="")
        if derived_filter and derived_filter != "CALC":
            return derived_filter
        stored_display = self.get_filter_display_label(stored_label)
        if stored_display != "Raw":
            return self._normalize_filter_display_label(stored_display)
        inferred = self._infer_filter_display_label_from_name(column_name)
        if inferred:
            return inferred
        return "Raw"

    def get_effective_filter_label(self, column_name=None, filter_label=None):
        active_label = str(filter_label or self.get_filter_label() or "Raw").strip() or "Raw"
        if active_label != "Raw":
            return active_label
        if column_name is None:
            return "Raw"
        return self.get_stored_filter_label(column_name)

    def get_current_filter_title_label(self, column_name=None):
        if column_name is None:
            return self.get_filter_display_label(self.get_effective_filter_label(column_name))
        active_label = str(self.get_filter_label() or "Raw").strip() or "Raw"
        if active_label != "Raw":
            return self.get_filter_display_label(active_label)
        return self.get_stored_filter_display_label(column_name)

    def _get_derived_channel_info(self, column_name):
        metadata = dict(getattr(self, "loaded_metadata", {}) or {})
        derived = dict(metadata.get("derived_channels") or {})
        return dict(derived.get(column_name) or {})

    def is_calculated_channel(self, column_name):
        info = self._get_derived_channel_info(column_name)
        calc_label = str(info.get("calculation_label") or info.get("filter_label") or "").strip().upper()
        if calc_label == "CALC":
            return True
        stored_label = str(self.get_stored_filter_label(column_name) or "").strip().upper()
        return stored_label == "CALC"

    def get_title_channel_name(self, column_name):
        name = str(column_name)
        if self.is_calculated_channel(column_name) and not name.endswith("_CALC"):
            return f"{name}_CALC"
        return name

    def get_plot_title(self, column_name, filter_label=None):
        unit = self._normalize_unit_display(self.units.get(column_name, "").strip())
        effective_filter = self._normalize_filter_display_label(self.get_current_filter_title_label(column_name), fallback="Raw")
        title_name = self.get_title_channel_name(column_name)
        filter_suffix = "" if effective_filter == "Raw" else f" [{effective_filter}]"
        return f"{title_name} [{unit}]{filter_suffix}"

    def get_channel_display_name(self, column_name):
        desc = self.descriptions.get(column_name, "").strip()
        if desc:
            return desc
        return str(column_name)

    def get_numeric_column(self, column_name):
        if column_name in self.numeric_cache:
            return self.numeric_cache[column_name]
        arr = pd.to_numeric(self.df[column_name], errors="coerce").to_numpy()
        self.numeric_cache[column_name] = arr
        return arr

    def get_standard_label(self):
        return str((getattr(self, "loaded_metadata", {}) or {}).get("standard_label", "") or "").strip()

    def get_filter_label(self):
        return self.filter_mode.get().strip() or "Raw"

    def get_filter_display_label(self, filter_label=None, standard_label=None):
        label = str(filter_label or self.get_filter_label() or "Raw").strip() or "Raw"
        return "Raw" if label == "Raw" else label

    def _get_filter_cache_key(self, column_name, filter_label=None, standard_label=None):
        label = filter_label or self.get_filter_label()
        return (column_name, label)

    def _get_sample_rate(self, x_all):
        return cfc_get_sample_rate(x_all)

    def _apply_cfc_filter_segment(self, y_segment, fs, cfc_value, standard_label=None):
        return cfc_filter_segment(y_segment, fs, cfc_value)

    def get_plot_series(self, column_name, filter_label=None):
        if self.df is None or column_name is None:
            return None

        label = filter_label or self.get_filter_label()
        if label == "Raw":
            return self.get_numeric_column(column_name)

        cache_key = self._get_filter_cache_key(column_name, label)
        if cache_key in self.filtered_cache:
            return self.filtered_cache[cache_key]

        raw_y = self.get_numeric_column(column_name)
        x_all = self.get_numeric_column(self.time_column)
        filtered = raw_y.astype(float).copy()

        try:
            cfc_value = int(label.replace("CFC", "").strip())
        except Exception:
            self.filtered_cache[cache_key] = filtered
            return filtered

        fs = self._get_sample_rate(x_all)
        valid = np.isfinite(x_all) & np.isfinite(raw_y)
        if not np.any(valid):
            self.filtered_cache[cache_key] = filtered
            return filtered

        idx = np.flatnonzero(valid)
        split_points = np.where(np.diff(idx) > 1)[0] + 1
        groups = np.split(idx, split_points)
        for grp in groups:
            if grp.size < 8:
                continue
            filtered[grp] = self._apply_cfc_filter_segment(raw_y[grp].astype(float), fs, cfc_value)

        self.filtered_cache[cache_key] = filtered
        return filtered

    def on_filter_option_changed(self, event=None):
        if self.df is None:
            return
        if self.current_channel is not None or self.multi_channels:
            self.plot_channel(selected_row=self.selected_graph_row, preserve_view=True)

    def format_value(self, value):
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass

        if isinstance(value, (int, np.integer)):
            return str(int(value))

        if isinstance(value, (float, np.floating)):
            if np.isfinite(value):
                return f"{value:.6g}"
            return str(value)

        return str(value)

    def _prepare_plot_data(self, x, y):
        return x, y

    def _build_display_dataframe_and_labels(self, metadata=None):
        metadata = metadata or {}
        display_df = self.df.copy()
        self.display_meta_rows = []
        if str(metadata.get("source_format", "")).upper() == "DAT":
            display_df = display_df.fillna(0)
        else:
            display_df = display_df.replace({np.nan: ""})

        meta_rows = []
        if self.columns:
            unit_row = [self.units.get(col, "") for col in self.columns]
            filter_labels = dict((metadata.get("channel_filter_labels") or getattr(self, "loaded_metadata", {}).get("channel_filter_labels") or {}))
            filter_row = [str(filter_labels.get(col, "Raw") or "Raw") for col in self.columns]
            length_row = [str(self.get_channel_length(col) or "") for col in self.columns]
            meta_rows.append(unit_row)
            meta_rows.append(filter_row)
            meta_rows.append(length_row)
            self.display_meta_rows = ["UNIT", "FILTER", "Length"]

        data_rows = display_df.astype(str).to_numpy(copy=True)
        if meta_rows:
            meta_array = np.array(meta_rows, dtype=object)
            if data_rows.size == 0:
                display_data = meta_array.astype(str)
            else:
                display_data = np.vstack([meta_array, data_rows]).astype(str)
            row_labels = ["UNIT", "FILTER", "Length"] + [str(i) for i in range(len(display_df))]
            self.display_row_offset = len(meta_rows)
        else:
            display_data = data_rows
            row_labels = [str(i) for i in range(len(display_df))]
            self.display_row_offset = 0

        return display_data, row_labels


    def _is_meta_display_row(self, row_idx):
        if row_idx is None:
            return False
        return 0 <= int(row_idx) < int(getattr(self, "display_row_offset", 0) or 0)

    def _display_row_to_data_row(self, row_idx):
        if row_idx is None:
            return None
        data_row = int(row_idx) - int(getattr(self, "display_row_offset", 0) or 0)
        if self.df is None or data_row < 0 or data_row >= len(self.df):
            return None
        return data_row

    def _data_row_to_display_row(self, row_idx):
        if row_idx is None:
            return None
        return int(row_idx) + int(getattr(self, "display_row_offset", 0) or 0)

    def _update_standard_info_label(self):
        return

    def update_status_bar(self, row_idx=None, col_idx=None):
        if self.df is None or row_idx is None or col_idx is None:
            self.status_var.set("준비")
            return

        data_row = self._display_row_to_data_row(row_idx)
        if data_row is None or not (0 <= col_idx < len(self.columns)):
            if 0 <= col_idx < len(self.columns) and 0 <= row_idx < len(getattr(self, "display_data", []) or []):
                col_name = self.columns[col_idx]
                cell_value = self.display_data[row_idx][col_idx]
                row_label = self.grid_table.row_labels[row_idx]
                suffix = " (metadata)" if self._is_meta_display_row(row_idx) else ""
                self.status_var.set(f"Row: {row_label}{suffix} | Column: {col_name} | Value: {cell_value}")
            else:
                self.status_var.set("준비")
            return

        col_name = self.columns[col_idx]
        raw_value = self.df.iloc[data_row, col_idx]
        value_text = self.format_value(raw_value)

        desc = self.descriptions.get(col_name, "").strip()
        unit = self.units.get(col_name, "").strip()

        time_text = ""
        if self.time_column is not None and data_row < len(self.df):
            try:
                time_val = self.df.loc[data_row, self.time_column]
                time_text = self.format_value(time_val)
            except Exception:
                time_text = ""

        parts = [
            f"Row: {data_row}",
            f"Column: {col_name}"
        ]

        if desc:
            parts.append(f"Desc: {desc}")

        parts.append(f"Value: {value_text}")

        if unit:
            parts.append(f"Unit: {unit}")

        if time_text != "":
            parts.append(f"Time: {time_text} s")

        self.status_var.set(" | ".join(parts))

    def get_channel_length(self, column_name):
        if not column_name:
            return None
        length = self.external_lengths.get(column_name)
        if length not in (None, ""):
            try:
                return int(length)
            except Exception:
                pass
        if self.df is not None and column_name in getattr(self, "columns", []):
            try:
                return int(len(self.df[column_name]))
            except Exception:
                return None
        return None

    def update_metadata_info(self, column_name=None):
        self._update_standard_info_label()

    def _apply_loaded_dataframe(self, loaded_df, file_path, metadata=None):
        loaded_df = loaded_df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
        self.file_label.config(text=file_path)

        if loaded_df.empty:
            messagebox.showwarning("경고", "DAT 파일에 데이터가 없습니다.")
            return False

        self.df = loaded_df
        self.columns = list(self.df.columns)
        self.numeric_cache.clear()
        self.filtered_cache.clear()
        self.current_channel = None
        self.selected_graph_row = None
        self.selected_graph_col = None
        self.current_xlim_full = None
        self.current_ylim_full = None
        self.multi_channels = []
        self.channel_colors = {}
        self.hover_row = None
        self.filter_mode.set("Raw")
        self.overlay_raw.set(False)
        self.set_span_zoom_active(False)

        metadata = metadata or {}
        self.loaded_metadata = dict(metadata)
        self.external_units = dict(metadata.get("units", {}) or {})
        self.external_descriptions = dict(metadata.get("descriptions", {}) or {})
        self.external_lengths = dict(metadata.get("lengths", {}) or {})
        self.time_column = metadata.get("time_column") or self.find_time_column()
        self.extract_metadata_rows()

        self.display_data, row_labels = self._build_display_dataframe_and_labels(metadata)

        self.grid_table.set_data(self.columns, self.display_data, row_labels=row_labels)
        self.grid_table.set_multi_checked_columns(self.multi_channels)
        self.refresh_multi_channel_ui()
        self.clear_graph()
        self.update_metadata_info()
        self.update_status_bar()
        return True

    def load_dat(self):
        file_path = filedialog.askopenfilename(
            title="데이터 파일 선택",
            filetypes=[
                ("Supported files", f"*.dat *.csv *{DATASET_EXT}"),
                ("DAT files", "*.dat"),
                ("CSV files", "*.csv"),
                ("Saved dataset", f"*{DATASET_EXT}"),
                ("All files", "*.*"),
            ]
        )

        if not file_path:
            return

        suffix = file_path.lower()
        try:
            if suffix.endswith('.dat'):
                loaded_df, metadata = load_dat_file(file_path)
                self._apply_loaded_dataframe(loaded_df, file_path, metadata=metadata)
            elif suffix.endswith('.csv'):
                preview_df = load_csv_preview(file_path)
                dialog = RowHideDialog(self.root, preview_df, preview_count=min(60, len(preview_df)))
                if dialog.result is None:
                    return
                hidden_rows = list(dialog.result.get("hidden_rows", []))
                loaded_df, metadata = load_csv_file(file_path, hidden_rows=hidden_rows)
                self._apply_loaded_dataframe(loaded_df, file_path, metadata=metadata)
            elif suffix.endswith(DATASET_EXT):
                payload = load_dataset_pickle(file_path)
                self._apply_loaded_dataframe(payload['dataframe'], file_path, metadata=payload.get('metadata'))
                self.loaded_history = list(payload.get('history') or [])
            else:
                messagebox.showwarning("안내", "지원하지 않는 파일 형식입니다.")
        except DatLoadError as e:
            messagebox.showerror("DAT 로드 오류", str(e))
        except CsvLoadError as e:
            messagebox.showerror("CSV 로드 오류", str(e))
        except DatasetStoreError as e:
            messagebox.showerror("임시 데이터 로드 오류", str(e))
        except Exception as e:
            messagebox.showerror("오류", f"데이터 파일을 읽는 중 오류가 발생했습니다.\n\n{e}")

    def load_csv(self):
        self.load_dat()

    def _apply_x_locator(self, span=None):
        if span is None:
            try:
                xmin, xmax = self.ax.get_xlim()
                span = abs(xmax - xmin)
            except Exception:
                span = None

        if span is None or not np.isfinite(span) or span <= 0:
            try:
                self.ax.xaxis.set_major_locator(MultipleLocator(0.5))
            except Exception:
                self.ax.xaxis.set_major_locator(MaxNLocator(nbins=10))
            self.ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:g}"))
            return

        target_ticks = 8
        raw_step = span / target_ticks
        nice_steps = [
            0.001, 0.002, 0.005,
            0.01, 0.02, 0.05,
            0.1, 0.2, 0.5,
            1, 2, 5,
            10, 20, 50,
            100, 200, 500,
            1000
        ]
        step = nice_steps[-1]
        for s in nice_steps:
            if raw_step <= s:
                step = s
                break

        try:
            self.ax.xaxis.set_major_locator(MultipleLocator(step))
        except Exception:
            self.ax.xaxis.set_major_locator(MaxNLocator(nbins=target_ticks))

        if step >= 1:
            self.ax.xaxis.set_major_formatter(
                FuncFormatter(lambda x, pos: f"{x:.0f}" if abs(x - round(x)) < 1e-9 else f"{x:g}")
            )
        elif step >= 0.1:
            self.ax.xaxis.set_major_formatter(
                FuncFormatter(lambda x, pos: f"{x:.1f}".rstrip("0").rstrip("."))
            )
        elif step >= 0.01:
            self.ax.xaxis.set_major_formatter(
                FuncFormatter(lambda x, pos: f"{x:.2f}".rstrip("0").rstrip("."))
            )
        elif step >= 0.001:
            self.ax.xaxis.set_major_formatter(
                FuncFormatter(lambda x, pos: f"{x:.3f}".rstrip("0").rstrip("."))
            )
        else:
            self.ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:g}"))

    def on_column_click(self, column_name):
        if self.df is None:
            return

        self.selected_graph_row = None
        self.selected_graph_col = None
        self.update_status_bar()

        if self.time_column is None:
            messagebox.showwarning("경고", "Time 열을 찾을 수 없습니다.")
            return

        if column_name == self.time_column:
            self.current_channel = None
            self.channel_label.config(text=f"선택 채널: {column_name} (시간축)")
            self.clear_graph()
            return

        self.current_channel = column_name
        self.current_view_xlim = None
        self.current_view_ylim = None
        self._update_channel_label(column_name)
        self.update_metadata_info(column_name)
        self.plot_channel(selected_row=None, preserve_view=False)

    def on_row_click(self, row_idx):
        if self.df is None:
            return

        self.grid_table.set_selected_row(row_idx)
        self.update_metadata_info(self.current_channel)

        if self._is_meta_display_row(row_idx):
            self.selected_graph_row = None
            if self.current_channel is not None:
                self.plot_channel(selected_row=None, preserve_view=True)
            self.status_var.set(f"Row: {self.grid_table.row_labels[row_idx]} (metadata)")
            return

        if self.current_channel is not None:
            try:
                col_idx = self.columns.index(self.current_channel)
                self.update_status_bar(row_idx, col_idx)
            except ValueError:
                self.status_var.set(f"Row: {self.grid_table.row_labels[row_idx]}")
        else:
            self.status_var.set(f"Row: {self.grid_table.row_labels[row_idx]}")

    def on_cell_click(self, row_idx, col_idx, column_name):
        if self.df is None:
            return

        self.grid_table.set_selected_cell(row_idx, col_idx)
        self.update_status_bar(row_idx, col_idx)

        data_row = self._display_row_to_data_row(row_idx)
        if data_row is None:
            self.selected_graph_row = None
            self.selected_graph_col = None
            if self.current_channel is not None:
                self.plot_channel(selected_row=None, preserve_view=True)
            if column_name != self.time_column:
                self.current_channel = column_name
                self._update_channel_label(column_name)
            return

        if self.time_column is None or column_name == self.time_column:
            self.selected_graph_row = None
            self.selected_graph_col = None
            if column_name == self.time_column:
                self.current_channel = None
            return

        preserve_view = (
            column_name == self.current_channel
            and self.current_view_xlim is not None
            and self.current_view_ylim is not None
        )
        self.current_channel = column_name
        if not preserve_view:
            self.current_view_xlim = None
            self.current_view_ylim = None
        self.selected_graph_row = data_row
        self.selected_graph_col = column_name
        self._update_channel_label(column_name)
        self.update_metadata_info(column_name)
        self.plot_channel(selected_row=data_row, preserve_view=preserve_view)

    def _update_channel_label(self, column_name):
        desc = self.descriptions.get(column_name, "").strip()
        unit = self.units.get(column_name, "").strip()

        if desc and unit:
            self.channel_label.config(text=f"선택 채널: {desc} [{unit}]")
        elif desc:
            self.channel_label.config(text=f"선택 채널: {desc}")
        elif unit:
            self.channel_label.config(text=f"선택 채널: {column_name} [{unit}]")
        else:
            self.channel_label.config(text=f"선택 채널: {column_name}")

    def refresh_multi_channel_ui(self):
        selected_names = [self.get_channel_display_name(ch) for ch in self.multi_channels]
        if selected_names:
            self.channel_label.config(text=f"선택 채널: {self.get_channel_display_name(self.current_channel) if self.current_channel else '없음'} | 멀티: {', '.join(selected_names[:4])}{' ...' if len(selected_names) > 4 else ''}")
        elif self.current_channel is not None:
            self._update_channel_label(self.current_channel)
        self.update_metadata_info(self.current_channel)

    def on_header_multi_toggle(self, column_name):
        if self.time_column is not None and column_name == self.time_column:
            return
        if column_name in self.multi_channels:
            self.multi_channels.remove(column_name)
        else:
            self.multi_channels.append(column_name)
            if self.current_channel is None or self.current_channel == self.time_column:
                self.current_channel = column_name
                self._update_channel_label(column_name)

        if self.current_channel == column_name and column_name not in self.multi_channels and not self.get_channels_to_plot():
            self.current_channel = None

        self.grid_table.set_multi_checked_columns(self.multi_channels)
        self.refresh_multi_channel_ui()
        if self.current_channel is not None or self.multi_channels:
            self.plot_channel(selected_row=self.selected_graph_row, preserve_view=True)
        else:
            self.clear_graph()

        self._remove_zoom_span()
        self.plot_channel(selected_row=self.selected_graph_row)
    def clear_multi_channels(self):
        self.multi_channels = []
        self.grid_table.set_multi_checked_columns(self.multi_channels)
        self.refresh_multi_channel_ui()
        if self.current_channel is not None:
            self.plot_channel(selected_row=self.selected_graph_row, preserve_view=True)
        else:
            self.clear_graph()

    def get_channels_to_plot(self):
        channels = []
        for ch in self.multi_channels:
            if ch != self.time_column and ch not in channels:
                channels.append(ch)
        if self.current_channel is not None and self.current_channel != self.time_column and self.current_channel not in channels:
            channels.append(self.current_channel)
        return channels

    def _get_channel_color(self, channel_name):
        color = self.channel_colors.get(channel_name)
        if color is not None:
            return color
        color = self.plot_color_cycle[len(self.channel_colors) % len(self.plot_color_cycle)]
        self.channel_colors[channel_name] = color
        return color

    def _find_nearest_valid_row(self, x_clicked, channel_name):
        if self.df is None or self.time_column is None or channel_name is None:
            return None

        x_all = self.get_numeric_column(self.time_column)
        y_all = self.get_plot_series(channel_name)
        valid_mask = np.isfinite(x_all) & np.isfinite(y_all)
        valid_rows = np.flatnonzero(valid_mask)
        if len(valid_rows) == 0:
            return None

        x_valid = x_all[valid_rows]
        pos = int(np.searchsorted(x_valid, x_clicked, side="left"))

        candidates = []
        if pos < len(valid_rows):
            candidates.append(valid_rows[pos])
        if pos > 0:
            candidates.append(valid_rows[pos - 1])
        if not candidates:
            return None

        nearest_row = min(candidates, key=lambda idx: abs(x_all[idx] - x_clicked))
        return int(nearest_row)

    def _graph_interaction_allowed(self):
        return hasattr(self.toolbar, "mode") and not self.toolbar.mode and not self.span_zoom_enabled.get()

    def _select_row_from_graph_x(self, xdata, preserve_view=True):
        row_idx = self._find_nearest_valid_row(xdata, self.current_channel)
        if row_idx is None:
            return

        try:
            col_idx = self.columns.index(self.current_channel)
        except ValueError:
            return

        self.grid_table.set_selected_cell(self._data_row_to_display_row(row_idx), col_idx)
        self.selected_graph_row = row_idx
        self.selected_graph_col = self.current_channel
        self.update_status_bar(self._data_row_to_display_row(row_idx), col_idx)
        self.plot_channel(selected_row=row_idx, preserve_view=preserve_view)

    def _remove_zoom_span(self):
        if self.zoom_span_artist is not None:
            try:
                self.zoom_span_artist.remove()
            except Exception:
                pass
            self.zoom_span_artist = None

    def on_graph_click(self, event):
        self.canvas.get_tk_widget().focus_set()

        if event.inaxes != self.ax:
            return
        if self.df is None or self.time_column is None:
            return
        if event.xdata is None:
            return
        if not self._graph_interaction_allowed():
            return

        if self.span_zoom_enabled.get() and event.button == 1:
            return

        if self.current_channel is None:
            return

        if event.button != 1:
            return

        self.is_graph_dragging = True
        self._graph_drag_motion_counter = 0
        self._select_row_from_graph_x(event.xdata, preserve_view=True)

    def on_graph_motion(self, event):
        if event.inaxes == self.ax and self.current_channel is not None and not self.span_zoom_enabled.get():
            if self.is_graph_dragging and event.xdata is not None and self._graph_interaction_allowed():
                self._graph_drag_motion_counter += 1
                if self._graph_drag_motion_counter >= max(1, int(self.graph_drag_motion_skip)):
                    self._graph_drag_motion_counter = 0
                    self._select_row_from_graph_x(event.xdata, preserve_view=True)

        self.update_hover_annotation(event)

    def on_graph_release(self, event):
        self.is_graph_dragging = False
        self._graph_drag_motion_counter = 0

    def _clamp_view_to_full(self, x0, x1, y0, y1):
        if self.current_xlim_full is not None:
            full_x0, full_x1 = self.current_xlim_full
            full_w = full_x1 - full_x0
            view_w = x1 - x0
            if view_w >= full_w:
                x0, x1 = full_x0, full_x1
            else:
                if x0 < full_x0:
                    x1 += (full_x0 - x0)
                    x0 = full_x0
                if x1 > full_x1:
                    x0 -= (x1 - full_x1)
                    x1 = full_x1

        if self.current_ylim_full is not None:
            full_y0, full_y1 = self.current_ylim_full
            full_h = full_y1 - full_y0
            view_h = y1 - y0
            if view_h >= full_h:
                y0, y1 = full_y0, full_y1
            else:
                if y0 < full_y0:
                    y1 += (full_y0 - y0)
                    y0 = full_y0
                if y1 > full_y1:
                    y0 -= (y1 - full_y1)
                    y1 = full_y1

        return x0, x1, y0, y1

    def on_graph_scroll(self, event):
        if event.inaxes != self.ax:
            return
        if self.current_channel is None and not self.multi_channels:
            return
        if hasattr(self.toolbar, "mode") and self.toolbar.mode:
            return

        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata
        if xdata is None:
            return

        button = getattr(event, "button", None)
        if button == "up":
            scale_factor = 1 / 1.2
        elif button == "down":
            scale_factor = 1.2
        else:
            step = getattr(event, "step", 0)
            if step > 0:
                scale_factor = 1 / 1.2
            elif step < 0:
                scale_factor = 1.2
            else:
                return

        x_left = xdata - cur_xlim[0]
        x_right = cur_xlim[1] - xdata
        new_x0 = xdata - x_left * scale_factor
        new_x1 = xdata + x_right * scale_factor

        if self.span_zoom_enabled.get():
            new_x0, new_x1, _, _ = self._clamp_view_to_full(new_x0, new_x1, cur_ylim[0], cur_ylim[1])
            self.ax.set_xlim(new_x0, new_x1)
            self.ax.set_ylim(cur_ylim)
        else:
            ydata = event.ydata
            if ydata is None:
                return
            y_bottom = ydata - cur_ylim[0]
            y_top = cur_ylim[1] - ydata
            new_y0 = ydata - y_bottom * scale_factor
            new_y1 = ydata + y_top * scale_factor
            new_x0, new_x1, new_y0, new_y1 = self._clamp_view_to_full(new_x0, new_x1, new_y0, new_y1)
            self.ax.set_xlim(new_x0, new_x1)
            self.ax.set_ylim(new_y0, new_y1)

        self._apply_x_locator(abs(new_x1 - new_x0))
        self.current_view_xlim = self.ax.get_xlim()
        self.current_view_ylim = self.ax.get_ylim()
        self.canvas.draw_idle()

    def move_graph_selection(self, step):
        if self.df is None or self.current_channel is None or self.time_column is None:
            return "break"
        if not self._graph_interaction_allowed():
            return "break"

        try:
            col_idx = self.columns.index(self.current_channel)
        except ValueError:
            return "break"

        x_all = self.get_numeric_column(self.time_column)
        y_all = self.get_plot_series(self.current_channel)
        valid_rows = np.flatnonzero(np.isfinite(x_all) & np.isfinite(y_all))
        if len(valid_rows) == 0:
            return "break"

        if self.selected_graph_row is None:
            row_idx = int(valid_rows[0] if step > 0 else valid_rows[-1])
        else:
            pos = np.searchsorted(valid_rows, self.selected_graph_row)
            if pos < len(valid_rows) and valid_rows[pos] == self.selected_graph_row:
                new_pos = pos + step
            else:
                new_pos = pos if step > 0 else pos - 1
            new_pos = max(0, min(len(valid_rows) - 1, new_pos))
            row_idx = int(valid_rows[new_pos])

        self.grid_table.set_selected_cell(self._data_row_to_display_row(row_idx), col_idx)
        self.selected_graph_row = row_idx
        self.selected_graph_col = self.current_channel
        self.update_status_bar(self._data_row_to_display_row(row_idx), col_idx)
        self.plot_channel(selected_row=row_idx, preserve_view=True)
        return "break"

    def on_graph_left_key(self, event=None):
        return self.move_graph_selection(-1)

    def on_graph_right_key(self, event=None):
        return self.move_graph_selection(1)

    def on_escape_key(self, event=None):
        mode = getattr(self.toolbar, "mode", "")
        if mode:
            if "PAN" in mode.upper():
                self.toolbar.pan()
            elif "ZOOM" in mode.upper():
                self.toolbar.zoom()

        if self.span_zoom_enabled.get():
            self.set_span_zoom_active(False)

        self._remove_zoom_span()

        # ESC는 그래프 기능 버튼만 해제하고,
        # 표 선택/셀 하이라이트/그래프 포인트는 유지한다.
        self.canvas.draw_idle()
        return "break"

    def reset_graph_view(self):
        if self.current_channel is None and not self.multi_channels:
            self.clear_graph()
            return
        self.current_view_xlim = None
        self.current_view_ylim = None
        self._remove_zoom_span()
        self.plot_channel(selected_row=self.selected_graph_row)

    def on_marker_display_mode_changed(self):
        if self.current_channel is not None or self.multi_channels:
            self.plot_channel(selected_row=self.selected_graph_row, preserve_view=True)

    def on_hover_toggle_changed(self):
        if not self.hover_enabled.get():
            self.hover_row = None
            changed = False
            if self.hover_annotation is not None:
                self.hover_annotation.set_visible(False)
                changed = True
            if self.hover_point_artist is not None:
                self.hover_point_artist.set_visible(False)
                changed = True
            if changed:
                self.canvas.draw_idle()

    def update_hover_annotation(self, event):
        if self.hover_annotation is None or self.hover_point_artist is None:
            return

        def hide_hover():
            changed = False
            if self.hover_annotation.get_visible():
                self.hover_annotation.set_visible(False)
                changed = True
            if self.hover_point_artist.get_visible():
                self.hover_point_artist.set_visible(False)
                changed = True
            if changed:
                self.canvas.draw_idle()

        if not self.hover_enabled.get() or event.inaxes != self.ax or event.xdata is None:
            hide_hover()
            return

        channels = self.get_channels_to_plot()
        if not channels:
            hide_hover()
            return

        hover_channel = self.current_channel
        if len(channels) > 1 and self.selected_graph_col in channels:
            hover_channel = self.selected_graph_col
        elif hover_channel not in channels:
            hover_channel = channels[0]

        if hover_channel is None:
            hide_hover()
            return

        row_idx = self._find_nearest_valid_row(event.xdata, hover_channel)
        if row_idx is None:
            hide_hover()
            return

        x_all = self.get_numeric_column(self.time_column)
        y_all = self.get_plot_series(hover_channel)
        x_val = x_all[row_idx]
        y_val = y_all[row_idx]
        if not (np.isfinite(x_val) and np.isfinite(y_val)):
            hide_hover()
            return

        unit = self.units.get(hover_channel, "").strip()
        unit_text = f" {unit}" if unit else ""
        color = self.channel_colors.get(hover_channel, "#666666")
        self.hover_annotation.xy = (x_val, y_val)
        self.hover_annotation.set_text(
            f"{self.get_channel_display_name(hover_channel)}\n"
            f"Time: {x_val:.6g} s\n"
            f"Value: {y_val:.6g}{unit_text}"
        )
        self.hover_annotation.set_bbox(dict(boxstyle="round,pad=0.35", fc="#fff8dc", ec=color, alpha=0.97))
        self.hover_annotation.set_visible(True)

        self.hover_point_artist.set_data([x_val], [y_val])
        self.hover_point_artist.set_color(color)
        self.hover_point_artist.set_visible(True)

        self.hover_row = row_idx
        self.canvas.draw_idle()

    def ensure_annotations(self):
        if self.hover_annotation is None or self.hover_annotation.axes is not self.ax:
            self.hover_annotation = self.ax.annotate(
                "",
                xy=(0, 0),
                xytext=(12, 12),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.35", fc="#fff8dc", ec="#7f7f7f", alpha=0.97),
                fontsize=9,
                visible=False,
                annotation_clip=False,
                zorder=10
            )
        if self.hover_point_artist is None or self.hover_point_artist.axes is not self.ax:
            self.hover_point_artist = self.ax.plot([], [], marker="o", markersize=4, linestyle="None", zorder=11, visible=False)[0]

    def build_plot_line_infos(self):
        channels = self.get_channels_to_plot()
        if not channels:
            return []
        x_all = self.get_numeric_column(self.time_column)
        line_infos = []
        filter_label = self.get_filter_label()
        show_overlay_raw = self.overlay_raw.get() and filter_label != "Raw"
        for ch in channels:
            y_all = self.get_plot_series(ch, filter_label)
            valid_mask = np.isfinite(x_all) & np.isfinite(y_all)
            if np.any(valid_mask):
                x_valid = x_all[valid_mask]
                y_valid = y_all[valid_mask]
                x_plot, y_plot = self._prepare_plot_data(x_valid, y_valid)
                line_infos.append((ch, x_plot, y_plot, filter_label, False))

            if show_overlay_raw:
                y_raw = self.get_numeric_column(ch)
                raw_mask = np.isfinite(x_all) & np.isfinite(y_raw)
                if np.any(raw_mask):
                    x_raw = x_all[raw_mask]
                    y_raw_valid = y_raw[raw_mask]
                    x_plot_raw, y_plot_raw = self._prepare_plot_data(x_raw, y_raw_valid)
                    line_infos.append((ch, x_plot_raw, y_plot_raw, "Raw", True))
        return line_infos

    def plot_channel(self, selected_row=None, preserve_view=False):
        if self.df is None or self.time_column is None:
            return

        line_infos = self.build_plot_line_infos()
        if not line_infos:
            if self.current_channel is not None:
                messagebox.showwarning("경고", f"{self.current_channel} 채널은 숫자 데이터가 없습니다.")
            else:
                self.clear_graph()
            return

        old_xlim = self.current_view_xlim if preserve_view else None
        old_ylim = self.current_view_ylim if preserve_view else None

        self.ax.clear()
        self._remove_zoom_span()
        self.hover_annotation = None
        self.hover_point_artist = None
        plotted_channels = []
        for ch, x_plot, y_plot, filter_label, is_overlay_raw in line_infos:
            base_label = self.get_title_channel_name(ch) if self.is_calculated_channel(ch) else self.get_channel_display_name(ch)
            color = self._get_channel_color(ch)
            if is_overlay_raw:
                label = f"{base_label} [Raw]"
                self.ax.plot(x_plot, y_plot, linewidth=1.0, label=label, color=color, alpha=0.35, linestyle="--")
            else:
                display_filter_label = self.get_filter_display_label(filter_label)
                label = f"{base_label} [{display_filter_label}]" if filter_label != "Raw" else base_label
                self.ax.plot(x_plot, y_plot, linewidth=1.0, label=label, color=color)
                plotted_channels.append(ch)

        if self.current_channel in plotted_channels:
            title_channel = self.current_channel
        else:
            title_channel = plotted_channels[0]
            self.current_channel = title_channel
            self._update_channel_label(title_channel)

        title_filter = self.get_filter_display_label(self.get_effective_filter_label(title_channel))
        if len(plotted_channels) == 1:
            self.ax.set_title(self.get_plot_title(title_channel))
        else:
            filter_suffix = "" if title_filter == "Raw" else f" [{title_filter}]"
            multi_label = f"Multiple channels ({len(plotted_channels)}){filter_suffix}"
            self.ax.set_title(multi_label)
        self.ax.set_xlabel(self.get_x_axis_label())
        if len(plotted_channels) == 1:
            self.ax.set_ylabel(self.get_y_axis_label(title_channel))
        else:
            self.ax.set_ylabel(f"Multiple channels ({len(plotted_channels)})")
        if len(line_infos) > 1:
            self.ax.legend(loc="upper right", fontsize=8)
        self.ax.grid(True)
        self._apply_x_locator()

        self.ax.relim()
        self.ax.autoscale_view()
        self.current_xlim_full = self.ax.get_xlim()
        self.current_ylim_full = self.ax.get_ylim()
        self.current_view_xlim = self.ax.get_xlim()
        self.current_view_ylim = self.ax.get_ylim()

        if selected_row is not None:
            self.selected_graph_row = selected_row

        marker_channel = self.current_channel
        if self.selected_graph_col in plotted_channels:
            marker_channel = self.selected_graph_col

        if self.selected_graph_row is not None and marker_channel is not None and 0 <= self.selected_graph_row < len(self.df):
            x_all = self.get_numeric_column(self.time_column)
            y_all = self.get_plot_series(marker_channel)
            x_sel = x_all[self.selected_graph_row]
            y_sel = y_all[self.selected_graph_row]

            if np.isfinite(x_sel) and np.isfinite(y_sel):
                display_mode = self.marker_display_mode.get()
                if display_mode == "point_line":
                    self.ax.axvline(x=x_sel, linewidth=1.0, color="red", alpha=0.75)
                self.ax.plot([x_sel], [y_sel], marker="o", markersize=7, color="red")
                self.ax.annotate(
                    f"({x_sel:.3f}, {y_sel:.3f})",
                    (x_sel, y_sel),
                    textcoords="offset points",
                    xytext=(8, 8),
                    fontsize=9,
                    color="red"
                )

        self.ensure_annotations()

        if preserve_view and old_xlim is not None and old_ylim is not None:
            self.ax.set_xlim(old_xlim)
            self.ax.set_ylim(old_ylim)

        self.current_view_xlim = self.ax.get_xlim()
        self.current_view_ylim = self.ax.get_ylim()
        self._apply_x_locator(abs(self.current_view_xlim[1] - self.current_view_xlim[0]))

        self.figure.tight_layout()
        if self.span_selector is not None:
            self._rebuild_span_selector()
        self.canvas.draw_idle()

    def clear_graph(self):
        self.current_view_xlim = None
        self.current_view_ylim = None
        self.channel_extrema_cache.clear()
        self.ax.clear()
        self.ax.set_title("채널을 선택하세요")
        self.ax.set_xlabel(self.get_x_axis_label())
        self.ax.set_ylabel("Value")
        self.ax.grid(True)
        self._apply_x_locator()
        self._remove_zoom_span()
        self.hover_annotation = None
        self.hover_point_artist = None
        self.figure.tight_layout()
        self.canvas.draw_idle()




if __name__ == "__main__":
    root = tk.Tk()
    app = FastCSVViewerWithGraph(root)
    root.mainloop()
