import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.io.dataset_store import DATASET_EXT, save_dataset_pickle
from app.core.isocode import build_channel_metadata_map, build_isocode_metadata
from app.services.state.persistence import build_dataset_snapshot_metadata

from app.ui.pages.viewer_page import ViewerPage
from app.ui.pages.offset_page import OffsetPage
from app.ui.pages.filtering_page import FilteringPage
from app.ui.pages.trimming_page import TrimmingPage
from app.ui.pages.injury_page import InjuryPage
from app.ui.pages.test_setup_page import TestSetupPage
from app.ui.pages.report_summary_page import ReportSummaryPage
from app.ui.pages.report_ploting_page import ReportPlotingPage
from app.ui.styles import (
    APP_BG,
    APP_TITLE_FONT,
    MUTED_FG,
    NAV_ACTIVE_BG,
    NAV_FONT,
    NAV_FONT_BOLD,
    OVERLAY_BG,
    PAGE_BG,
    SECTION_FG,
    SIDEBAR_BG,
    STATUS_BG,
    TEXT_FG,
    TITLE_FG,
)


INJURY_NAV_ORDER = ("hic", "nij", "chest", "pelvis", "femur", "knee", "iliac", "tibia")
INJURY_PAGE_LABELS = {
    "hic": "L HEAD",
    "nij": "L NECK",
    "chest": "L CHEST",
    "pelvis": "L PELVIS",
    "femur": "L FEMUR",
    "knee": "L KNEE",
    "iliac": "L ILIAC",
    "tibia": "L TIBIA",
}
INJURY_TEST_MODE_MODULES = {
    "-": tuple(),
    "FRONTAL": ("hic", "nij", "chest", "pelvis", "femur", "knee", "iliac", "tibia"),
    "SIDE": ("hic", "chest", "pelvis", "iliac"),
}

# Compatibility aliases for legacy page keys and forward spelling fixes.
# Keep these aliases until saved references/imports are explicitly migrated.
PAGE_KEY_ALIASES = {
    "dummyset": "test_setup",
    "report_plotting": "report_ploting",
}


