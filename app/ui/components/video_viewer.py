import tkinter as tk

from app.ui.styles import MUTED_FG, PAGE_BG, TEXT_FG


class VideoSlotViewer(tk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, bg="#111827", bd=1, relief=tk.SOLID)
        self.title = str(title)
        self._photo = None
        self.header = tk.Label(self, text=self.title, bg="#111827", fg="#e5e7eb", anchor="w", padx=10, pady=5)
        self.header.pack(side=tk.TOP, fill=tk.X)
        self.canvas = tk.Canvas(
            self,
            bg="#0b1120",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _event: self._redraw())
        self._placeholder_text = f"{self.title}\nNo video loaded"

    def show_placeholder(self, text=None):
        self._photo = None
        self._placeholder_text = str(text or f"{self.title}\nNo video loaded")
        self._redraw()

    def show_frame(self, photo_image):
        self._photo = photo_image
        if photo_image is None:
            self.show_placeholder()
            return
        self._redraw()

    def image_size(self):
        return (
            max(320, int(self.canvas.winfo_width() or 640)),
            max(240, int(self.canvas.winfo_height() or 360)),
        )

    def _redraw(self):
        canvas = self.canvas
        canvas.delete("all")
        width = max(1, int(canvas.winfo_width()))
        height = max(1, int(canvas.winfo_height()))
        if self._photo is None:
            canvas.create_rectangle(0, 0, width, height, fill="#0b1120", outline="")
            canvas.create_text(
                width / 2,
                height / 2,
                text=self._placeholder_text,
                fill="#d1d5db",
                justify="center",
                anchor="center",
                font=("Arial", 12, "bold"),
            )
            return
        canvas.create_rectangle(0, 0, width, height, fill="#000000", outline="")
        canvas.create_image(width / 2, height / 2, image=self._photo, anchor="center")


class KeyframeTimeline(tk.Frame):
    def __init__(self, parent, on_seek=None):
        super().__init__(parent, bg=PAGE_BG)
        self.duration_ms = 0.0
        self.start_ms = 0.0
        self.end_ms = 0.0
        self.cursor_ms = 0.0
        self.keyframes = []
        self.on_seek = on_seek
        self._dragging = False
        self.canvas = tk.Canvas(self, height=42, bg="#f8fafc", highlightthickness=1, highlightbackground="#cbd5e1")
        self.canvas.pack(fill=tk.X, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def set_state(self, duration_ms, cursor_ms, keyframes=None, start_ms=0.0, end_ms=None):
        self.start_ms = float(start_ms or 0.0)
        if end_ms is None:
            self.end_ms = max(self.start_ms, float(duration_ms or 0.0))
        else:
            self.end_ms = max(self.start_ms, float(end_ms or 0.0))
        self.duration_ms = max(0.0, self.end_ms - self.start_ms)
        self.cursor_ms = float(cursor_ms or 0.0)
        self.keyframes = list(keyframes or [])
        self._draw()

    def _draw(self):
        canvas = self.canvas
        canvas.delete("all")
        width = max(1, int(canvas.winfo_width()))
        height = max(1, int(canvas.winfo_height()))
        y = height // 2
        left = 18
        right = width - 18
        canvas.create_line(left, y, right, y, fill="#94a3b8", width=8, capstyle=tk.ROUND)
        canvas.create_text(left, height - 8, text=f"{self.start_ms:.0f}ms", anchor="sw", fill=MUTED_FG, font=("Arial", 8))
        canvas.create_text(right, height - 8, text=f"{self.end_ms:.0f}ms", anchor="se", fill=MUTED_FG, font=("Arial", 8))

        def x_for_time(value_ms):
            if self.duration_ms <= 0.0:
                return left
            ratio = max(0.0, min((float(value_ms) - self.start_ms) / self.duration_ms, 1.0))
            return left + ratio * (right - left)

        for marker in self.keyframes:
            marker_ms = float(dict(marker or {}).get("time_ms") or 0.0)
            x = x_for_time(marker_ms)
            canvas.create_polygon(x, y - 11, x - 5, y - 1, x + 5, y - 1, fill="#f59e0b", outline="")

        cursor_x = x_for_time(self.cursor_ms)
        canvas.create_line(cursor_x, 6, cursor_x, height - 6, fill="#dc2626", width=2)
        canvas.create_text(cursor_x + 4, 6, text=f"{self.cursor_ms:.1f}ms", anchor="nw", fill=TEXT_FG, font=("Arial", 8, "bold"))

    def _time_for_x(self, x):
        width = max(1, int(self.canvas.winfo_width()))
        left = 18
        right = width - 18
        if right <= left or self.duration_ms <= 0.0:
            return self.start_ms
        ratio = max(0.0, min((float(x) - left) / float(right - left), 1.0))
        return self.start_ms + ratio * self.duration_ms

    def _seek_event(self, event):
        value_ms = self._time_for_x(event.x)
        self.cursor_ms = value_ms
        self._draw()
        if callable(self.on_seek):
            self.on_seek(value_ms)

    def _on_press(self, event):
        self._dragging = True
        self._seek_event(event)

    def _on_drag(self, event):
        if self._dragging:
            self._seek_event(event)

    def _on_release(self, event):
        if self._dragging:
            self._dragging = False
            self._seek_event(event)
