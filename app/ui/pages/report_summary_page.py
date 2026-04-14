import tkinter as tk
from tkinter import messagebox, ttk

from app.report import build_report_snapshot, get_regulation_choices


class ReportSummaryPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        choices = get_regulation_choices()
        self.regulation_var = tk.StringVar(value=(choices[0] if choices else ""))
        self.manufacturer_var = tk.StringVar()
        self.vehicle_var = tk.StringVar()
        self.speed_var = tk.StringVar()
        self.test_date_var = tk.StringVar()
        self.test_id_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Summary report is ready.")
        self.loaded_values_var = tk.StringVar(value="Loaded injury values: 0")
        self._loaded_dataset_identity = None
        self._snapshot = None
        self._valuation_ready = False
        self._build_ui()
        for var in (self.manufacturer_var, self.vehicle_var, self.speed_var, self.test_date_var, self.test_id_var):
            var.trace_add("write", lambda *_: self._cache_report_state_in_memory())

    def _build_ui(self):
        outer = tk.Frame(self, bg="#ffffff")
        outer.pack(fill=tk.BOTH, expand=True, anchor="nw")

        body = tk.Frame(outer, bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, anchor="nw", padx=16, pady=(16, 8))

        header = tk.Frame(body, bg="#ffffff")
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text="REPORT - SUMMARY", font=("Arial", 15, "bold"), bg="#ffffff").pack(side=tk.LEFT)

        top = tk.Frame(body, bg="#ffffff")
        top.pack(fill=tk.X, pady=(0, 12))

        tk.Label(top, text="평가모드", bg="#ffffff", anchor="w").pack(side=tk.LEFT, padx=(2, 10))

        self.regulation_combo = ttk.Combobox(
            top,
            textvariable=self.regulation_var,
            values=get_regulation_choices(),
            state="readonly",
            width=18,
        )
        self.regulation_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.regulation_combo.bind("<<ComboboxSelected>>", self._on_regulation_changed)

        tk.Button(top, text="Valuation", command=self.run_valuation, width=12).pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(top, text="Save", command=self.save_report, width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="Export", command=self.export_placeholder, width=10).pack(side=tk.LEFT, padx=(8, 0))

        input_box = tk.LabelFrame(body, text="Report Inputs", bg="#ffffff")
        input_box.pack(fill=tk.X, pady=(0, 10))
        inputs_row = tk.Frame(input_box, bg="#ffffff")
        inputs_row.pack(fill=tk.X, padx=10, pady=8)
        self._inline_entry(inputs_row, "Manufacturer", self.manufacturer_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self._inline_entry(inputs_row, "Vehicle", self.vehicle_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self._inline_entry(inputs_row, "Speed", self.speed_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self._inline_entry(inputs_row, "Test DATE", self.test_date_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self._inline_entry(inputs_row, "Test ID", self.test_id_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        info_row = tk.Frame(body, bg="#ffffff")
        info_row.pack(fill=tk.X, pady=(0, 10))

        selected_box = tk.LabelFrame(info_row, text="Selected Regulation", bg="#ffffff")
        selected_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        for idx, (label_text, variable) in enumerate((
            ("Regulation", self.regulation_var),
            ("Manufacturer", self.manufacturer_var),
            ("Vehicle", self.vehicle_var),
            ("Speed", self.speed_var),
            ("Test DATE", self.test_date_var),
            ("Test ID", self.test_id_var),
        )):
            pady = (8, 2) if idx == 0 else ((2, 8) if idx == 5 else 2)
            tk.Label(selected_box, text=label_text, bg="#ffffff", width=12, anchor="w").grid(row=idx, column=0, padx=10, pady=pady, sticky="w")
            tk.Label(selected_box, textvariable=variable, bg="#ffffff", anchor="w").grid(row=idx, column=1, padx=(0, 10), pady=pady, sticky="w")

        loaded_box = tk.LabelFrame(info_row, text="Loaded Injury Values", bg="#ffffff")
        loaded_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        tk.Label(
            loaded_box,
            textvariable=self.loaded_values_var,
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=360,
        ).pack(fill=tk.X, padx=10, pady=(8, 4))
        tk.Label(
            loaded_box,
            textvariable=self.status_var,
            bg="#ffffff",
            fg="#374151",
            justify="left",
            anchor="w",
            wraplength=360,
        ).pack(fill=tk.X, padx=10, pady=(0, 8))

        table_box = tk.LabelFrame(body, text="SUMMARY REPORT", bg="#ffffff")
        table_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        guide = tk.Frame(table_box, bg="#ffffff")
        guide.pack(fill=tk.X, padx=8, pady=(8, 0))
        tk.Label(
            guide,
            text=(
                "Status: PASS=limit 만족, FAIL=limit 초과, MISSING=저장된 결과값 없음, N/A=비교 limit 없음 | "
                "Source: Saved value=uid 결과 payload에 구조화된 수치가 저장되어 그 값을 직접 읽음"
            ),
            bg="#ffffff",
            fg="#4b5563",
            justify="left",
            anchor="w",
            wraplength=980,
        ).pack(fill=tk.X)

        columns = ("slot", "dummy", "criterion", "value", "unit", "limit", "status", "uid", "source")
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings", height=16)
        for column, heading, width in (
            ("slot", "Slot", 60),
            ("dummy", "Dummy", 160),
            ("criterion", "Criteria", 250),
            ("value", "Value", 90),
            ("unit", "Unit", 70),
            ("limit", "Limit", 90),
            ("status", "Status", 80),
            ("uid", "Result UID", 290),
            ("source", "Source", 90),
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor="w")
        self.tree.tag_configure("PASS", foreground="#166534")
        self.tree.tag_configure("FAIL", foreground="#b91c1c")
        self.tree.tag_configure("MISSING", foreground="#6b7280")
        self.tree.tag_configure("N/A", foreground="#1f2937")

        y_scroll = ttk.Scrollbar(table_box, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)

    def _inline_entry(self, parent, label, variable):
        frame = tk.Frame(parent, bg="#ffffff")
        tk.Label(frame, text=label, bg="#ffffff", anchor="w").pack(anchor="w")
        tk.Entry(frame, textvariable=variable, width=18).pack(fill=tk.X, pady=(3, 0))
        return frame

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
        self.manufacturer_var.set(fields.get("manufacturer") or "")
        self.vehicle_var.set(fields.get("vehicle") or "")
        self.speed_var.set(fields.get("speed") or "")
        self.test_date_var.set(fields.get("test_date") or "")
        self.test_id_var.set(fields.get("test_id") or "")
        return True

    def _tree_value_text(self, value):
        return "-" if value is None else f"{float(value):.4f}"

    def _populate_tree(self, snapshot):
        self.tree.delete(*self.tree.get_children())
        for row in snapshot.get("rows", []):
            dummy_label = row.get("dummy_profile") or "-"
            value_text = self._tree_value_text(row.get("value"))
            limit_text = self._tree_value_text(row.get("limit"))
            source_name = row.get("value_source")
            source_text = {
                "report_values": "Saved value (report_values)",
                "structured_metrics": "Saved value (structured_metrics)",
                "top_level": "Saved value (top-level payload)",
            }.get(source_name, "-")
            tag = row.get("status") or "N/A"
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row.get("slot_label") or row.get("slot") or "-",
                    dummy_label,
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

    def _report_fields(self):
        return {
            "manufacturer": self.manufacturer_var.get().strip(),
            "vehicle": self.vehicle_var.get().strip(),
            "speed": self.speed_var.get().strip(),
            "test_date": self.test_date_var.get().strip(),
            "test_id": self.test_id_var.get().strip(),
        }

    def _build_report_payload(self):
        snapshot = self._snapshot or build_report_snapshot(self.workbench.dataset_metadata, self.regulation_var.get())
        rows = []
        for row in snapshot.get("rows", []):
            rows.append({
                "slot": row.get("slot"),
                "result_key": row.get("result_key"),
                "result_uid": row.get("result_uid"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "limit": row.get("limit"),
                "status": row.get("status"),
                "value_source": row.get("value_source"),
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

    def _set_waiting_state(self):
        self._snapshot = None
        self._valuation_ready = False
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
        self.loaded_values_var.set("Loaded injury values: waiting for Valuation")
        if getattr(self.workbench, "working_df", None) is None:
            self.status_var.set("Load a dataset first.")
        else:
            self.status_var.set("SUMMARY REPORT is waiting. Click Valuation to load uid-based results.")

    def run_valuation(self):
        snapshot = build_report_snapshot(getattr(self.workbench, "dataset_metadata", {}) or {}, self.regulation_var.get())
        self._snapshot = snapshot
        self._valuation_ready = True
        self._populate_tree(snapshot)
        total_rows = len(snapshot.get("rows") or [])
        loaded_rows = int(snapshot.get("value_count") or 0)
        self.loaded_values_var.set(f"Loaded injury values: {loaded_rows} / {total_rows}")
        if getattr(self.workbench, "working_df", None) is None:
            self.status_var.set("Load a dataset first.")
        elif not snapshot.get("rows"):
            self.status_var.set("No summary rows are available for the selected regulation.")
        elif loaded_rows == 0:
            self.status_var.set("Stored uid results were found, but no numeric values are currently extractable for the selected regulation.")
        else:
            self.status_var.set("Valuation refreshed from existing uid-based saved results.")
        self._cache_report_state_in_memory()

    def save_report(self):
        if getattr(self.workbench, "working_df", None) is None:
            messagebox.showwarning("REPORT", "먼저 데이터를 로드하세요.")
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
                "section": "REPORT",
                "message": f"Summary report saved: {display_name}",
                "display_message": f"Summary report saved as {display_name}",
            }
        )
        saved_path = self.workbench.save_current_dataset_snapshot(
            "_R",
            metadata_override={"report_saved_results": report_saved},
            prefer_original_source=False,
        )
        if not saved_path:
            messagebox.showwarning("REPORT", "REPORT 저장 경로를 만들 수 없습니다.")
            return
        self.status_var.set(f"Saved report dataset: {saved_path}")
        self._loaded_dataset_identity = None
        messagebox.showinfo("REPORT", f"REPORT 데이터가 저장되었습니다.\n{saved_path}")

    def export_placeholder(self):
        messagebox.showinfo("REPORT", "Export는 placeholder만 준비되어 있습니다.")

    def reset_session_state(self):
        self._loaded_dataset_identity = None
        choices = get_regulation_choices()
        self.regulation_var.set(choices[0] if choices else "")
        self.manufacturer_var.set("")
        self.vehicle_var.set("")
        self.speed_var.set("")
        self.test_date_var.set("")
        self.test_id_var.set("")
        self.status_var.set("Summary report is ready.")
        self.loaded_values_var.set("Loaded injury values: waiting for Valuation")
        self._snapshot = None
        self._valuation_ready = False
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())

    def on_show(self):
        changed = self._load_saved_state()
        if changed and not self._valuation_ready:
            self._set_waiting_state()
