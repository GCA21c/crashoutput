import tkinter as tk

from app.ui.styles import HEADER_FONT, PAGE_BG


class ReportPlotingPage(tk.Frame):
    """Legacy class name kept for the existing report_ploting page key."""

    def __init__(self, parent, workbench):
        super().__init__(parent, bg=PAGE_BG)
        self.workbench = workbench
        self._build_ui()

    def _build_ui(self):
        body = tk.Frame(self, bg=PAGE_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(body, bg=PAGE_BG)
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(header, text="REPORT - PLOTTING", font=HEADER_FONT, bg=PAGE_BG).pack(side=tk.LEFT)

        info = tk.LabelFrame(body, text="Status", bg=PAGE_BG)
        info.pack(fill=tk.X)
        tk.Label(
            info,
            text="PLOTTING 메뉴는 자리만 준비되어 있습니다.\nExcel/plot export logic는 아직 연결되지 않았습니다.",
            bg=PAGE_BG,
            justify="left",
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=12)

    def reset_session_state(self):
        pass

    def on_show(self):
        pass
