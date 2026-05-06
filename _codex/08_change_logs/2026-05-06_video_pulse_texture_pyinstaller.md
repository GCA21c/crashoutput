# Video pulse texture PyInstaller path

## What changed
- `app/ui/components/video_viewer.py` now resolves video pulse texture resources through PyInstaller `_MEIPASS` when running from a bundled executable.
- Pulse background textures are rendered through Pillow `ImageTk.PhotoImage` first, preserving RGBA alpha more reliably than Tk `PhotoImage` PNG loading in bundled Tcl/Tk environments.
- Tk `PhotoImage` remains as a fallback when Pillow is unavailable.

## Why
- In PyInstaller builds, `resources/video/pulse_overlay_bg*.png` may not be found through the development-time `__file__` relative path.
- Some bundled Tk runtimes render PNG alpha inconsistently, which can make the Video Analysis pulse texture appear opaque.

## Risk
- The exe build must still include the `resources` directory via PyInstaller `--add-data` or spec `datas`.
- Windows exe alpha rendering should be checked directly because Tk/Pillow behavior depends on the bundled runtime.
