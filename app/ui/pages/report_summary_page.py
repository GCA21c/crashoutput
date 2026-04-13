import tkinter as tk
from tkinter import messagebox, ttk

from app.core.utils.formatting import fmt_value
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
        self.test_id_var = tk.StringVar()
        self.status_var = tk.StringVar(value="FMVSS 208 summary report is ready.")
        self.loaded_values_var = tk.StringVar(value="Loaded injury values: 0")
        self._loaded_dataset_identity = None
        self._snapshot = None
        self._build_ui()

    def _build_ui(self):
        outer = tk.Frame(self, bg="#ffffff")
        outer.pack(fill=tk.BOTH, expand=True, anchor="nw")

        body = tk.Frame(outer, bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, anchor="nw", padx=16, pady=(16, 8))

        top = tk.Frame(body, bg="#ffffff")
        top.pack(fill=tk.X, pady=(0, 10))

        self.regulation_combo = ttk.Combobox(
            top,
            textvariable=self.regulation_var,
            values=get_regulation_choices(),
            state="readonly",
            width=18,
        )
        self.regulation_combo.pack(side=tk.LEFT)
        self.regulation_combo.bind("<<ComboboxSelected>>", self._on_regulation_changed)

        tk.Button(top, text="Valuation", command=self.run_valuation, width=12).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="Save", command=self.save_report, width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="Export", command=self.export_placeholder, width=10).pack(side=tk.LEFT, padx=(8, 0))

        info_row = tk.Frame(body, bg="#ffffff")
        info_row.pack(fill=tk.X, pady=(0, 10))

        selected_box = tk.LabelFrame(info_row, text="Selected Regulation", bg="#ffffff")
        selected_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        tk.Label(selected_box, text="Regulation", bg="#ffffff", width=12, anchor="w").grid(row=0, column=0, padx=10, pady=(10, 4), sticky="w")
        tk.Label(selected_box, textvariable=self.regulation_var, bg="#ffffff", anchor="w").grid(row=0, column=1, padx=(0, 10), pady=(10, 4), sticky="w")
        tk.Label(selected_box, text="Manufacturer", bg="#ffffff", width=12, anchor="w").grid(row=1, column=0, padx=10, pady=4, sticky="w")
        tk.Label(selected_box, textvariable=self.manufacturer_var, bg="#ffffff", anchor="w").grid(row=1, column=1, padx=(0, 10), pady=4, sticky="w")
        tk.Label(selected_box, text="Vehicle", bg="#ffffff", width=12, anchor="w").grid(row=2, column=0, padx=10, pady=4, sticky="w")
        tk.Label(selected_box, textvariable=self.vehicle_var, bg="#ffffff", anchor="w").grid(row=2, column=1, padx=(0, 10), pady=4, sticky="w")
        tk.Label(selected_box, text="Speed", bg="#ffffff", width=12, anchor="w").grid(row=3, column=0, padx=10, pady=4, sticky="w")
        tk.Label(selected_box, textvariable=self.speed_var, bg="#ffffff", anchor="w").grid(row=3, column=1, padx=(0, 10), pady=4, sticky="w")
        tk.Label(selected_box, text="Test ID", bg="#ffffff", width=12, anchor="w").grid(row=4, column=0, padx=10, pady=(4, 10), sticky="w")
        tk.Label(selected_box, textvariable=self.test_id_var, bg="#ffffff", anchor="w").grid(row=4, column=1, padx=(0, 10), pady=(4, 10), sticky="w")

        loaded_box = tk.LabelFrame(info_row, text="Loaded Injury Values", bg="#ffffff")
        loaded_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        tk.Label(
            loaded_box,
            textvariable=self.loaded_values_var,
            bg="#ffffff",
            justify="left",
            anchor="w",
            wraplength=360,
        ).pack(fill=tk.X, padx=10, pady=(10, 6))
        tk.Label(
            loaded_box,
            textvariable=self.status_var,
            bg="#ffffff",
            fg="#374151",
            justify="left",
            anchor="w",
            wraplength=360,
        ).pack(fill=tk.X, padx=10, pady=(0, 10))

        table_box = tk.LabelFrame(body, text="SUMMARY REPORT", bg="#ffffff")
        table_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("slot", "dummy", "criterion", "value", "unit", "limit", "status", "uid", "source")
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings", height=16)
        for column, heading, width in (
            ("slot", "Slot", 60),
            ("dummy", "Dummy", 160),
            ("criterion", "Criteria", 210),
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

        input_box = tk.LabelFrame(body, text="Report Inputs", bg="#ffffff")
        input_box.pack(fill=tk.X)
        self._entry_row(input_box, 0, "Manufacturer", self.manufacturer_var)
        self._entry_row(input_box, 1, "Vehicle", self.vehicle_var)
        self._entry_row(input_box, 2, "Speed", self.speed_var)
        self._entry_row(input_box, 3, "Test ID", self.test_id_var)

    def _entry_row(self, parent, row, label, variable):
        tk.Label(parent, text=label, bg="#ffffff", width=12, anchor="w").grid(row=row, column=0, padx=10, pady=6, sticky="w")
        tk.Entry(parent, textvariable=variable, width=42).grid(row=row, column=1, padx=(0, 10), pady=6, sticky="w")

    def _dataset_identity(self):
        current = getattr(self.workbench, "current_file_path", None) or ""
        source = dict(getattr(self.workbench, "dataset_metadata", {}) or {}).get("source_file_path") or ""
        return f"{current}|{source}"

    def _load_saved_state(self):
        identity = self._dataset_identity()
        if identity == self._loaded_dataset_identity:
            return
        self._loaded_dataset_identity = identity
        saved = dict((dict(getattr(self.workbench, "dataset_metadata", {}) or {}).get("report_saved_results") or {}).get("summary_report") or {})
        self.regulation_var.set(saved.get("regulation") or (get_regulation_choices()[0] if get_regulation_choices() else ""))
        fields = dict(saved.get("report_fields") or {})
        self.manufacturer_var.set(fields.get("manufacturer") or "")
        self.vehicle_var.set(fields.get("vehicle") or "")
        self.speed_var.set(fields.get("speed") or "")
        self.test_id_var.set(fields.get("test_id") or "")

    def _format_metric(self, value, unit):
        if value is None:
            return "-"
        unit_text = "" if unit in ("", "-") else unit
        return fmt_value(value, unit_text, decimals=4, unit_style="suffix_space" if unit_text else "suffix")

    def _tree_value_text(self, value):
        return "-" if value is None else f"{float(value):.4f}"

    def _populate_tree(self, snapshot):
        self.tree.delete(*self.tree.get_children())
        for row in snapshot.get("rows", []):
            dummy_label = row.get("dummy_name") or row.get("dummy_profile") or "-"
            value_text = self._tree_value_text(row.get("value"))
            limit_text = self._tree_value_text(row.get("limit"))
            source_text = "payload" if row.get("value_source") == "payload" else "summary" if row.get("value_source") == "summary_text" else "-"
            tag = row.get("status") or "N/A"
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row.get("slot") or "-",
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

    def _on_regulation_changed(self, _event=None):
        self.run_valuation()

    def run_valuation(self):
        snapshot = build_report_snapshot(getattr(self.workbench, "dataset_metadata", {}) or {}, self.regulation_var.get())
        self._snapshot = snapshot
        self._populate_tree(snapshot)
        total_rows = len(snapshot.get("rows") or [])
        loaded_rows = int(snapshot.get("value_count") or 0)
        self.loaded_values_var.set(f"Loaded injury values: {loaded_rows} / {total_rows}")
        if getattr(self.workbench, "working_df", None) is None:
            self.status_var.set("Load a dataset first.")
        elif not snapshot.get("rows"):
            self.status_var.set("No FMVSS 208 summary rows are available.")
        elif loaded_rows == 0:
            self.status_var.set("Stored uid results were found, but no numeric FMVSS 208 values are currently extractable.")
        else:
            self.status_var.set("Valuation refreshed from existing uid-based saved results.")

    def save_report(self):
        if getattr(self.workbench, "working_df", None) is None:
            messagebox.showwarning("REPORT", "먼저 데이터를 로드하세요.")
            return
        self.run_valuation()
        report_saved = dict((getattr(self.workbench, "dataset_metadata", {}) or {}).get("report_saved_results") or {})
        report_saved["summary_report"] = self._build_report_payload()
        save_name = self.workbench._build_original_source_save_path("_R")
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
            prefer_original_source=True,
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
        self.test_id_var.set("")
        self.status_var.set("FMVSS 208 summary report is ready.")
        self.loaded_values_var.set("Loaded injury values: 0")
        self._snapshot = None
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())

    def on_show(self):
        self._load_saved_state()
        self.run_valuation()
