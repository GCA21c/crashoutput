import tkinter as tk
from tkinter import ttk

DUMMY_POSITION_OPTIONS = tuple(f"B{i}" for i in range(1, 7))


class MultiDummyPanel(tk.LabelFrame):
    def __init__(
        self,
        parent,
        *,
        dummy_count_var,
        active_dummy_var,
        profile_options_getter,
        on_count_changed=None,
        on_active_changed=None,
        on_positions_changed=None,
        show_count_row=True,
        show_rows=True,
        show_tabs=True,
        title="멀티 더미 설정",
    ):
        super().__init__(parent, text=title, bg="#ffffff")
        self.dummy_count_var = dummy_count_var
        self.active_dummy_var = active_dummy_var
        self.profile_options_getter = profile_options_getter
        self.on_count_changed = on_count_changed
        self.on_active_changed = on_active_changed
        self.on_positions_changed = on_positions_changed
        self.show_count_row = show_count_row
        self.show_rows = show_rows
        self.show_tabs = show_tabs

        self._name_vars = {slot: tk.StringVar() for slot in DUMMY_POSITION_OPTIONS}
        self._profile_vars = {slot: tk.StringVar() for slot in DUMMY_POSITION_OPTIONS}
        self._position_row_vars = [tk.StringVar() for _ in DUMMY_POSITION_OPTIONS]
        self._profile_combos = {}
        self._tab_frames = {}
        self._detected_positions = []
        self._selected_positions = ["B1"]
        self._explicit_row_positions = ["B1"] + ["" for _ in range(5)]
        self._updating_tabs = False
        self._rebuilding_rows = False
        self.group_info_var = tk.StringVar(value="검출 위치: 미검출")
        self._style_name = "CrashDummyTabs.TNotebook"
        self._tab_style_name = "CrashDummyTabs.TNotebook.Tab"

        self._build_ui()
        self.active_dummy_var.trace_add('write', lambda *_: self._sync_tab_from_active())

    def _build_ui(self):
        self._configure_tab_style()
        self.row1 = tk.Frame(self, bg="#ffffff")
        tk.Label(self.row1, text="더미 대수", bg="#ffffff", width=12, anchor="w").pack(side=tk.LEFT)
        self.dummy_count_combo = ttk.Combobox(
            self.row1,
            textvariable=self.dummy_count_var,
            state="readonly",
            width=8,
            values=tuple(str(i) for i in range(1, 7)),
        )
        self.dummy_count_combo.pack(side=tk.LEFT)
        self.dummy_count_combo.bind("<<ComboboxSelected>>", lambda _e: self._fire_count_changed())
        tk.Label(
            self.row1,
            textvariable=self.group_info_var,
            bg="#ffffff",
            fg="#555555",
            anchor="w",
            justify="left",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))
        if self.show_count_row:
            self.row1.pack(fill=tk.X, padx=10, pady=(10, 4))

        self.rows_host = tk.Frame(self, bg="#ffffff")
        if self.show_rows:
            self.rows_host.pack(fill=tk.X, padx=10, pady=(2, 6))

        self.tabs_box = tk.LabelFrame(self, text="더미 위치 탭", bg="#ffffff")
        self.notebook = ttk.Notebook(self.tabs_box, style=self._style_name)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        if self.show_tabs:
            self.tabs_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))


    def _configure_tab_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use(style.theme_use())
        except Exception:
            pass
        style.configure(
            self._style_name,
            background="#ffffff",
            borderwidth=0,
            tabmargins=(2, 2, 2, 0),
        )
        style.configure(
            self._tab_style_name,
            padding=(10, 2),
            font=("Arial", 9, "bold"),
            background="#dbeafe",
            foreground="#111111",
            lightcolor="#dbeafe",
            bordercolor="#7da8ff",
        )
        style.map(
            self._tab_style_name,
            background=[("selected", "#2563eb"), ("active", "#93c5fd"), ("!selected", "#dbeafe")],
            foreground=[("selected", "#111111"), ("active", "#111111"), ("!selected", "#111111")],
            lightcolor=[("selected", "#2563eb"), ("!selected", "#dbeafe")],
            bordercolor=[("selected", "#1d4ed8"), ("!selected", "#93c5fd")],
        )

    def _fire_count_changed(self):
        if callable(self.on_count_changed):
            self.on_count_changed()

    def _fire_active_changed(self):
        if callable(self.on_active_changed):
            self.on_active_changed()

    def _fire_positions_changed(self):
        if callable(self.on_positions_changed):
            self.on_positions_changed()

    def name_var(self, slot):
        return self._name_vars[slot]

    def profile_var(self, slot):
        return self._profile_vars[slot]

    def tab_frame(self, slot):
        return self._tab_frames.get(slot)

    def get_selected_positions(self):
        return list(self._selected_positions)

    def get_row_positions(self):
        count = self._row_count()
        return list(self._explicit_row_positions[:count])

    def refresh_profile_options(self):
        values = tuple(self.profile_options_getter() or ())
        for combo in self._profile_combos.values():
            combo['values'] = values

    def set_group_info(self, text):
        self.group_info_var.set(text)

    def set_detected_positions(self, positions):
        self._detected_positions = [p for p in positions if p in DUMMY_POSITION_OPTIONS]
        if self._detected_positions:
            self.group_info_var.set('검출 위치: ' + ', '.join(self._detected_positions))
        else:
            self.group_info_var.set('검출 위치: 미검출')
        self._rebuild_rows()

    def set_active_positions(self, positions, explicit_positions=None):
        count = self._row_count()
        explicit = list(explicit_positions[:count] if explicit_positions is not None else positions[:count])
        while len(explicit) < count:
            explicit.append("")

        internal = []
        used = set()
        for pos in positions:
            if pos in DUMMY_POSITION_OPTIONS and pos not in used:
                internal.append(pos)
                used.add(pos)
            if len(internal) >= count:
                break
        for pos in self._detected_positions:
            if len(internal) >= count:
                break
            if pos not in used:
                internal.append(pos)
                used.add(pos)
        for pos in DUMMY_POSITION_OPTIONS:
            if len(internal) >= count:
                break
            if pos not in used:
                internal.append(pos)
                used.add(pos)
        if not internal:
            internal = ["B1"]
        while len(internal) < count:
            internal.append(DUMMY_POSITION_OPTIONS[min(len(internal), len(DUMMY_POSITION_OPTIONS) - 1)])

        # 기본 자동 지정은 유지하되, 검출 수를 초과하는 행만 공란을 허용한다.
        detected_or_requested = [pos for pos in (list(positions) + list(self._detected_positions)) if pos in DUMMY_POSITION_OPTIONS]
        auto_fill_limit = min(count, len(dict.fromkeys(detected_or_requested)))
        normalized_explicit = []
        for idx in range(count):
            raw = (explicit[idx] or "").strip()
            if raw in DUMMY_POSITION_OPTIONS:
                normalized_explicit.append(raw)
            elif idx < auto_fill_limit:
                normalized_explicit.append(internal[idx])
            else:
                normalized_explicit.append("")

        self._selected_positions = internal[:count]
        self._explicit_row_positions = normalized_explicit[:count]
        for idx in range(count):
            self._position_row_vars[idx].set(self._explicit_row_positions[idx])

        self._rebuild_rows()
        self._rebuild_tabs(self._selected_positions)
        valid_tabs = [slot for slot in self._selected_positions if slot in DUMMY_POSITION_OPTIONS]
        current = self.active_dummy_var.get().strip()
        if valid_tabs and current not in valid_tabs:
            self.active_dummy_var.set(valid_tabs[0])
        self._sync_tab_from_active()

    def remove_row(self, row_index):
        count = self._row_count()
        if count <= 1:
            return
        explicit = self.get_row_positions()
        if 0 <= row_index < len(explicit):
            explicit.pop(row_index)
        self.dummy_count_var.set(str(count - 1))
        self.set_active_positions(self._selected_positions, explicit_positions=explicit)
        self._fire_count_changed()

    def is_empty_slot(self, slot):
        for idx, current in enumerate(self._selected_positions[:self._row_count()]):
            if current == slot:
                return not (self._explicit_row_positions[idx] or "").strip()
        return False

    def display_label_for_slot(self, slot):
        empty_index = 0
        for idx, current in enumerate(self._selected_positions[:self._row_count()]):
            if not (self._explicit_row_positions[idx] or "").strip():
                empty_index += 1
                if current == slot:
                    return f"empty{empty_index}"
        name = self._name_vars[slot].get().strip()
        return name if name else slot

    def _row_count(self):
        try:
            return min(max(int(self.dummy_count_var.get()), 1), 6)
        except Exception:
            return 1

    def _available_values_for_row(self, row_index):
        current = self._position_row_vars[row_index].get().strip()
        values = [""] + list(self._detected_positions)
        if current and current not in values and current in DUMMY_POSITION_OPTIONS:
            values.append(current)
        return tuple(values)

    def _sanitize_selected_positions(self):
        count = self._row_count()
        previous_internal = list(self._selected_positions)
        explicit = []
        internal = []
        used = set()

        for idx in range(count):
            raw = self._position_row_vars[idx].get().strip()
            explicit.append(raw if raw in DUMMY_POSITION_OPTIONS else "")
            chosen = raw if raw in DUMMY_POSITION_OPTIONS and raw not in used else None
            if chosen is None and idx < len(previous_internal):
                prev = previous_internal[idx]
                if prev in DUMMY_POSITION_OPTIONS and prev not in used:
                    chosen = prev
            if chosen is None:
                for pos in self._detected_positions:
                    if pos not in used:
                        chosen = pos
                        break
            if chosen is None:
                for pos in DUMMY_POSITION_OPTIONS:
                    if pos not in used:
                        chosen = pos
                        break
            chosen = chosen or "B1"
            internal.append(chosen)
            used.add(chosen)

        self._explicit_row_positions = explicit[:count]
        self._selected_positions = internal[:count]
        for idx in range(count):
            desired = self._explicit_row_positions[idx]
            if self._position_row_vars[idx].get().strip() != desired:
                self._position_row_vars[idx].set(desired)

    def _rebuild_rows(self):
        if not self.show_rows:
            return
        if self._rebuilding_rows:
            return
        self._rebuilding_rows = True
        try:
            self._sanitize_selected_positions()
            for child in self.rows_host.winfo_children():
                child.destroy()
            self._profile_combos = {}
            options = tuple(self.profile_options_getter() or ())
            count = self._row_count()
            for idx in range(count):
                slot = self._selected_positions[idx]
                row = tk.Frame(self.rows_host, bg="#f8fafc", bd=1, relief=tk.FLAT, highlightthickness=1, highlightbackground="#dbe3f1")
                row.pack(fill=tk.X, pady=3, ipady=3)

                pos_combo = ttk.Combobox(
                    row,
                    textvariable=self._position_row_vars[idx],
                    state="readonly",
                    width=8,
                    values=self._available_values_for_row(idx),
                )
                pos_combo.pack(side=tk.LEFT)
                pos_combo.bind("<<ComboboxSelected>>", lambda _e, r=idx: self._on_row_position_changed(r))

                name_entry = tk.Entry(
                    row,
                    textvariable=self._name_vars[slot],
                    width=14,
                    relief=tk.SOLID,
                    bd=1,
                    highlightthickness=1,
                    highlightbackground="#cfd4dc",
                    highlightcolor="#7aa2ff",
                    bg="#ffffff",
                )
                name_entry.pack(side=tk.LEFT, padx=(8, 8), ipady=2)

                combo = ttk.Combobox(
                    row,
                    textvariable=self._profile_vars[slot],
                    state="readonly",
                    values=options,
                )
                combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._profile_combos[slot] = combo

                remove_button = tk.Button(
                    row,
                    text="x",
                    width=3,
                    command=lambda r=idx: self.remove_row(r),
                    bg="#eff6ff",
                    fg="#1d4ed8",
                    activebackground="#dbeafe",
                    activeforeground="#1e3a8a",
                    relief=tk.GROOVE,
                )
                remove_button.pack(side=tk.LEFT, padx=(8, 0))
        finally:
            self._rebuilding_rows = False

    def _rebuild_tabs(self, positions):
        current_tabs = set(self._tab_frames.keys())
        desired = set(positions)
        for slot in list(current_tabs - desired):
            frame = self._tab_frames.pop(slot)
            try:
                self.notebook.forget(frame)
            except Exception:
                pass
        for slot in positions:
            if slot not in self._tab_frames:
                frame = tk.Frame(self.notebook, bg="#ffffff")
                self._tab_frames[slot] = frame
                self.notebook.add(frame, text=self.display_label_for_slot(slot))
        for idx, slot in enumerate(positions):
            frame = self._tab_frames[slot]
            self.notebook.tab(frame, text=self.display_label_for_slot(slot))
            try:
                self.notebook.insert(idx, frame)
            except Exception:
                pass

    def refresh_tab_labels(self, positions=None):
        positions = positions or list(self._tab_frames.keys())
        for slot in positions:
            frame = self._tab_frames.get(slot)
            if frame is not None:
                self.notebook.tab(frame, text=self.display_label_for_slot(slot))

    def _on_row_position_changed(self, row_index):
        chosen = self._position_row_vars[row_index].get().strip()
        if chosen and chosen in self._selected_positions:
            old_slot = self._selected_positions[row_index] if row_index < len(self._selected_positions) else ""
            other_idx = next((idx for idx, pos in enumerate(self._selected_positions) if idx != row_index and pos == chosen), None)
            if other_idx is not None:
                self._position_row_vars[other_idx].set(old_slot if old_slot in DUMMY_POSITION_OPTIONS else "")
        self._sanitize_selected_positions()
        self._rebuild_rows()
        self._rebuild_tabs(self._selected_positions)
        if self.active_dummy_var.get().strip() not in self._selected_positions:
            self.active_dummy_var.set(self._selected_positions[0])
        self._sync_tab_from_active()
        self._fire_positions_changed()

    def _on_tab_changed(self, _event=None):
        if self._updating_tabs:
            return
        current = self.notebook.select()
        for slot, frame in self._tab_frames.items():
            if str(frame) == str(current):
                if self.active_dummy_var.get() != slot:
                    self.active_dummy_var.set(slot)
                self._fire_active_changed()
                break

    def _sync_tab_from_active(self):
        slot = self.active_dummy_var.get().strip()
        frame = self._tab_frames.get(slot)
        if frame is None:
            return
        self._updating_tabs = True
        try:
            self.notebook.select(frame)
        finally:
            self._updating_tabs = False
