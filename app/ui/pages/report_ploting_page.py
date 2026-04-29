import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.report.exporters.ppt import PptExportError, export_plotting_report_to_ppt
from app.report.exporters.runtime import execution_folder, open_export_file
from app.report.plotting_service import (
    available_plot_options,
    build_plotting_payload,
    collect_plot_items,
    merge_plot_items,
    plotting_default_template_path,
    plotting_item_display_name,
    plotting_item_text,
    plotting_output_name_from_fields,
    plotting_payload_from_metadata,
    plotting_report_fields,
    plotting_save_suffix,
    update_plotting_cache,
)
from app.ui.styles import HEADER_FONT, MUTED_FG, PAGE_BG, TEXT_FG


PAGE_TITLE = "REPORT - PLOTTING"


class _PptExportOverlay:
    def __init__(self, root):
        self.root = root
        self.frame = tk.Frame(root, bg="#20242a", bd=0)

        self.message_var = tk.StringVar(value="PPT export 준비 중...")
        self.detail_var = tk.StringVar(value="프로그램이 멈춘 것이 아니니 잠시 기다려 주세요.")
        self.progress_var = tk.DoubleVar(value=0.0)

        panel = tk.Frame(self.frame, bg="#ffffff", bd=1, relief=tk.SOLID)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=560, height=170)
        tk.Label(
            panel,
            text="PPT EXPORT",
            bg="#ffffff",
            fg="#111827",
            font=("맑은 고딕", 16, "bold"),
        ).pack(anchor="w", padx=24, pady=(22, 6))
        tk.Label(
            panel,
            textvariable=self.message_var,
            bg="#ffffff",
            fg="#111827",
            font=("맑은 고딕", 11),
            anchor="w",
        ).pack(fill=tk.X, padx=24)
        tk.Label(
            panel,
            textvariable=self.detail_var,
            bg="#ffffff",
            fg="#6b7280",
            font=("맑은 고딕", 9),
            anchor="w",
        ).pack(fill=tk.X, padx=24, pady=(3, 12))
        self.progress = ttk.Progressbar(panel, variable=self.progress_var, maximum=100.0, mode="determinate")
        self.progress.pack(fill=tk.X, padx=24)

    def show(self):
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.frame.lift()
        try:
            self.frame.grab_set()
        except Exception:
            pass
        self.root.update_idletasks()
        self.root.update()

    def update(self, current, total, message):
        total = max(1, int(total or 1))
        current = max(0, min(int(current or 0), total))
        percent = (current / total) * 100.0
        self.progress_var.set(percent)
        self.message_var.set(str(message or "PPT export 진행 중..."))
        self.detail_var.set(f"{current} / {total} 단계 처리 중")
        self.frame.lift()
        self.root.update_idletasks()
        self.root.update()

    def close(self):
        try:
            self.frame.grab_release()
        except Exception:
            pass
        try:
            self.frame.destroy()
        except Exception:
            pass


