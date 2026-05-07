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
    splash.configure(bg="#ffffff")
    splash.attributes("-topmost", True)
    width = 520
    height = 245
    screen_w = splash.winfo_screenwidth()
    screen_h = splash.winfo_screenheight()
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")
    panel = tk.Frame(splash, bg="#ffffff", padx=34, pady=28)
    panel.pack(fill=tk.BOTH, expand=True)
    tk.Label(
        panel,
        text="CRASH OUTPUT™",
        bg="#ffffff",
        fg="#111827",
        font=("Segoe UI", 25, "bold"),
    ).pack(anchor="w")
    tk.Label(
        panel,
        text="Crash Data Analysis System",
        bg="#ffffff",
        fg="#1f2937",
        font=("Segoe UI", 14),
    ).pack(anchor="w", pady=(8, 0))
    tk.Label(
        panel,
        text="Powered by GCA21c with Codex",
        bg="#ffffff",
        fg="#4b5563",
        font=("Segoe UI", 11),
    ).pack(anchor="w", pady=(18, 0))
    tk.Label(
        panel,
        text="Ver 1.0 | Build260296",
        bg="#ffffff",
        fg="#111827",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w", pady=(8, 0))
    status_var = tk.StringVar(value="Initializing...")
    tk.Label(
        panel,
        textvariable=status_var,
        bg="#ffffff",
        fg="#6b7280",
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(20, 0))
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
