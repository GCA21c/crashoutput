import tkinter as tk
from tkinter import messagebox, ttk

from app.report import (
    ExcelExportError,
    build_report_snapshot,
    export_summary_report_to_excel,
    get_regulation_choices,
    get_regulation_definition,
)
from app.report.exporters.runtime import open_export_file, unique_export_path
from app.ui.pages.report_summary_constants import (
    BUTTON_EXCEL_EXPORT,
    BUTTON_SAVE,
    BUTTON_VALUATION,
    INFO_GROUP_TITLE,
    INPUT_GROUP_TITLE,
    LOADED_GROUP_TITLE,
    LOADED_VALUES_COUNT,
    LOADED_VALUES_INITIAL,
    LOADED_VALUES_WAITING,
    PAGE_TITLE,
    REGULATION_MODE_LABEL,
    REPORT_INPUT_FIELDS,
    SELECTED_REGULATION_FIELDS,
    SOURCE_DISPLAY_NAMES,
    DIALOG_TITLE_REPORT,
    HISTORY_SUMMARY_SAVED,
    HISTORY_SUMMARY_SAVED_DISPLAY,
    INFO_EXCEL_EXPORT_COMPLETED,
    INFO_REPORT_SAVED_KO,
    STATUS_LOAD_DATASET_FIRST,
    STATUS_LOADED_SAVED,
    STATUS_NO_NUMERIC_VALUES,
    STATUS_NO_ROWS,
    STATUS_READY,
    STATUS_EXCEL_EXPORT_COMPLETED,
    STATUS_EXCEL_EXPORT_FAILED,
    STATUS_REPORT_SAVED,
    STATUS_VALUATION_REFRESHED,
    STATUS_WAITING,
    SUMMARY_GUIDE_TEXT,
    SUMMARY_TABLE_COLUMNS,
    SUMMARY_TABLE_COLUMN_SPECS,
    TABLE_GROUP_TITLE,
    TREE_STATUS_TAG_COLORS,
    WARNING_EXCEL_EXPORT_FAILED,
    WARNING_EXCEL_OPEN_FAILED,
    WARNING_LOAD_DATA_FIRST_KO,
    WARNING_REPORT_SAVE_PATH_KO,
    WARNING_VALUATION_REQUIRED_KO,
)
from app.ui.styles import HEADER_FONT, MUTED_FG, PAGE_BG, TEXT_FG


class ReportSummaryPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg=PAGE_BG)
        self.workbench = workbench
        choices = get_regulation_choices()
        self.regulation_var = tk.StringVar(value=(choices[0] if choices else ""))
        self.manufacturer_var = tk.StringVar()
        self.vehicle_var = tk.StringVar()
        self.speed_var = tk.StringVar()
        self.test_date_var = tk.StringVar()
        self.test_id_var = tk.StringVar()
        self.status_var = tk.StringVar(value=STATUS_READY)
        self.loaded_values_var = tk.StringVar(value=LOADED_VALUES_INITIAL)
        self._loaded_dataset_identity = None
        self._snapshot = None
        self._valuation_ready = False
        self._build_ui()
        for var in self._report_input_variables().values():
            var.trace_add("write", lambda *_: self._cache_report_state_in_memory())

    def _build_ui(self):
        outer = tk.Frame(self, bg=PAGE_BG)
        outer.pack(fill=tk.BOTH, expand=True, anchor="nw")

        body = tk.Frame(outer, bg=PAGE_BG)
        body.pack(fill=tk.BOTH, expand=True, anchor="nw", padx=16, pady=(16, 8))

        header = tk.Frame(body, bg=PAGE_BG)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text=PAGE_TITLE, font=HEADER_FONT, bg=PAGE_BG).pack(side=tk.LEFT)

        top = tk.Frame(body, bg=PAGE_BG)
        top.pack(fill=tk.X, pady=(0, 12))

        tk.Label(top, text=REGULATION_MODE_LABEL, bg=PAGE_BG, anchor="w").pack(side=tk.LEFT, padx=(2, 10))

        self.regulation_combo = ttk.Combobox(
            top,
            textvariable=self.regulation_var,
            values=get_regulation_choices(),
            state="readonly",
            width=18,
        )
        self.regulation_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.regulation_combo.bind("<<ComboboxSelected>>", self._on_regulation_changed)

        tk.Button(top, text=BUTTON_VALUATION, command=self.run_valuation, width=12).pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(top, text=BUTTON_SAVE, command=self.save_report, width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text=BUTTON_EXCEL_EXPORT, command=self.export_excel, width=14).pack(side=tk.LEFT, padx=(8, 0))

        input_box = tk.LabelFrame(body, text=INPUT_GROUP_TITLE, bg=PAGE_BG)
        input_box.pack(fill=tk.X, pady=(0, 10))
        inputs_row = tk.Frame(input_box, bg=PAGE_BG)
        inputs_row.pack(fill=tk.X, padx=10, pady=8)
        input_vars = self._report_input_variables()
        for index, (label, field_key) in enumerate(REPORT_INPUT_FIELDS):
            padx = (0, 6) if index == 0 else ((6, 0) if index == len(REPORT_INPUT_FIELDS) - 1 else 6)
            self._inline_entry(inputs_row, label, input_vars[field_key]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=padx)

        info_row = tk.Frame(body, bg=PAGE_BG)
        info_row.pack(fill=tk.X, pady=(0, 10))

        selected_box = tk.LabelFrame(info_row, text=INFO_GROUP_TITLE, bg=PAGE_BG)
        selected_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        selected_vars = self._selected_regulation_variables()
        for idx, (label_text, field_key) in enumerate(SELECTED_REGULATION_FIELDS):
            pady = (8, 2) if idx == 0 else ((2, 8) if idx == len(SELECTED_REGULATION_FIELDS) - 1 else 2)
            tk.Label(selected_box, text=label_text, bg=PAGE_BG, width=12, anchor="w").grid(row=idx, column=0, padx=10, pady=pady, sticky="w")
            tk.Label(selected_box, textvariable=selected_vars[field_key], bg=PAGE_BG, anchor="w").grid(row=idx, column=1, padx=(0, 10), pady=pady, sticky="w")

        loaded_box = tk.LabelFrame(info_row, text=LOADED_GROUP_TITLE, bg=PAGE_BG)
        loaded_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        tk.Label(
            loaded_box,
            textvariable=self.loaded_values_var,
            bg=PAGE_BG,
            justify="left",
            anchor="w",
            wraplength=360,
        ).pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(
            loaded_box,
            textvariable=self.status_var,
            bg=PAGE_BG,
            fg=TEXT_FG,
            justify="left",
            anchor="w",
            wraplength=360,
        ).pack(fill=tk.X, padx=10, pady=(0, 8))

        table_box = tk.LabelFrame(body, text=TABLE_GROUP_TITLE, bg=PAGE_BG)
        table_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        guide = tk.Frame(table_box, bg=PAGE_BG)
        guide.pack(fill=tk.X, padx=8, pady=(8, 0))
        tk.Label(
            guide,
            text=SUMMARY_GUIDE_TEXT,
            bg=PAGE_BG,
            fg=MUTED_FG,
            justify="left",
            anchor="w",
            wraplength=980,
        ).pack(fill=tk.X)

        self.tree = ttk.Treeview(table_box, columns=SUMMARY_TABLE_COLUMNS, show="headings", height=16)
        for column, heading, width in SUMMARY_TABLE_COLUMN_SPECS:
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor="w")
        for tag, color in TREE_STATUS_TAG_COLORS.items():
            self.tree.tag_configure(tag, foreground=color)

        y_scroll = ttk.Scrollbar(table_box, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

    def _inline_entry(self, parent, label, variable):
        frame = tk.Frame(parent, bg=PAGE_BG)
        tk.Label(frame, text=label, bg=PAGE_BG, anchor="w").pack(anchor="w")
        tk.Entry(frame, textvariable=variable, width=18).pack(fill=tk.X, pady=(3, 0))
        return frame

    def _report_input_variables(self):
        return {
            "manufacturer": self.manufacturer_var,
            "vehicle": self.vehicle_var,
            "speed": self.speed_var,
            "test_date": self.test_date_var,
            "test_id": self.test_id_var,
        }

    def _selected_regulation_variables(self):
        variables = self._report_input_variables()
        variables["regulation"] = self.regulation_var
        return variables

    def _set_report_input_values(self, values):
        values = dict(values or {})
        for field_key, variable in self._report_input_variables().items():
            variable.set(values.get(field_key) or "")

    def _dataset_identity(self):
        current = getattr(self.workbench, "current_file_path", None) or ""
        source = dict(getattr(self.workbench, "dataset_metadata", {}) or {}).get("source_file_path") or ""
        return f"{current}|{source}"

    def _load_saved_state(self):
        identity = self._dataset_identity()
        if identity == self._loaded_dataset_identity:
            return False
        self._loaded_dataset_identity = identity
        saved = dict((dict(getattr(self.workbench, "dataset_metadata", {}) or {}).get("report_saved_results") or {}).get("summary_report") or {})
        self.regulation_var.set(saved.get("regulation") or (get_regulation_choices()[0] if get_regulation_choices() else ""))
        fields = dict(saved.get("report_fields") or {})
        self._set_report_input_values(fields)
        restored_snapshot = self._snapshot_from_saved_report(saved)
        if restored_snapshot:
            self._snapshot = restored_snapshot
            self._valuation_ready = True
            self._populate_tree(restored_snapshot)
            total_rows = len(restored_snapshot.get("rows") or [])
            loaded_rows = int(restored_snapshot.get("value_count") or 0)
            self._set_loaded_values_count(loaded_rows, total_rows)
            self.status_var.set(STATUS_LOADED_SAVED)
        else:
            self._snapshot = None
            self._valuation_ready = False
        return True

    def _snapshot_from_saved_report(self, saved):
        saved = dict(saved or {})
        saved_rows = list(saved.get("rows") or [])
        if not saved_rows:
            return None
        definition = get_regulation_definition(saved.get("regulation") or self.regulation_var.get())
        item_map = {item.get("result_key"): dict(item) for item in (definition or {}).get("items", ())}
        slot_map = {}
        for slot_info in list(saved.get("slots") or []):
            info = dict(slot_info or {})
            slot_key = info.get("slot")
            if slot_key:
                slot_map[slot_key] = info
        slot_order = {slot: index for index, slot in enumerate(slot_map.keys())}
        item_order = {item.get("result_key"): index for index, item in enumerate((definition or {}).get("items", ()))}

        rows = []
        value_count = 0
        sorted_saved_rows = sorted(
            saved_rows,
            key=lambda row: (
                slot_order.get(dict(row or {}).get("slot"), len(slot_order)),
                item_order.get(dict(row or {}).get("result_key"), len(item_order)),
            ),
        )
        for saved_row in sorted_saved_rows:
            row = dict(saved_row or {})
            item = item_map.get(row.get("result_key"), {})
            slot_info = dict(slot_map.get(row.get("slot")) or {})
            value = row.get("value")
            if value is not None:
                value_count += 1
            rows.append({
                "slot": row.get("slot"),
                "slot_label": row.get("slot_label") or slot_info.get("slot_label") or row.get("slot") or "-",
                "dummy_name": row.get("dummy_name") or slot_info.get("dummy_name") or "",
                "dummy_profile": row.get("dummy_profile") or slot_info.get("dummy_profile") or "",
                "section_key": row.get("section_key") or item.get("section_key"),
                "region": row.get("region") or str(row.get("section_key") or item.get("section_key") or "-").upper(),
                "result_key": row.get("result_key"),
                "label": row.get("label") or item.get("label") or "-",
                "unit": row.get("unit") or item.get("unit") or "",
                "value": value,
                "limit": row.get("limit"),
                "status": row.get("status"),
                "comparison": row.get("comparison") or item.get("comparison"),
                "result_uid": row.get("result_uid") or "",
                "value_source": row.get("value_source"),
                "value_path": row.get("value_path") or "",
                "limit_source": row.get("limit_source") or "",
            })

        return {
            "regulation_name": saved.get("regulation") or self.regulation_var.get(),
            "definition": definition,
            "slots": list(saved.get("slots") or []),
            "rows": rows,
            "excel_mapping": dict(saved.get("excel_mapping") or {}),
            "value_count": value_count,
        }

    def _tree_value_text(self, value):
        return "-" if value is None else f"{float(value):.4f}"

    def _populate_tree(self, snapshot):
        self.tree.delete(*self.tree.get_children())
        for row in snapshot.get("rows", []):
            dummy_label = row.get("dummy_profile") or "-"
            value_text = self._tree_value_text(row.get("value"))
            limit_text = self._tree_value_text(row.get("limit"))
            source_name = row.get("value_source")
            source_text = SOURCE_DISPLAY_NAMES.get(source_name, "-")
            tag = row.get("status") or "N/A"
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row.get("slot_label") or row.get("slot") or "-",
                    dummy_label,
                    row.get("region") or str(row.get("section_key") or "-").upper(),
                    row.get("label") or "-",
                    value_text,
                    row.get("unit") or "-",
                    limit_text,
                    tag,
                    row.get("result_uid") or "-",
                    source_text,
                ),
                tags=(tag,),
            )

    def _occupant_slots_from_config(self, config):
        config = dict(config or {})
        slot_meta = dict(config.get("slot_meta") or {})
        ordered_slots = []
        for slot in list(config.get("active_positions") or []) + list(config.get("row_positions") or []):
            slot_key = str(slot or "").strip().upper()
            if slot_key and slot_key not in ordered_slots:
                ordered_slots.append(slot_key)
        for slot, meta in slot_meta.items():
            slot_key = str(slot or "").strip().upper()
            if not slot_key or slot_key in ordered_slots:
                continue
            meta = dict(meta or {})
            if str(meta.get("dummy_name") or "").strip() or str(meta.get("dummy_profile") or "").strip():
                ordered_slots.append(slot_key)
        result = []
        for slot_key in ordered_slots:
            meta = dict(slot_meta.get(slot_key) or {})
            result.append({
                "slot": slot_key,
                "dummy_name": str(meta.get("dummy_name") or "").strip(),
                "dummy_profile": str(meta.get("dummy_profile") or "").strip(),
            })
        return result

    def _merge_occupant_slots(self, *slot_groups):
        merged = {}
        order = []
        for group in slot_groups:
            for info in list(group or []):
                info = dict(info or {})
                slot_key = str(info.get("slot") or "").strip().upper()
                if not slot_key:
                    continue
                if slot_key not in merged:
                    merged[slot_key] = {"slot": slot_key, "dummy_name": "", "dummy_profile": ""}
                    order.append(slot_key)
                current = merged[slot_key]
                dummy_name = str(info.get("dummy_name") or "").strip()
                dummy_profile = str(info.get("dummy_profile") or "").strip()
                if dummy_name and not current["dummy_name"]:
                    current["dummy_name"] = dummy_name
                if dummy_profile and not current["dummy_profile"]:
                    current["dummy_profile"] = dummy_profile
        return [merged[slot] for slot in order]

    def _report_fields(self):
        metadata = dict(getattr(self.workbench, "dataset_metadata", {}) or {})
        saved_summary = dict((dict(metadata.get("report_saved_results") or {}).get("summary_report") or {}))
        saved_fields = dict(saved_summary.get("report_fields") or {})
        current_config = self.workbench.get_shared_dummy_config() if hasattr(self.workbench, "get_shared_dummy_config") else {}
        metadata_config = dict(metadata.get("shared_dummy_config") or {})
        occupant_slots = self._merge_occupant_slots(
            self._occupant_slots_from_config(current_config),
            self._occupant_slots_from_config(metadata_config),
            saved_fields.get("occupant_slots"),
            (self._snapshot or {}).get("slots"),
            saved_summary.get("slots"),
        )
        report_fields = {
            field_key: variable.get().strip()
            for field_key, variable in self._report_input_variables().items()
        }
        report_fields["occupant_slots"] = occupant_slots
        return report_fields

    def _build_report_payload(self):
        snapshot = self._snapshot or build_report_snapshot(self.workbench.dataset_metadata, self.regulation_var.get())
        rows = []
        for row in snapshot.get("rows", []):
            rows.append({
                "slot": row.get("slot"),
                "slot_label": row.get("slot_label"),
                "dummy_name": row.get("dummy_name"),
                "dummy_profile": row.get("dummy_profile"),
                "section_key": row.get("section_key"),
                "region": row.get("region"),
                "result_key": row.get("result_key"),
                "label": row.get("label"),
                "result_uid": row.get("result_uid"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "limit": row.get("limit"),
                "status": row.get("status"),
                "comparison": row.get("comparison"),
                "value_source": row.get("value_source"),
                "value_path": row.get("value_path"),
                "limit_source": row.get("limit_source"),
            })
        return {
            "report_type": "summary_report",
            "regulation": snapshot.get("regulation_name") or self.regulation_var.get(),
            "report_fields": self._report_fields(),
            "slots": list(snapshot.get("slots") or []),
            "rows": rows,
            "excel_mapping": dict(snapshot.get("excel_mapping") or {}),
        }

    def _cache_report_state_in_memory(self):
        metadata = dict(getattr(self.workbench, "dataset_metadata", {}) or {})
        report_saved = dict(metadata.get("report_saved_results") or {})
        existing = dict(report_saved.get("summary_report") or {})
        existing["regulation"] = self.regulation_var.get()
        existing["report_fields"] = self._report_fields()
        if self._snapshot:
            existing["slots"] = list(self._snapshot.get("slots") or [])
            existing["rows"] = list(self._build_report_payload().get("rows") or [])
            existing["excel_mapping"] = dict(self._snapshot.get("excel_mapping") or {})
            existing["report_type"] = "summary_report"
        report_saved["summary_report"] = existing
        metadata["report_saved_results"] = report_saved
        self.workbench.dataset_metadata = metadata

    def _on_regulation_changed(self, _event=None):
        self._cache_report_state_in_memory()
        self._set_waiting_state()

    def _show_report_warning(self, message):
        messagebox.showwarning(DIALOG_TITLE_REPORT, message)

    def _show_report_info(self, message):
        messagebox.showinfo(DIALOG_TITLE_REPORT, message)

    def _set_loaded_values_count(self, loaded_rows, total_rows):
        self.loaded_values_var.set(
            LOADED_VALUES_COUNT.format(loaded_rows=loaded_rows, total_rows=total_rows)
        )

    def _set_waiting_state(self):
        self._snapshot = None
        self._valuation_ready = False
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
        self.loaded_values_var.set(LOADED_VALUES_WAITING)
        if getattr(self.workbench, "working_df", None) is None:
            self.status_var.set(STATUS_LOAD_DATASET_FIRST)
        else:
            self.status_var.set(STATUS_WAITING)

    def run_valuation(self):
        snapshot = build_report_snapshot(getattr(self.workbench, "dataset_metadata", {}) or {}, self.regulation_var.get())
        self._snapshot = snapshot
        self._valuation_ready = True
        self._populate_tree(snapshot)
        total_rows = len(snapshot.get("rows") or [])
        loaded_rows = int(snapshot.get("value_count") or 0)
        self._set_loaded_values_count(loaded_rows, total_rows)
        if getattr(self.workbench, "working_df", None) is None:
            self.status_var.set(STATUS_LOAD_DATASET_FIRST)
        elif not snapshot.get("rows"):
            self.status_var.set(STATUS_NO_ROWS)
        elif loaded_rows == 0:
            self.status_var.set(STATUS_NO_NUMERIC_VALUES)
        else:
            self.status_var.set(STATUS_VALUATION_REFRESHED)
        self._cache_report_state_in_memory()

    def save_report(self):
        if getattr(self.workbench, "working_df", None) is None:
            self._show_report_warning(WARNING_LOAD_DATA_FIRST_KO)
            return
        if not self._valuation_ready:
            self.run_valuation()
        report_saved = dict((getattr(self.workbench, "dataset_metadata", {}) or {}).get("report_saved_results") or {})
        report_saved["summary_report"] = self._build_report_payload()
        save_name = self.workbench._build_next_save_path("_R")
        display_name = save_name or "_R"
        self.workbench.add_history_entry(
            {
                "type": "save",
                "section": DIALOG_TITLE_REPORT,
                "message": HISTORY_SUMMARY_SAVED.format(display_name=display_name),
                "display_message": HISTORY_SUMMARY_SAVED_DISPLAY.format(display_name=display_name),
            }
        )
        saved_path = self.workbench.save_current_dataset_snapshot(
            "_R",
            metadata_override={"report_saved_results": report_saved},
            prefer_original_source=False,
        )
        if not saved_path:
            self._show_report_warning(WARNING_REPORT_SAVE_PATH_KO)
            return
        self.status_var.set(STATUS_REPORT_SAVED.format(saved_path=saved_path))
        self._loaded_dataset_identity = None
        self._show_report_info(INFO_REPORT_SAVED_KO.format(saved_path=saved_path))

    def _unique_export_path(self):
        return unique_export_path(self.test_id_var.get().strip(), source_file=__file__)

    def _open_export_file(self, path):
        try:
            open_export_file(path)
        except Exception as exc:
            self._show_report_warning(WARNING_EXCEL_OPEN_FAILED.format(path=path, error=exc))

    def export_excel(self):
        if not self._valuation_ready:
            self.run_valuation()
        if not self._snapshot:
            self._show_report_warning(WARNING_VALUATION_REQUIRED_KO)
            return
        output_path = self._unique_export_path()
        try:
            result = export_summary_report_to_excel(
                self._snapshot,
                self._report_fields(),
                output_path,
            )
        except ExcelExportError as exc:
            self._show_report_warning(str(exc))
            self.status_var.set(STATUS_EXCEL_EXPORT_FAILED.format(error=exc))
            return
        except Exception as exc:
            self._show_report_warning(WARNING_EXCEL_EXPORT_FAILED.format(error=exc))
            self.status_var.set(STATUS_EXCEL_EXPORT_FAILED.format(error=exc))
            return

        output_path = result.get("output_path")
        detail = INFO_EXCEL_EXPORT_COMPLETED.format(output_path=output_path)
        self.status_var.set(STATUS_EXCEL_EXPORT_COMPLETED.format(output_path=output_path))
        self._show_report_info(detail)
        self._open_export_file(output_path)

    def reset_session_state(self):
        self._loaded_dataset_identity = None
        choices = get_regulation_choices()
        self.regulation_var.set(choices[0] if choices else "")
        self._set_report_input_values({})
        self.status_var.set(STATUS_READY)
        self.loaded_values_var.set(LOADED_VALUES_WAITING)
        self._snapshot = None
        self._valuation_ready = False
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())

    def on_show(self):
        changed = self._load_saved_state()
        if changed and not self._valuation_ready:
            self._set_waiting_state()
