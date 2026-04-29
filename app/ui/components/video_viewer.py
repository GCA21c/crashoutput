import tkinter as tk

from app.ui.styles import MUTED_FG, PAGE_BG


class VideoSlotViewer(tk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, bg="#111827", bd=1, relief=tk.SOLID)
        self.title = str(title)
        self._photo = None
        self.overlay_channels = []
        self.overlay_start_ms = 0.0
        self.overlay_end_ms = 1.0
        self.overlay_cursor_ms = 0.0
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

    def set_pulse_overlay(self, channels, start_ms, end_ms, cursor_ms):
        self.overlay_channels = [dict(item) for item in list(channels or [])[:3]]
        self.overlay_start_ms = float(start_ms or 0.0)
        self.overlay_end_ms = max(self.overlay_start_ms + 1.0, float(end_ms or 1.0))
        self.overlay_cursor_ms = float(cursor_ms or 0.0)
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
        self._draw_pulse_overlay(width, height)

    def _draw_pulse_overlay(self, width, height):
        if not self.overlay_channels:
            return
        left = 18
        right = max(left + 1, width - 18)
        bottom = max(42, height - 16)
        top = max(10, bottom - max(56, int(height * 0.22)))
        canvas = self.canvas
        canvas.create_rectangle(left, top, right, bottom, fill="#020617", outline="#38bdf8", stipple="gray50")
        canvas.create_line(left, bottom, right, bottom, fill="#38bdf8", width=1)
        colors = ("#22d3ee", "#f97316", "#a3e635")

        def x_for_time(value):
            span = max(1.0, self.overlay_end_ms - self.overlay_start_ms)
            ratio = max(0.0, min((float(value) - self.overlay_start_ms) / span, 1.0))
            return left + ratio * (right - left)

        for channel_index, item in enumerate(self.overlay_channels):
            time_source = item.get("time_ms")
            signal_source = item.get("values")
            time_values = [] if time_source is None else list(time_source)
            signal_values = [] if signal_source is None else list(signal_source)
            n = min(len(time_values), len(signal_values))
            if n <= 1:
                continue
            pairs = []
            step = max(1, n // 900)
            for idx in range(0, n, step):
                t = time_values[idx]
                v = signal_values[idx]
                try:
                    t = float(t)
                    v = float(v)
                except (TypeError, ValueError):
                    continue
                if self.overlay_start_ms <= t <= self.overlay_end_ms:
                    pairs.append((t, v))
            if len(pairs) <= 1:
                continue
            values = [v for _t, v in pairs]
            v_min = min(values)
            v_max = max(values)
            v_span = max(1e-9, v_max - v_min)
            points = []
            for t, v in pairs:
                x = x_for_time(t)
                y_ratio = (v - v_min) / v_span
                y = bottom - 6 - y_ratio * max(1, (bottom - top - 12))
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=colors[channel_index % len(colors)], width=2.2, smooth=True)

        cursor_x = x_for_time(self.overlay_cursor_ms)
        canvas.create_line(cursor_x, top - 5, cursor_x, bottom + 5, fill="#f8fafc", width=2)


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
        canvas.create_rectangle(0, 0, width, height, fill="#0f172a", outline="")
        left = 22
        right = width - 22
        track_top = 14
        track_bottom = 26
        track_mid = (track_top + track_bottom) / 2
        canvas.create_rectangle(left, track_top, right, track_bottom, fill="#1e293b", outline="#334155")
        canvas.create_line(left, track_mid, right, track_mid, fill="#64748b", width=1)
        for index in range(11):
            x = left + (right - left) * (index / 10.0)
            tick_height = 8 if index in (0, 5, 10) else 5
            canvas.create_line(x, track_bottom, x, track_bottom + tick_height, fill="#64748b")
        canvas.create_text(left, height - 6, text=f"{self.start_ms:.0f}ms", anchor="sw", fill="#cbd5e1", font=("Arial", 8))
        canvas.create_text(right, height - 6, text=f"{self.end_ms:.0f}ms", anchor="se", fill="#cbd5e1", font=("Arial", 8))

        def x_for_time(value_ms):
            if self.duration_ms <= 0.0:
                return left
            ratio = max(0.0, min((float(value_ms) - self.start_ms) / self.duration_ms, 1.0))
            return left + ratio * (right - left)

        for marker in self.keyframes:
            marker_ms = float(dict(marker or {}).get("time_ms") or 0.0)
            x = x_for_time(marker_ms)
            canvas.create_polygon(
                x,
                track_top - 8,
                x - 6,
                track_top + 1,
                x,
                track_top + 10,
                x + 6,
                track_top + 1,
                fill="#f59e0b",
                outline="#fef3c7",
            )

        cursor_x = x_for_time(self.cursor_ms)
        canvas.create_rectangle(left, track_top, cursor_x, track_bottom, fill="#2563eb", outline="")
        canvas.create_line(cursor_x, 6, cursor_x, height - 6, fill="#f8fafc", width=2)
        canvas.create_oval(cursor_x - 5, track_mid - 5, cursor_x + 5, track_mid + 5, fill="#f8fafc", outline="#38bdf8", width=2)
        label = f"{self.cursor_ms:.1f}ms"
        label_width = max(54, len(label) * 7 + 14)
        label_left = max(4, min(cursor_x + 8, width - label_width - 4))
        canvas.create_rectangle(label_left, 3, label_left + label_width, 18, fill="#e0f2fe", outline="#38bdf8")
        canvas.create_text(label_left + label_width / 2, 10.5, text=label, fill="#0f172a", font=("Arial", 8, "bold"))

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
