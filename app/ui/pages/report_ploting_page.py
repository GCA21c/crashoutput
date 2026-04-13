import tkinter as tk


class ReportPlotingPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg="#ffffff")
        self.workbench = workbench
        self._build_ui()

    def _build_ui(self):
        body = tk.Frame(self, bg="#ffffff")
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(body, bg="#ffffff")
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(header, text="PLOTING", font=("Arial", 15, "bold"), bg="#ffffff").pack(side=tk.LEFT)

        info = tk.LabelFrame(body, text="Status", bg="#ffffff")
        info.pack(fill=tk.X)
        tk.Label(
            info,
            text="PLOTING 메뉴는 자리만 준비되어 있습니다.\nExcel/plot export logic는 아직 연결되지 않았습니다.",
            bg="#ffffff",
            justify="left",
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=12)

    def reset_session_state(self):
        pass

    def on_show(self):
        pass
