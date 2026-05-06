# Video pulse texture PyInstaller rendering

## What changed
- Video Analysis pulse background texture now supports a pre-composited rendering path.
- When Pillow is available, the pulse box, time box, and legend box texture are blended into the displayed video frame before Tk draws the image.
- Pulse curves, peak lines, cursor, T0 line, time text, and legend text remain canvas items above the video image.
- The old Tk `PhotoImage` texture-on-canvas path remains as a fallback.

## Why
- PyInstaller/Tk builds can fail to preserve PNG alpha when a semi-transparent image is placed directly on a Tk canvas.
- Pre-compositing alpha into the video frame avoids relying on Tk canvas image alpha behavior.

## Risk
- The exe build still needs the `resources` directory included through PyInstaller `--add-data` or spec `datas`.
- If Pillow is not bundled, the app falls back to the previous Tk texture path and may show the same alpha limitation.