class CrashAnalysisWorkbench(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=APP_BG)
        self.master = master
        self.page_buttons = {}
        self.pages = {}
        self.current_page_key = None
        self.is_resizing = False
        self._resize_after_id = None
        self._page_switch_busy_after_id = None
        self._top_status_busy_reasons = set()
        self._top_status_shimmer_job = None
        self._top_status_shimmer_offset = -160
        self._last_root_size = None
        self._resize_commit_delay_ms = 600
        self.original_df = None
        self.pre_filter_reference_df = None
        self.working_df = None
        self.source_file_label = "선택된 파일 없음"
        self.original_file_path = None
        self.original_source_path = None
        self.current_file_path = None
        self.last_saved_file_path = None
        self.history = []
        self.history_entries = []
        self.channel_filter_labels = {}
        self.dataset_metadata = {}
        self.original_metadata = {}
        self.pre_filter_reference_time_column = None
        self.dataset_info_var = tk.StringVar(value="파일: 선택된 파일 없음")
        self.history_info_var = tk.StringVar(value="History: 0")
        self.injury_test_mode_var = tk.StringVar(value="-")
        self.injury_page_keys = list(INJURY_NAV_ORDER)
        self._injury_mode_combo = None
        self._injury_nav_frame = None
        self.shared_dummy_config = self._default_shared_dummy_config()
        self._build_ui()
        self.show_page("viewer")
        self.master.bind("<Configure>", self._on_root_configure)

    def _default_shared_dummy_config(self):
        return {
            "injury_test_mode": "-",
            "setup_complete": False,
            "dummy_count": 1,
            "active_positions": ["B1"],
            "row_positions": ["B1"],
            "slot_meta": {slot: {"dummy_name": "", "dummy_profile": ""} for slot in ("B1", "B2", "B3", "B4", "B5", "B6")},
        }

    def _current_descriptions(self, base_metadata=None):
        metadata = dict(base_metadata or self.dataset_metadata or {})
        return dict(getattr(self.viewer, "external_descriptions", {}) or metadata.get("descriptions", {}) or {})

    def _current_units(self, base_metadata=None):
        metadata = dict(base_metadata or self.dataset_metadata or {})
        return dict(getattr(self.viewer, "external_units", {}) or metadata.get("units", {}) or {})

    def _enrich_isocode_metadata(self, dataframe=None, metadata=None):
        df = dataframe if dataframe is not None else self.working_df
        base = dict(metadata or self.dataset_metadata or {})
        if df is None:
            return base
        columns = list(getattr(df, "columns", []))
        iso_meta = build_isocode_metadata(
            columns,
            descriptions=self._current_descriptions(base),
            units=self._current_units(base),
            filter_labels=dict(self.channel_filter_labels or base.get("channel_filter_labels", {}) or {}),
            existing_raw_map=base.get("isocode_raw_map"),
            derived_channels=base.get("derived_channels"),
        )
        base.update(iso_meta)
        base["channel_metadata_map"] = build_channel_metadata_map(
            columns,
            descriptions=self._current_descriptions(base),
            units=self._current_units(base),
            filter_labels=dict(self.channel_filter_labels or base.get("channel_filter_labels", {}) or {}),
            existing_raw_map=base.get("isocode_raw_map"),
            derived_channels=base.get("derived_channels"),
        )
        return base

    @property
    def viewer(self):
        return self.pages["viewer"].viewer

    def _build_ui(self):
        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg=APP_BG, bd=0)
        main_pane.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(main_pane, width=300, bg=SIDEBAR_BG, bd=1, relief=tk.SOLID)
        self.sidebar.pack_propagate(False)
        main_pane.add(self.sidebar, minsize=260)

        right_area = tk.Frame(main_pane, bg=PAGE_BG)
        main_pane.add(right_area, stretch="always", minsize=720)

        top_status = tk.Frame(right_area, bg=STATUS_BG, bd=1, relief=tk.SOLID)
        top_status.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 0))
        self.top_status = top_status
        self.top_status_text = tk.Frame(top_status, bg=STATUS_BG)
        self.top_status_text.pack(side=tk.TOP, fill=tk.X)
        tk.Label(self.top_status_text, textvariable=self.dataset_info_var, bg=STATUS_BG, anchor="w", fg=TITLE_FG).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=6)
        tk.Label(self.top_status_text, textvariable=self.history_info_var, bg=STATUS_BG, anchor="e", fg=TEXT_FG).pack(side=tk.RIGHT, padx=10)
        self.top_status_shimmer = tk.Canvas(top_status, height=6, bg="#cfd6df", highlightthickness=0, bd=0)
        self.top_status_shimmer.pack(side=tk.TOP, fill=tk.X)
        self.top_status_shimmer.bind("<Configure>", lambda _event: self._render_top_status_shimmer())

        self.content = tk.Frame(right_area, bg=PAGE_BG)
        self.content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        history_frame = tk.LabelFrame(right_area, text="Processing History", bg=PAGE_BG)
        history_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=8)
        self.history_text = ScrolledText(history_frame, height=6, wrap=tk.WORD, state=tk.DISABLED)
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        title = tk.Label(self.sidebar, text="CRASH TOOLS", font=APP_TITLE_FONT, bg=SIDEBAR_BG, anchor="w", padx=14, pady=14)
        title.pack(fill=tk.X)

        self._add_nav_button("viewer", "DATA VIEWER")
        self._add_nav_section("PRE-PROCESSING")
        self._add_nav_button("test_setup", "TEST SETUP", indent=18)
        self._add_nav_button("offset", "DATA OFFSET", indent=18)
        self._add_nav_button("filtering", "DATA FILTERING", indent=18)
        self._add_nav_button("trimming", "DATA TRIMMING", indent=18)
        self._add_nav_section("POST-PROCESSING")
        self._build_injury_nav_group()
        self._build_report_nav_group()

        quick = tk.LabelFrame(self.sidebar, text="Quick Guide", bg=SIDEBAR_BG)
        quick.pack(fill=tk.X, padx=12, pady=(16, 8))
        tk.Label(quick, text="1) DAT 로드\n2) Offset\n3) Filtering\n4) Trimming\n5) Injury 계산", justify="left", bg=SIDEBAR_BG, fg=TEXT_FG).pack(anchor="w", padx=10, pady=10)

        self.page_host = tk.Frame(self.content, bg=PAGE_BG)
        self.page_host.pack(fill=tk.BOTH, expand=True)
        self.resize_overlay = tk.Frame(self.page_host, bg=OVERLAY_BG, bd=1, relief=tk.SOLID)
        overlay_panel = tk.Frame(self.resize_overlay, bg=OVERLAY_BG)
        overlay_panel.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            overlay_panel,
            text="Resizing window...",
            font=APP_TITLE_FONT,
            bg=OVERLAY_BG,
            fg=TITLE_FG,
        ).pack()
        tk.Label(
            overlay_panel,
            text="Rendering will resume when resizing stops.",
            font=NAV_FONT,
            bg=OVERLAY_BG,
            fg=MUTED_FG,
        ).pack(pady=(6, 0))

        self.pages["viewer"] = ViewerPage(self.page_host, self.master, self)
        self.pages["offset"] = OffsetPage(self.page_host, self)
        self.pages["filtering"] = FilteringPage(self.page_host, self)
        self.pages["trimming"] = TrimmingPage(self.page_host, self)
        self.pages["hic"] = InjuryPage(self.page_host, self, initial_mode="hic", show_internal_menu=False)
        self.pages["nij"] = InjuryPage(self.page_host, self, initial_mode="nij", show_internal_menu=False)
        self.pages["chest"] = InjuryPage(self.page_host, self, initial_mode="chest", show_internal_menu=False)
        self.pages["pelvis"] = InjuryPage(self.page_host, self, initial_mode="pelvis", show_internal_menu=False)
        self.pages["femur"] = InjuryPage(self.page_host, self, initial_mode="femur", show_internal_menu=False)
        self.pages["knee"] = InjuryPage(self.page_host, self, initial_mode="knee", show_internal_menu=False)
        self.pages["iliac"] = InjuryPage(self.page_host, self, initial_mode="iliac", show_internal_menu=False)
        self.pages["tibia"] = InjuryPage(self.page_host, self, initial_mode="tibia", show_internal_menu=False)
        self.pages["test_setup"] = TestSetupPage(self.page_host, self)
        # Keep the old key registered because older saved/UI references may still request it.
        self.pages["dummyset"] = self.pages["test_setup"]
        self.pages["report_summary"] = ReportSummaryPage(self.page_host, self)
        # Internal key/class spelling is kept for compatibility; user-facing text says PLOTTING.
        self.pages["report_ploting"] = ReportPlotingPage(self.page_host, self)
        self._apply_injury_mode_nav()

    def _render_top_status_shimmer(self):
        canvas = getattr(self, "top_status_shimmer", None)
        if canvas is None:
            return
        canvas.delete("shimmer")
        width = max(1, int(canvas.winfo_width()))
        height = max(1, int(canvas.winfo_height()))
        if not self._top_status_busy_reasons:
            canvas.create_rectangle(0, 0, width, height, fill="#cfd6df", outline="", tags="shimmer")
            return
        offset = float(self._top_status_shimmer_offset)
        canvas.create_rectangle(0, 0, width, height, fill="#d6dde6", outline="", tags="shimmer")
        canvas.create_rectangle(offset - 72, 0, offset + 72, height, fill="#f3f7fb", outline="", tags="shimmer")
        canvas.create_rectangle(offset - 24, 0, offset + 24, height, fill="#ffffff", outline="", tags="shimmer")

    def _animate_top_status_shimmer(self):
        self._top_status_shimmer_job = None
        canvas = getattr(self, "top_status_shimmer", None)
        if canvas is None or not self._top_status_busy_reasons:
            return
        width = max(1, int(canvas.winfo_width()))
        self._top_status_shimmer_offset += max(12, width // 20)
        if self._top_status_shimmer_offset > (width + 160):
            self._top_status_shimmer_offset = -160
        self._render_top_status_shimmer()
        self._top_status_shimmer_job = self.after(28, self._animate_top_status_shimmer)

    def start_busy_top_status(self, reason="busy"):
        self._top_status_busy_reasons.add(str(reason or "busy"))
        if self._top_status_shimmer_job is not None:
            return
        self._top_status_shimmer_offset = -160
        self._render_top_status_shimmer()
        self._top_status_shimmer_job = self.after(1, self._animate_top_status_shimmer)

    def stop_busy_top_status(self, reason="busy"):
        self._top_status_busy_reasons.discard(str(reason or "busy"))
        if self._top_status_busy_reasons:
            return
        if self._top_status_shimmer_job is not None:
            try:
                self.after_cancel(self._top_status_shimmer_job)
            except Exception:
                pass
            self._top_status_shimmer_job = None
        self._render_top_status_shimmer()

    def _add_nav_section(self, text):
        tk.Label(self.sidebar, text=text, font=NAV_FONT_BOLD, bg=SIDEBAR_BG, fg=SECTION_FG, anchor="w", padx=14, pady=8).pack(fill=tk.X, pady=(10, 2))

    def _add_nav_label(self, text, indent=0):
        tk.Label(self.sidebar, text=text, font=NAV_FONT_BOLD, bg=SIDEBAR_BG, fg=TEXT_FG, anchor="w", padx=14 + indent, pady=6).pack(fill=tk.X)

    def _add_nav_button(self, key, text, indent=0, parent=None):
        host = parent or self.sidebar
        button = tk.Button(
            host,
            text=text,
            anchor="w",
            relief=tk.FLAT,
            bd=0,
            padx=14 + indent,
            pady=10,
            bg=SIDEBAR_BG,
            activebackground=NAV_ACTIVE_BG,
            command=lambda k=key: self.show_page(k),
        )
        button.pack(fill=tk.X)
        self.page_buttons[key] = button

    def _build_injury_nav_group(self):
        group = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        group.pack(fill=tk.X)
        header = tk.Frame(group, bg=SIDEBAR_BG)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="INJURY",
            font=NAV_FONT_BOLD,
            bg=SIDEBAR_BG,
            fg=TEXT_FG,
            anchor="w",
            padx=32,
            pady=6,
        ).pack(side=tk.LEFT)

        self._injury_nav_frame = tk.Frame(group, bg=SIDEBAR_BG)
        self._injury_nav_frame.pack(fill=tk.X)
        for key in self.injury_page_keys:
            self._add_nav_button(key, INJURY_PAGE_LABELS[key], indent=34, parent=self._injury_nav_frame)

    def _build_report_nav_group(self):
        group = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        group.pack(fill=tk.X)
        header = tk.Frame(group, bg=SIDEBAR_BG)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="REPORT",
            font=NAV_FONT_BOLD,
            bg=SIDEBAR_BG,
            fg=TEXT_FG,
            anchor="w",
            padx=32,
            pady=6,
        ).pack(side=tk.LEFT)
        self._add_nav_button("report_summary", "L SUMMARY REPORT", indent=34, parent=group)
        self._add_nav_button("report_ploting", "L PLOTTING", indent=34, parent=group)

    def _available_injury_pages(self):
        if not bool((self.shared_dummy_config or {}).get("setup_complete")):
            return tuple()
        mode = self.injury_test_mode_var.get().strip() or "-"
        return tuple(INJURY_TEST_MODE_MODULES.get(mode, ()))

    def _apply_injury_mode_nav(self):
        visible_keys = set(self._available_injury_pages())
        for key in self.injury_page_keys:
            button = self.page_buttons.get(key)
            if button is None:
                continue
            if button.winfo_manager():
                button.pack_forget()
        for key in self.injury_page_keys:
            if key not in visible_keys:
                continue
            button = self.page_buttons.get(key)
            if button is not None:
                button.pack(fill=tk.X)

        if self.current_page_key in self.injury_page_keys and self.current_page_key not in visible_keys:
            fallback_key = next(iter(self._available_injury_pages()), None)
            self.show_page(fallback_key or "viewer")
            return
        self._refresh_nav_styles()

    def _on_injury_mode_changed(self, _event=None):
        self._apply_injury_mode_nav()

    def show_page(self, key):
        key = PAGE_KEY_ALIASES.get(key, key)
        if key not in self.pages:
            return
        if key in self.injury_page_keys and key not in self._available_injury_pages():
            allowed = self._available_injury_pages()
            if not allowed:
                return
            key = allowed[0]
        self.start_busy_top_status("page_switch")
        if self._page_switch_busy_after_id is not None:
            try:
                self.after_cancel(self._page_switch_busy_after_id)
            except Exception:
                pass
            self._page_switch_busy_after_id = None
        if self.is_resizing:
            self._finish_resize(commit_render=False)
        if self.current_page_key and self.current_page_key in self.pages and self.current_page_key != key:
            self.pages[self.current_page_key].place_forget()
        self._place_page(key)
        self.pages[key].tkraise()
        self.current_page_key = key
        self._refresh_nav_styles()
        if hasattr(self.pages[key], "on_show"):
            self.pages[key].on_show()
        self._page_switch_busy_after_id = self.after(260, lambda: self.stop_busy_top_status("page_switch"))

    def _place_page(self, key):
        page = self.pages.get(key)
        if page is None:
            return
        if str(page.winfo_manager()) != "place":
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _begin_resize_feedback(self):
        if self.is_resizing:
            return
        self.is_resizing = True
        if self.current_page_key in self.pages:
            self.pages[self.current_page_key].place_forget()
        self.resize_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.resize_overlay.lift()

    def _finish_resize(self, commit_render=True):
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
            self._resize_after_id = None
        self.is_resizing = False
        self.resize_overlay.place_forget()
        if self.current_page_key in self.pages:
            self._place_page(self.current_page_key)
            self.pages[self.current_page_key].tkraise()
            if commit_render:
                commit_fn = getattr(self.pages[self.current_page_key], "on_resize_commit", None)
                if callable(commit_fn):
                    try:
                        commit_fn()
                    except Exception:
                        pass

    def _on_root_configure(self, event):
        if event.widget is not self.master:
            return
        size = (event.width, event.height)
        if size == self._last_root_size:
            return
        self._last_root_size = size
        self._begin_resize_feedback()
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.after(self._resize_commit_delay_ms, self._finish_resize)

    def _refresh_nav_styles(self):
        for key, button in self.page_buttons.items():
            if key == self.current_page_key:
                button.configure(bg=NAV_ACTIVE_BG, activebackground=NAV_ACTIVE_BG, font=NAV_FONT_BOLD)
            else:
                button.configure(bg=SIDEBAR_BG, activebackground=NAV_ACTIVE_BG, font=NAV_FONT)



    def get_detected_dummy_positions(self):
        metadata = self._enrich_isocode_metadata(self.working_df, self.dataset_metadata)
        parsed_map = dict(metadata.get("isocode_parsed_map", {}) or {})
        detected = []
        for channel, parsed in parsed_map.items():
            slot = str((parsed or {}).get("dummy_position_normalized") or "").strip().upper()
            if slot and slot.startswith("B") and slot not in detected:
                detected.append(slot)
        return [slot for slot in ("B1","B2","B3","B4","B5","B6") if slot in detected]

    def get_shared_dummy_config(self):
        config = dict(self.shared_dummy_config or {})
        config["slot_meta"] = {slot: dict(meta or {}) for slot, meta in (config.get("slot_meta") or {}).items()}
        return config

    def set_shared_dummy_config(self, config):
        merged = self.get_shared_dummy_config()
        merged.update({k: v for k, v in dict(config or {}).items() if k != "slot_meta"})
        slot_meta = dict(merged.get("slot_meta") or {})
        for slot, meta in dict((config or {}).get("slot_meta") or {}).items():
            slot_meta[slot] = {"dummy_name": str((meta or {}).get("dummy_name") or "").strip(), "dummy_profile": str((meta or {}).get("dummy_profile") or "").strip()}
        merged["slot_meta"] = slot_meta
        mode = str(merged.get("injury_test_mode") or self.injury_test_mode_var.get() or "-").strip().upper()
        if mode not in INJURY_TEST_MODE_MODULES:
            mode = "-"
        merged["injury_test_mode"] = mode
        self.injury_test_mode_var.set(mode)
        self.shared_dummy_config = merged
        self.dataset_metadata = dict(self.dataset_metadata or {})
        self.dataset_metadata["shared_dummy_config"] = self.get_shared_dummy_config()
        self._apply_injury_mode_nav()
        for key in self.injury_page_keys:
            page = self.pages.get(key)
            if hasattr(page, "apply_shared_dummy_config"):
                page.apply_shared_dummy_config(merged)
        if self.current_file_path and str(self.current_file_path).lower().endswith(DATASET_EXT):
            self._persist_history_to_current_pickle()

    def _update_dataset_info(self):
        label = self.source_file_label or "선택된 파일 없음"
        self.dataset_info_var.set(f"파일: {label}")
        self.history_info_var.set(f"History: {len(self.history_entries or self.history)}")

    def _normalize_history_entry(self, item):
        if isinstance(item, dict):
            entry = dict(item)
            entry.setdefault('timestamp', datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'))
            entry.setdefault('type', 'general')
            entry['message'] = str(entry.get('message') or '').strip() or 'Event recorded'
            return entry
        text = str(item or '').strip()
        if not text:
            return None
        return {
            'timestamp': datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'general',
            'message': text,
        }

    def _format_history_entry(self, entry):
        if not isinstance(entry, dict):
            return str(entry or '').strip()
        parts = []
        timestamp = str(entry.get('timestamp') or '').strip()
        if timestamp:
            parts.append(f'[{timestamp}]')
        section = str(entry.get('section') or '').strip().upper()
        if section:
            parts.append(f'[{section}]')
        slot = str(entry.get('slot') or entry.get('dummy_position') or '').strip()
        if slot:
            parts.append(f'[{slot}]')
        message = str(entry.get('display_message') or entry.get('message') or '').strip()
        event_type = str(entry.get('type') or '').strip().lower()
        if not message:
            type_map = {
                'injury_calculation': 'Calculation completed successfully.',
                'auto_assign': 'Channel assignment completed successfully.',
                'graph_saved': 'Graph saved successfully.',
                'graph_selection': 'Graph updated successfully.',
                'save': 'Saved successfully.',
                'load': 'Loaded successfully.',
            }
            message = type_map.get(event_type, 'Event completed successfully.')
        parts.append(message)
        return ' '.join(part for part in parts if part)

    def _refresh_history_view(self):
        widget = getattr(self, 'history_text', None)
        if widget is None:
            return
        widget.configure(state=tk.NORMAL)
        widget.delete('1.0', tk.END)
        source = self.history_entries or [self._normalize_history_entry(item) for item in self.history]
        for idx, item in enumerate(source, start=1):
            display = self._format_history_entry(item)
            if display:
                widget.insert(tk.END, f"{idx}. {display}\n")
        widget.configure(state=tk.DISABLED)
        widget.see(tk.END)

    def _persist_history_to_current_pickle(self):
        current_file = self.current_file_path
        if not current_file or not str(current_file).lower().endswith(DATASET_EXT):
            return
        dataframe = self.working_df
        if dataframe is None:
            return
        metadata = build_dataset_snapshot_metadata(
            self.dataset_metadata,
            source_file_path=self.original_source_path or self.source_file_label,
            history=self.history,
            history_entries=self.history_entries,
            shared_dummy_config=self.get_shared_dummy_config(),
            time_column=self.viewer.time_column,
            units=self._current_units(self.dataset_metadata),
            descriptions=self._current_descriptions(self.dataset_metadata),
            channel_filter_labels=self.channel_filter_labels or (self.dataset_metadata or {}).get("channel_filter_labels", {}) or {},
            pre_filter_reference_df=self.pre_filter_reference_df,
            pre_filter_reference_time_column=self.pre_filter_reference_time_column,
        )
        metadata = self._enrich_isocode_metadata(dataframe, metadata)
        save_dataset_pickle(
            current_file,
            dataframe,
            metadata=metadata,
            history=self.history,
            source_file_path=self.original_source_path or self.source_file_label,
            source_label=self.source_file_label,
        )
        self.dataset_metadata = metadata


    def reset_session_state(self):
        self.history = []
        self.history_entries = []
        self.channel_filter_labels = {}
        self.dataset_metadata = {}
        self.original_metadata = {}
        self.original_df = None
        self.pre_filter_reference_df = None
        self.pre_filter_reference_time_column = None
        self.working_df = None
        self.source_file_label = "선택된 파일 없음"
        self.original_file_path = None
        self.original_source_path = None
        self.current_file_path = None
        self.last_saved_file_path = None
        self.shared_dummy_config = self._default_shared_dummy_config()
        self.injury_test_mode_var.set("-")

        for key, page in self.pages.items():
            target = page
            if key == 'viewer' and hasattr(page, 'viewer'):
                target = page.viewer
            reset_fn = getattr(target, 'reset_session_state', None)
            if callable(reset_fn):
                try:
                    reset_fn()
                except Exception:
                    pass

        self._refresh_history_view()
        self._update_dataset_info()

    def add_history_entry(self, text=None, persist=False, **entry_kwargs):
        entry = None
        if isinstance(text, dict):
            entry = dict(text)
            entry.update(entry_kwargs)
        elif entry_kwargs:
            entry = dict(entry_kwargs)
            if text is not None:
                entry.setdefault('message', str(text))
        else:
            entry = {'message': text}
        normalized = self._normalize_history_entry(entry)
        if not normalized:
            return
        display = self._format_history_entry(normalized)
        self.history_entries.append(normalized)
        self.history.append(display)
        self._refresh_history_view()
        self._update_dataset_info()
        if persist:
            self._persist_history_to_current_pickle()

    def set_loaded_dataset(self, dataframe, file_label_text, is_new_file=False, metadata=None):
        if is_new_file:
            self.reset_session_state()
        self.original_df = dataframe.copy(deep=True)
        self.working_df = dataframe.copy(deep=True)
        self.source_file_label = file_label_text
        self.dataset_metadata = dict(metadata or {})
        self.channel_filter_labels = dict(self.dataset_metadata.get('channel_filter_labels') or {})
        self.dataset_metadata = self._enrich_isocode_metadata(self.working_df, self.dataset_metadata)
        self.original_metadata = dict(self.dataset_metadata)
        stored_reference_df = self.dataset_metadata.get("pre_filter_reference_df")
        if stored_reference_df is not None:
            try:
                self.pre_filter_reference_df = stored_reference_df.copy(deep=True)
            except Exception:
                self.pre_filter_reference_df = dataframe.copy(deep=True)
        else:
            self.pre_filter_reference_df = dataframe.copy(deep=True)
        self.pre_filter_reference_time_column = (
            self.dataset_metadata.get("pre_filter_reference_time_column")
            or self.dataset_metadata.get("time_column")
        )
        self.set_shared_dummy_config(self.dataset_metadata.get("shared_dummy_config") or self._default_shared_dummy_config())

        source_format = str(self.dataset_metadata.get("source_format", "")).upper()
        if isinstance(file_label_text, str) and file_label_text.lower().endswith(".dat"):
            self.original_source_path = file_label_text
            self.original_file_path = file_label_text
            self.current_file_path = file_label_text
        else:
            self.original_source_path = self.dataset_metadata.get("source_file_path") or file_label_text
            self.original_file_path = file_label_text if isinstance(file_label_text, str) and file_label_text.lower().endswith(DATASET_EXT) else None
            self.current_file_path = file_label_text

        self.last_saved_file_path = None
        self.history_entries = [e for e in (self.dataset_metadata.get("saved_history_entries") or []) if isinstance(e, dict)]
        if self.history_entries:
            self.history = [self._format_history_entry(e) for e in self.history_entries]
        else:
            self.history = list(self.dataset_metadata.get("saved_history") or [])
            self.history_entries = [e for e in (self._normalize_history_entry(item) for item in self.history) if e]
            self.history = [self._format_history_entry(e) for e in self.history_entries]
        if is_new_file and not self.history_entries:
            loaded_text = "Loaded new DAT dataset" if source_format == "DAT" else "Loaded saved dataset"
            self.add_history_entry(loaded_text)
        self._refresh_history_view()
        self._update_dataset_info()

    def _build_save_path(self, suffix, prefer_original_source=False):
        naming_source = None
        if prefer_original_source:
            naming_source = (
                self.original_source_path
                or self.dataset_metadata.get("source_file_path")
                or self.source_file_label
                or self.current_file_path
            )
        else:
            naming_source = self.current_file_path or self.original_source_path
        if not naming_source:
            return None
        naming_path = Path(naming_source)
        stem = naming_path.stem

        parent_candidates = []
        if prefer_original_source:
            parent_candidates.extend([
                naming_path.parent,
                Path(self.current_file_path).parent if self.current_file_path else None,
                Path(self.source_file_label).parent if self.source_file_label else None,
            ])
        else:
            parent_candidates.extend([
                naming_path.parent,
                Path(self.original_source_path).parent if self.original_source_path else None,
            ])

        parent = None
        for candidate in parent_candidates:
            if candidate is None:
                continue
            try:
                if candidate.exists() and candidate.is_dir():
                    parent = candidate
                    break
            except Exception:
                continue
        if parent is None:
            parent = Path.cwd()

        if suffix:
            while stem.endswith(suffix):
                stem = stem[:-len(suffix)]
            stem = f"{stem}{suffix}"
        return str(parent / f"{stem}{DATASET_EXT}")

    def _build_next_save_path(self, suffix):
        return self._build_save_path(suffix, prefer_original_source=False)

    def _build_original_source_save_path(self, suffix):
        return self._build_save_path(suffix, prefer_original_source=True)

    def save_dataframe_to_next_stage(self, dataframe, suffix):
        save_path = self._build_next_save_path(suffix)
        if not save_path:
            return None
        metadata = build_dataset_snapshot_metadata(
            self.dataset_metadata,
            source_file_path=self.original_source_path or self.source_file_label,
            history=self.history,
            history_entries=self.history_entries,
            shared_dummy_config=self.get_shared_dummy_config(),
            time_column=self.viewer.time_column,
            units=self._current_units(self.dataset_metadata),
            descriptions=self._current_descriptions(self.dataset_metadata),
            channel_filter_labels=self.channel_filter_labels or (self.dataset_metadata or {}).get("channel_filter_labels", {}) or {},
            pre_filter_reference_df=self.pre_filter_reference_df,
            pre_filter_reference_time_column=self.pre_filter_reference_time_column,
        )
        metadata = self._enrich_isocode_metadata(dataframe, metadata)
        return save_dataset_pickle(
            save_path,
            dataframe,
            metadata=metadata,
            history=self.history,
            source_file_path=self.original_source_path or self.source_file_label,
            source_label=self.source_file_label,
        )

    def save_current_dataset_snapshot(self, suffix, metadata_override=None, prefer_original_source=False):
        dataframe = self.working_df
        if dataframe is None:
            return None
        save_path = self._build_save_path(suffix, prefer_original_source=prefer_original_source)
        if not save_path:
            return None
        metadata_source = dict(self.dataset_metadata or {})
        if metadata_override:
            metadata_source.update(dict(metadata_override))
        metadata = build_dataset_snapshot_metadata(
            metadata_source,
            source_file_path=self.original_source_path or self.source_file_label,
            history=self.history,
            history_entries=self.history_entries,
            shared_dummy_config=self.get_shared_dummy_config(),
            time_column=self.viewer.time_column,
            units=self._current_units(metadata_source),
            descriptions=self._current_descriptions(metadata_source),
            channel_filter_labels=self.channel_filter_labels or metadata_source.get("channel_filter_labels", {}) or {},
            pre_filter_reference_df=self.pre_filter_reference_df,
            pre_filter_reference_time_column=self.pre_filter_reference_time_column,
        )
        metadata = self._enrich_isocode_metadata(dataframe, metadata)
        saved_path = save_dataset_pickle(
            save_path,
            dataframe,
            metadata=metadata,
            history=self.history,
            source_file_path=self.original_source_path or self.source_file_label,
            source_label=self.source_file_label,
        )
        self.dataset_metadata = metadata
        self.current_file_path = saved_path
        self.last_saved_file_path = saved_path
        self.source_file_label = saved_path
        self._update_dataset_info()
        return saved_path

    def apply_processed_dataframe(self, dataframe, history_text, op_suffix=None, reset_plot=False, metadata_override=None, update_pre_filter_reference=False):
        self.working_df = dataframe.copy(deep=True)
        if metadata_override:
            merged_metadata = dict(self.dataset_metadata)
            merged_metadata.update(dict(metadata_override))
            self.dataset_metadata = merged_metadata
        if update_pre_filter_reference:
            self.pre_filter_reference_df = self.working_df.copy(deep=True)
            self.pre_filter_reference_time_column = self.viewer.time_column or self.dataset_metadata.get("time_column")
        self.dataset_metadata["pre_filter_reference_df"] = (
            self.pre_filter_reference_df.copy(deep=True)
            if self.pre_filter_reference_df is not None else None
        )
        self.dataset_metadata["pre_filter_reference_time_column"] = (
            self.pre_filter_reference_time_column
            or self.viewer.time_column
            or self.dataset_metadata.get("time_column")
        )
        self.dataset_metadata = self._enrich_isocode_metadata(self.working_df, self.dataset_metadata)
        self.channel_filter_labels = dict(self.dataset_metadata.get("channel_filter_labels") or self.channel_filter_labels or {})
        file_label_text = self.source_file_label
        saved_path = None
        if history_text:
            if isinstance(history_text, dict):
                self.add_history_entry(history_text)
            else:
                self.add_history_entry(history_text)
        if op_suffix:
            saved_path = self.save_dataframe_to_next_stage(self.working_df, op_suffix)
            if saved_path:
                self.current_file_path = saved_path
                self.last_saved_file_path = saved_path
                file_label_text = saved_path
                self.source_file_label = saved_path
                self.dataset_metadata["source_format"] = "PICKLE"
                self.dataset_metadata["source_file_path"] = self.original_source_path or self.source_file_label
        self.viewer.load_dataframe(self.working_df, file_label_text=file_label_text, reset_plot=reset_plot, metadata=self.dataset_metadata)
        self._update_dataset_info()
        return saved_path

    def restore_original_dataset(self):
        if self.original_df is None:
            messagebox.showinfo("안내", "복원할 원본 데이터가 없습니다.")
            return
        self.working_df = self.original_df.copy(deep=True)
        self.current_file_path = self.original_file_path
        self.source_file_label = self.original_source_path or self.source_file_label
        self.dataset_metadata = dict(self.original_metadata)
        self.channel_filter_labels = dict(self.dataset_metadata.get('channel_filter_labels') or {})
        self.pre_filter_reference_df = self.original_df.copy(deep=True)
        self.pre_filter_reference_time_column = self.dataset_metadata.get("time_column")
        self.dataset_metadata["pre_filter_reference_df"] = self.pre_filter_reference_df.copy(deep=True)
        self.dataset_metadata["pre_filter_reference_time_column"] = self.pre_filter_reference_time_column
        self.dataset_metadata = self._enrich_isocode_metadata(self.working_df, self.dataset_metadata)
        self.add_history_entry("Restored original dataset")
        self.viewer.load_dataframe(self.working_df, file_label_text=self.source_file_label, reset_plot=True, metadata=self.dataset_metadata)
        self._update_dataset_info()
        messagebox.showinfo("완료", "원본 데이터로 복원했습니다.")
