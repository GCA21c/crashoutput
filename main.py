# ssh개발환경 시작 20260408 by gca21c



from pathlib import Path

import tkinter as tk
from matplotlib import font_manager, rcParams

from app.shell import CrashAnalysisWorkbench


def _configure_matplotlib_font():
    candidate_names = (
        "Malgun Gothic",
        "NanumGothic",
        "AppleGothic",
    )
    available_names = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidate_names:
        if name in available_names:
            rcParams["font.family"] = name
            rcParams["axes.unicode_minus"] = False
            return


if __name__ == "__main__":
    _configure_matplotlib_font()
    root = tk.Tk()
    root.title("Crashoutput™ Ver 1.0")
    root.geometry("1800x980")
    try:
        icon_path = Path(__file__).parent / "app" / "ui" / "components" / "assets" / "crash_icon.ico"
        if icon_path.exists():
            root.iconbitmap(default=str(icon_path))
    except Exception:
        pass
    app = CrashAnalysisWorkbench(root)
    app.pack(fill=tk.BOTH, expand=True)
    root.mainloop()
