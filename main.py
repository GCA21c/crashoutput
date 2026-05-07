# ssh개발환경 시작 20260408 by gca21c



from pathlib import Path

import tkinter as tk


def _set_splash_status(splash, status_var, text):
    if splash is None or status_var is None:
        return
    status_var.set(str(text or "Loading..."))
    try:
        splash.update_idletasks()
        splash.update()
    except Exception:
        pass


def _show_startup_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.configure(bg="#242424")
    splash.attributes("-topmost", True)
    width = 524
    height = 305
    screen_w = splash.winfo_screenwidth()
    screen_h = splash.winfo_screenheight()
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")
    panel = tk.Frame(splash, bg="#242424")
    panel.pack(fill=tk.BOTH, expand=True)
    tk.Label(
        panel,
        text="Powered by GCA21c with Codex",
        bg="#242424",
        fg="#dedede",
        font=("Segoe UI", 10, "italic"),
    ).place(relx=1.0, rely=1.0, x=-14, y=-10, anchor="se")
    content = tk.Frame(panel, bg="#242424")
    content.place(x=12, y=14, anchor="nw")
    tk.Label(
        content,
        text="CRASH OUTPUT™",
        bg="#242424",
        fg="#d6d6d6",
        font=("Segoe UI", 21, "bold"),
    ).pack(anchor="w", pady=(0, 0))
    tk.Label(
        content,
        text="Crash Data Analysis System",
        bg="#242424",
        fg="#d0d0d0",
        font=("Segoe UI", 17),
    ).pack(anchor="w", pady=(0, 0))
    meta = tk.Frame(panel, bg="#242424")
    meta.place(relx=0.5, rely=0.58, anchor="center")
    tk.Label(
        meta,
        text="Ver 1.0 | Build260296",
        bg="#242424",
        fg="#cfcfcf",
        font=("Segoe UI", 10),
    ).pack(anchor="center")
    status_var = tk.StringVar(value="Initializing...")
    tk.Label(
        meta,
        textvariable=status_var,
        bg="#242424",
        fg="#9ca3af",
        font=("Segoe UI", 9),
        width=46,
        anchor="center",
        justify="center",
    ).pack(anchor="center", pady=(18, 0))
    splash.update_idletasks()
    splash.update()
    return splash, status_var


def _configure_matplotlib_font():
    from matplotlib import font_manager, rcParams

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
    splash, splash_status = _show_startup_splash()
    _set_splash_status(splash, splash_status, "Loading matplotlib font manager...")
    _configure_matplotlib_font()
    _set_splash_status(splash, splash_status, "Loading application shell...")
    from app.shell import CrashAnalysisWorkbench

    _set_splash_status(splash, splash_status, "Creating main window...")
    root = tk.Tk()
    root.withdraw()
    root.title("Crashoutput™ Ver 1.0")
    root.geometry("1800x980")
    try:
        _set_splash_status(splash, splash_status, "Loading crash_icon.ico...")
        icon_path = Path(__file__).parent / "app" / "ui" / "components" / "assets" / "crash_icon.ico"
        if icon_path.exists():
            root.iconbitmap(default=str(icon_path))
    except Exception:
        pass
    _set_splash_status(splash, splash_status, "Loading CrashAnalysisWorkbench...")
    app = CrashAnalysisWorkbench(root)
    app.pack(fill=tk.BOTH, expand=True)
    _set_splash_status(splash, splash_status, "Ready.")
    try:
        splash.destroy()
    except Exception:
        pass
    root.deiconify()
    root.mainloop()
