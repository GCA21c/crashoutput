import numpy as np
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app.ui.styles import PAGE_BG


class PulseTimeline(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=PAGE_BG)
        self.channels = []
        self.cursor_ms = 0.0
        self.start_ms = 0.0
        self.end_ms = 0.0
        self._cursor_line = None
        self.figure = Figure(figsize=(10, 2.2), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw()

    def set_channels(self, channels):
        self.channels = [dict(item) for item in list(channels or [])]
        self._draw()

    def set_cursor(self, cursor_ms, duration_ms=None, start_ms=None, end_ms=None):
        self.cursor_ms = float(cursor_ms or 0.0)
        if start_ms is not None:
            self.start_ms = float(start_ms or 0.0)
        if end_ms is not None:
            self.end_ms = float(end_ms or 0.0)
        elif duration_ms is not None:
            self.start_ms = min(0.0, self.start_ms)
            self.end_ms = max(self.start_ms, float(duration_ms or 0.0))
        self._update_cursor()

    def _draw(self):
        self.ax.clear()
        self._cursor_line = None
        if not self.channels:
            self.ax.text(0.5, 0.5, "Add channel to display pulse data", ha="center", va="center", transform=self.ax.transAxes)
            self.ax.set_xlabel("Time (ms)")
            self.ax.set_yticks([])
            self.ax.grid(True, axis="x", alpha=0.25)
            self._cursor_line = self.ax.axvline(self.cursor_ms, color="#dc2626", linewidth=1.4)
            self.figure.tight_layout()
            self.canvas.draw_idle()
            return

        for item in self.channels[:3]:
            name = str(item.get("name") or "-")
            time_values = item.get("time_ms")
            signal_values = item.get("values")
            t = np.asarray([] if time_values is None else time_values, dtype=float)
            v = np.asarray([] if signal_values is None else signal_values, dtype=float)
            n = min(len(t), len(v))
            if n <= 0:
                continue
            t = t[:n]
            v = v[:n]
            mask = np.isfinite(t) & np.isfinite(v)
            if not np.any(mask):
                continue
            t = t[mask]
            v = v[mask]
            if len(t) > 4000:
                step = int(np.ceil(len(t) / 4000.0))
                t = t[::step]
                v = v[::step]
            self.ax.plot(t, v, linewidth=1.0, label=name)

        self._cursor_line = self.ax.axvline(self.cursor_ms, color="#dc2626", linewidth=1.4, label="Current frame")
        if self.end_ms > self.start_ms:
            left = min(self.start_ms, self.cursor_ms)
            right = max(self.end_ms, self.cursor_ms)
            if right > left:
                self.ax.set_xlim(left, right)
        self.ax.set_xlabel("Time (ms)")
        self.ax.grid(True, alpha=0.25)
        self.ax.legend(loc="upper right", fontsize=8)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _update_cursor(self):
        if self._cursor_line is None:
            self._draw()
            return
        self._cursor_line.set_xdata([self.cursor_ms, self.cursor_ms])
        self.canvas.draw_idle()