class ReportPlotingPage(tk.Frame):
    """Legacy class name kept for the existing report_ploting page key."""

    def __init__(self, parent, workbench):
        super().__init__(parent, bg=PAGE_BG)
        self.workbench = workbench
        self.status_var = tk.StringVar(value="Ready")
        self.loaded_count_var = tk.StringVar(value="Loaded plots: 0")
        self.template_path_var = tk.StringVar(value=plotting_default_template_path())
        self.report_inputs_var = tk.StringVar(value="-")
        self.add_plot_var = tk.StringVar()
        self.text_mode_var = tk.StringVar(value="auto")
        self._loaded_dataset_identity = None
        self._all_items = []
        self._items = []
        self._add_options = {}
        self._selected_item_key = None
        self._building_ui = False
        self._build_ui()

    def _build_ui(self):
        outer = tk.Frame(self, bg=PAGE_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(outer, bg=PAGE_BG)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text=PAGE_TITLE, font=HEADER_FONT, bg=PAGE_BG).pack(side=tk.LEFT)

        top = tk.Frame(outer, bg=PAGE_BG)
        top.pack(fill=tk.X, pady=(0, 12))
        tk.Button(top, text="Load Plot", command=self.load_plot_list, width=12).pack(side=tk.LEFT)
        tk.Button(top, text="Save", command=self.save_plotting, width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="PPT EXPORT", command=self.export_ppt, width=14).pack(side=tk.LEFT, padx=(8, 0))

        info_row = tk.Frame(outer, bg=PAGE_BG)
        info_row.pack(fill=tk.X, pady=(0, 10))

        inputs_box = tk.LabelFrame(info_row, text="Report Inputs", bg=PAGE_BG)
        inputs_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        tk.Label(
            inputs_box,
            textvariable=self.report_inputs_var,
            bg=PAGE_BG,
            fg=TEXT_FG,
            justify="left",
            anchor="w",
            wraplength=430,
        ).pack(fill=tk.X, padx=10, pady=8)

        loaded_box = tk.LabelFrame(info_row, text="Status", bg=PAGE_BG)
        loaded_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        tk.Label(loaded_box, textvariable=self.loaded_count_var, bg=PAGE_BG, justify="left", anchor="w").pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(loaded_box, textvariable=self.status_var, bg=PAGE_BG, fg=TEXT_FG, justify="left", anchor="w", wraplength=380).pack(fill=tk.X, padx=10, pady=(0, 8))

        template_box = tk.LabelFrame(outer, text="Template", bg=PAGE_BG)
        template_box.pack(fill=tk.X, pady=(0, 10))
        template_row = tk.Frame(template_box, bg=PAGE_BG)
        template_row.pack(fill=tk.X, padx=10, pady=8)
        tk.Entry(template_row, textvariable=self.template_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(template_row, text="Browse", command=self._browse_template).pack(side=tk.LEFT, padx=(8, 0))

        body = tk.Frame(outer, bg=PAGE_BG)
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.LabelFrame(body, text="Plot List", bg=PAGE_BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        guide = tk.Label(
            left,
            text="Load Plot 으로 현재 상해모듈 그래프를 수집한다. 초록 램프는 load 가능, 빨간 램프는 누락/미생성 상태다.",
            bg=PAGE_BG,
            fg=MUTED_FG,
            justify="left",
            anchor="w",
            wraplength=860,
        )
        guide.pack(fill=tk.X, padx=8, pady=(8, 0))

        self.tree = ttk.Treeview(
            left,
            columns=("lamp", "include", "slot", "module", "graph", "dummy", "text"),
            show="headings",
            height=18,
            selectmode="browse",
        )
        for column, heading, width in (
            ("lamp", "", 38),
            ("include", "Use", 52),
            ("slot", "Slot", 58),
            ("module", "Module", 78),
            ("graph", "Graph", 220),
            ("dummy", "Dummy", 160),
            ("text", "Text", 90),
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor="w")
        self.tree.tag_configure("loaded", foreground="#15803d")
        self.tree.tag_configure("missing", foreground="#b91c1c")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        tree_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

        right = tk.LabelFrame(body, text="Edit", bg=PAGE_BG)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0))

        edit_btns = tk.Frame(right, bg=PAGE_BG)
        edit_btns.pack(fill=tk.X, padx=10, pady=(10, 8))
        tk.Button(edit_btns, text="Remove", command=self._remove_selected).pack(fill=tk.X)
        tk.Button(edit_btns, text="Toggle Include", command=self._toggle_selected_include).pack(fill=tk.X, pady=(6, 0))
        tk.Button(edit_btns, text="Move Up", command=lambda: self._move_selected(-1)).pack(fill=tk.X, pady=(6, 0))
        tk.Button(edit_btns, text="Move Down", command=lambda: self._move_selected(1)).pack(fill=tk.X, pady=(6, 0))

        add_box = tk.LabelFrame(right, text="Add Plot", bg=PAGE_BG)
        add_box.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.add_plot_combo = ttk.Combobox(add_box, textvariable=self.add_plot_var, state="readonly")
        self.add_plot_combo.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Button(add_box, text="Add", command=self._add_selected_option).pack(fill=tk.X, padx=8, pady=(0, 8))

        text_box = tk.LabelFrame(right, text="Graph Text", bg=PAGE_BG)
        text_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        mode_row = tk.Frame(text_box, bg=PAGE_BG)
        mode_row.pack(fill=tk.X, padx=8, pady=(8, 6))
        tk.Label(mode_row, text="Mode", bg=PAGE_BG).pack(side=tk.LEFT)
        self.text_mode_combo = ttk.Combobox(mode_row, textvariable=self.text_mode_var, values=("auto", "custom"), state="readonly", width=10)
        self.text_mode_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.text_mode_combo.bind("<<ComboboxSelected>>", self._apply_text_editor)

        self.text_editor = tk.Text(text_box, height=12, wrap=tk.WORD)
        self.text_editor.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        tk.Button(text_box, text="Apply Text", command=self._apply_text_editor).pack(fill=tk.X, padx=8, pady=(0, 8))

    def _dataset_identity(self):
        current = getattr(self.workbench, "current_file_path", None) or ""
        source = dict(getattr(self.workbench, "dataset_metadata", {}) or {}).get("source_file_path") or ""
        return f"{current}|{source}"

    def _refresh_report_inputs(self):
        self.report_inputs_var.set(
            "\n".join(
                f"{label}: {str(plotting_report_fields(self.workbench).get(key) or '').strip() or '-'}"
                for key, label in (
                    ("manufacturer", "Manufacturer"),
                    ("vehicle", "Vehicle"),
                    ("speed", "Speed"),
                    ("test_date", "Test Date"),
                    ("test_id", "Test ID"),
                )
            )
        )

    def _load_saved_state(self):
        identity = self._dataset_identity()
        if identity == self._loaded_dataset_identity:
            return False
        self._loaded_dataset_identity = identity
        payload = plotting_payload_from_metadata(getattr(self.workbench, "dataset_metadata", {}) or {})
        self.template_path_var.set(str(payload.get("template_path") or plotting_default_template_path()))
        self._items = [dict(item) for item in list(payload.get("items") or [])]
        self._refresh_report_inputs()
        self._refresh_loaded_count()
        self._populate_tree()
        self._refresh_add_options()
        if self._items:
            self.status_var.set("Saved plotting state loaded.")
        else:
            self.status_var.set("Ready")
        return True

    def _cache_state_in_memory(self):
        payload = build_plotting_payload(self._items, plotting_report_fields(self.workbench), template_path=self.template_path_var.get().strip())
        self.workbench.dataset_metadata = update_plotting_cache(
            getattr(self.workbench, "dataset_metadata", {}) or {},
            payload,
        )

    def _refresh_loaded_count(self):
        total = len(self._items)
        loaded = sum(1 for item in self._items if bool(item.get("loaded")))
        self.loaded_count_var.set(f"Loaded plots: {loaded} / {total}")

    def _tree_row_values(self, item):
        item = dict(item or {})
        return (
            "●" if bool(item.get("loaded")) else "●",
            "Y" if bool(item.get("included", True)) else "N",
            item.get("slot") or "-",
            str(item.get("section_key") or item.get("page_key") or "-").upper(),
            item.get("graph_label") or item.get("graph_key") or "-",
            item.get("dummy_profile") or item.get("dummy_name") or "-",
            str(item.get("text_mode") or "auto"),
        )

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for item in self._items:
            tag = "loaded" if bool(item.get("loaded")) else "missing"
            self.tree.insert("", tk.END, iid=item["item_key"], values=self._tree_row_values(item), tags=(tag,))

    def _refresh_add_options(self):
        self._add_options = {
            plotting_item_display_name(item): dict(item)
            for item in available_plot_options(self._all_items, self._items)
        }
        values = list(self._add_options.keys())
        self.add_plot_combo.configure(values=values)
        self.add_plot_var.set(values[0] if values else "")

    def _selected_tree_item(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _find_item_index(self, item_key):
        for index, item in enumerate(self._items):
            if str(item.get("item_key")) == str(item_key):
                return index
        return None

    def _selected_item(self):
        item_key = self._selected_tree_item()
        if not item_key:
            return None
        index = self._find_item_index(item_key)
        return None if index is None else self._items[index]

    def _on_tree_select(self, _event=None):
        item = self._selected_item()
        self._selected_item_key = item.get("item_key") if item else None
        self._building_ui = True
        try:
            self.text_mode_var.set(str((item or {}).get("text_mode") or "auto"))
            self.text_editor.delete("1.0", tk.END)
            if item:
                if str(item.get("text_mode") or "auto").strip().lower() == "custom":
                    text_value = str(item.get("custom_text") or "")
                else:
                    text_value = plotting_item_text(item)
                self.text_editor.insert(tk.END, text_value)
        finally:
            self._building_ui = False

    def _apply_text_editor(self, _event=None):
        if self._building_ui:
            return
        item = self._selected_item()
        if not item:
            return
        item["text_mode"] = str(self.text_mode_var.get() or "auto")
        item["custom_text"] = self.text_editor.get("1.0", tk.END).strip()
        self._populate_tree()
        self._reselect_item(item.get("item_key"))
        self._cache_state_in_memory()

    def _reselect_item(self, item_key):
        if not item_key or not self.tree.exists(item_key):
            return
        self.tree.selection_set(item_key)
        self.tree.focus(item_key)

    def _remove_selected(self):
        item_key = self._selected_tree_item()
        if not item_key:
            return
        self._items = [item for item in self._items if str(item.get("item_key")) != str(item_key)]
        self._populate_tree()
        self._refresh_add_options()
        self._refresh_loaded_count()
        self._cache_state_in_memory()

    def _toggle_selected_include(self):
        item = self._selected_item()
        if not item:
            return
        item["included"] = not bool(item.get("included", True))
        self._populate_tree()
        self._reselect_item(item.get("item_key"))
        self._cache_state_in_memory()

    def _move_selected(self, direction):
        item_key = self._selected_tree_item()
        if not item_key:
            return
        index = self._find_item_index(item_key)
        if index is None:
            return
        new_index = index + int(direction)
        if new_index < 0 or new_index >= len(self._items):
            return
        self._items[index], self._items[new_index] = self._items[new_index], self._items[index]
        self._populate_tree()
        self._reselect_item(item_key)
        self._cache_state_in_memory()

    def _add_selected_option(self):
        display = str(self.add_plot_var.get() or "")
        item = dict(self._add_options.get(display) or {})
        if not item:
            return
        self._items.append(item)
        self._populate_tree()
        self._refresh_add_options()
        self._refresh_loaded_count()
        self._reselect_item(item.get("item_key"))
        self._cache_state_in_memory()

    def load_plot_list(self):
        if getattr(self.workbench, "working_df", None) is None:
            messagebox.showwarning("REPORT - PLOTTING", "먼저 데이터를 로드하세요.")
            return
        collected = collect_plot_items(self.workbench)
        self._all_items = [dict(item) for item in collected]
        saved = plotting_payload_from_metadata(getattr(self.workbench, "dataset_metadata", {}) or {})
        self._items = merge_plot_items(saved, self._all_items)
        self._refresh_report_inputs()
        self._refresh_loaded_count()
        self._populate_tree()
        self._refresh_add_options()
        self.status_var.set("Plot list loaded.")
        self._cache_state_in_memory()

    def save_plotting(self):
        if getattr(self.workbench, "working_df", None) is None:
            messagebox.showwarning("REPORT - PLOTTING", "먼저 데이터를 로드하세요.")
            return
        if not self._items:
            self.load_plot_list()
        payload = build_plotting_payload(self._items, plotting_report_fields(self.workbench), template_path=self.template_path_var.get().strip())
        report_saved = dict((getattr(self.workbench, "dataset_metadata", {}) or {}).get("report_saved_results") or {})
        report_saved["plotting_report"] = payload
        saved_path = self.workbench.save_current_dataset_snapshot(
            plotting_save_suffix(),
            metadata_override={"report_saved_results": report_saved},
            prefer_original_source=False,
        )
        if not saved_path:
            messagebox.showwarning("REPORT - PLOTTING", "저장 경로를 만들 수 없습니다.")
            return
        self.status_var.set(f"Saved: {saved_path}")
        messagebox.showinfo("REPORT - PLOTTING", f"Plotting state saved.\n{saved_path}")
        self._loaded_dataset_identity = None

    def _browse_template(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select PPT Template",
            initialdir=str(execution_folder(source_file=__file__)),
            filetypes=(("PowerPoint Template", "*.pptx *.potx *.pptm"), ("All Files", "*.*")),
        )
        if path:
            self.template_path_var.set(path)
            self._cache_state_in_memory()

    def _select_template_for_export(self):
        template_path = self.template_path_var.get().strip()
        if template_path:
            return template_path
        self._browse_template()
        return self.template_path_var.get().strip() or None

    def _select_export_path(self):
        current_source = getattr(self.workbench, "current_file_path", None) or getattr(self.workbench, "source_file_label", None)
        filename = plotting_output_name_from_fields(plotting_report_fields(self.workbench), current_source)
        return filedialog.asksaveasfilename(
            parent=self,
            title="Save PPT Export",
            initialdir=str(execution_folder(source_file=__file__)),
            initialfile=filename,
            defaultextension=".pptx",
            filetypes=(("PowerPoint Presentation", "*.pptx"), ("All Files", "*.*")),
            confirmoverwrite=True,
        ) or None

    def export_ppt(self):
        if getattr(self.workbench, "working_df", None) is None:
            messagebox.showwarning("REPORT - PLOTTING", "먼저 데이터를 로드하세요.")
            return
        if not self._items:
            self.load_plot_list()
        else:
            collected = collect_plot_items(self.workbench)
            if collected:
                self._all_items = [dict(item) for item in collected]
                self._items = merge_plot_items({"items": self._items}, self._all_items)
                self._refresh_loaded_count()
                self._populate_tree()
                self._refresh_add_options()
                if self._selected_item_key:
                    self._reselect_item(self._selected_item_key)
                self._cache_state_in_memory()
        template_path = self._select_template_for_export()
        if not template_path:
            messagebox.showwarning("REPORT - PLOTTING", "PPT 템플릿 파일을 선택하세요.")
            return
        output_path = self._select_export_path()
        if not output_path:
            return
        overlay = _PptExportOverlay(self.winfo_toplevel())
        overlay.show()
        try:
            result = export_plotting_report_to_ppt(
                self.workbench,
                self._items,
                plotting_report_fields(self.workbench),
                output_path=output_path,
                template_path=template_path,
                progress_callback=overlay.update,
            )
        except PptExportError as exc:
            overlay.close()
            messagebox.showwarning("REPORT - PLOTTING", str(exc))
            self.status_var.set(str(exc))
            return
        except Exception as exc:
            overlay.close()
            messagebox.showwarning("REPORT - PLOTTING", f"PPT export failed.\n{exc}")
            self.status_var.set(f"PPT export failed: {exc}")
            return
        overlay.close()
        self.status_var.set(f"PPT export completed. | Saved to: {result.get('output_path')}")
        messagebox.showinfo("REPORT - PLOTTING", f"PPT export completed.\n{result.get('output_path')}")
        try:
            open_export_file(result.get("output_path"))
        except Exception:
            pass

    def reset_session_state(self):
        self._loaded_dataset_identity = None
        self._all_items = []
        self._items = []
        self._add_options = {}
        self._selected_item_key = None
        self.template_path_var.set(plotting_default_template_path())
        self.report_inputs_var.set("-")
        self.loaded_count_var.set("Loaded plots: 0")
        self.status_var.set("Ready")
        self.tree.delete(*self.tree.get_children())
        self.text_editor.delete("1.0", tk.END)

    def on_show(self):
        self._refresh_report_inputs()
        changed = self._load_saved_state()
        if not changed:
            self._refresh_add_options()
