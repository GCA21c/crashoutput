import tkinter as tk
from pathlib import Path

from app.ui.styles import MUTED_FG, PAGE_BG


class VideoSlotViewer(tk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, bg="#111827", bd=1, relief=tk.SOLID)
        self.title = str(title)
        self._photo = None
        self._source_photo = None
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pulse_zoom_scale = 1.0
        self.pulse_zoom_center_ms = None
        self.overlay_channels = []
        self.overlay_start_ms = 0.0
        self.overlay_end_ms = 1.0
        self.overlay_cursor_ms = 0.0
        self.pulse_view_mode = 1
        self.pulse_background_enabled = True
        self.pulse_background_theme = "dark"
        self._pulse_bg_textures = {}
        self._pulse_bg_sized_images = {}
        self._pulse_sample_cache = {}
        self._pulse_box = None
        self._zoom_callback = None
        self._drag_mode = None
        self._drag_last_x = 0
        self._drag_last_y = 0
        self._canvas_bg_id = None
        self._canvas_image_id = None
        self._placeholder_ids = []
        self._pulse_static_signature = None
        self.header = tk.Label(self, text=self.title, bg="#111827", fg="#e5e7eb", anchor="w", padx=10, pady=5)
        self.header.pack(side=tk.TOP, fill=tk.X)
        self.canvas = tk.Canvas(
            self,
            bg="#0b1120",
            highlightthickness=0,
            bd=0,
            width=640,
            height=360,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _event: self._redraw())
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind("<Button-5>", self._on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)
        self._placeholder_text = f"{self.title}\nNo video loaded"

    def show_placeholder(self, text=None):
        self._photo = None
        self._source_photo = None
        self._placeholder_text = str(text or f"{self.title}\nNo video loaded")
        self._redraw()

    def show_frame(self, photo_image):
        self._source_photo = photo_image
        self._photo = photo_image
        if photo_image is None:
            self.show_placeholder()
            return
        self._redraw()

    def set_title_suffix(self, suffix=None):
        suffix_text = str(suffix or "").strip()
        label = self.title if not suffix_text else f"{self.title} - {suffix_text}"
        self.header.configure(text=label)

    def set_pulse_overlay(self, channels, start_ms, end_ms, cursor_ms, zoom_scale=None, zoom_center_ms=None):
        self.overlay_channels = [dict(item) for item in list(channels or [])[:3]]
        self.overlay_start_ms = float(start_ms or 0.0)
        self.overlay_end_ms = max(self.overlay_start_ms + 1.0, float(end_ms or 1.0))
        self.overlay_cursor_ms = float(cursor_ms or 0.0)
        if zoom_scale is not None:
            self.pulse_zoom_scale = max(1.0, float(zoom_scale or 1.0))
        if zoom_center_ms is not None:
            self.pulse_zoom_center_ms = float(zoom_center_ms)
        self._redraw()

    def set_zoom_callback(self, callback):
        self._zoom_callback = callback

    def set_pulse_view_mode(self, mode):
        raw_mode = int(mode or 1)
        next_mode = raw_mode if raw_mode in (1, 2) else 1
        if self.pulse_view_mode == next_mode:
            return
        self.pulse_view_mode = next_mode
        self._redraw()

    def set_pulse_background_enabled(self, enabled):
        next_enabled = bool(enabled)
        if self.pulse_background_enabled == next_enabled:
            return
        self.pulse_background_enabled = next_enabled
        self._pulse_static_signature = None
        self._redraw()

    def set_pulse_background_theme(self, theme):
        next_theme = str(theme or "dark").lower()
        if next_theme not in ("dark", "light"):
            next_theme = "dark"
        if self.pulse_background_theme == next_theme:
            return
        self.pulse_background_theme = next_theme
        self._pulse_static_signature = None
        self._redraw()

    def reset_zoom(self):
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pulse_zoom_scale = 1.0
        self.pulse_zoom_center_ms = None
        self._pulse_sample_cache.clear()
        self._pulse_bg_sized_images.clear()
        self._pulse_static_signature = None
        self._redraw()

    def image_size(self):
        scale = max(1.0, float(self.zoom_scale or 1.0))
        return (
            max(320, int((self.canvas.winfo_width() or 640) * scale)),
            max(240, int((self.canvas.winfo_height() or 360) * scale)),
        )

    def _redraw(self):
        canvas = self.canvas
        width = max(1, int(canvas.winfo_width()))
        height = max(1, int(canvas.winfo_height()))
        if self._photo is None:
            canvas.delete("all")
            self._canvas_bg_id = None
            self._canvas_image_id = None
            self._placeholder_ids = []
            self._pulse_static_signature = None
            self._placeholder_ids.append(canvas.create_rectangle(0, 0, width, height, fill="#0b1120", outline=""))
            self._placeholder_ids.append(canvas.create_text(
                width / 2,
                height / 2,
                text=self._placeholder_text,
                fill="#d1d5db",
                justify="center",
                anchor="center",
                font=("Arial", 12, "bold"),
            ))
            return
        if self._placeholder_ids:
            canvas.delete("all")
            self._canvas_bg_id = None
            self._canvas_image_id = None
            self._placeholder_ids = []
        if self._canvas_bg_id is None:
            self._canvas_bg_id = canvas.create_rectangle(0, 0, width, height, fill="#000000", outline="", tags=("video_bg",))
        else:
            canvas.coords(self._canvas_bg_id, 0, 0, width, height)
        self._clamp_pan(width, height)
        image_x = width / 2 + self.pan_x
        image_y = height / 2 + self.pan_y
        if self._canvas_image_id is None:
            self._canvas_image_id = canvas.create_image(image_x, image_y, image=self._photo, anchor="center", tags=("video_image",))
        else:
            canvas.coords(self._canvas_image_id, image_x, image_y)
            canvas.itemconfigure(self._canvas_image_id, image=self._photo)
        self._draw_pulse_overlay(width, height)

    def _draw_pulse_overlay(self, width, height):
        canvas = self.canvas
        if not self.overlay_channels:
            canvas.delete("pulse")
            self._pulse_static_signature = None
            self._pulse_box = None
            return
        left = 8
        right = max(left + 1, width - 8)
        bottom = max(42, height - 16)
        top = max(10, bottom - max(56, int(height * 0.22)))
        self._pulse_box = (left, top, right, bottom)
        colors = ("#ffff00", "#f97316", "#a3e635")

        def x_for_time(value):
            view_start, view_end = self._pulse_view_range()
            span = max(1.0, view_end - view_start)
            ratio = max(0.0, min((float(value) - view_start) / span, 1.0))
            return left + ratio * (right - left)

        view_start, view_end = self._pulse_view_range()
        static_signature = self._pulse_static_draw_signature(width, height, view_start, view_end)
        if static_signature == self._pulse_static_signature:
            canvas.delete("pulse_dynamic")
            self._draw_pulse_dynamic(left, right, top, bottom, colors, x_for_time)
            return

        canvas.delete("pulse")
        self._pulse_static_signature = static_signature
        if self.pulse_background_enabled:
            bg_image = self._pulse_bg_image_for_size(max(1, int(right - left)), max(1, int(bottom - top)))
            if bg_image is not None:
                canvas.create_image(left, top, image=bg_image, anchor="nw", tags=("pulse", "pulse_bg"))
            else:
                canvas.create_rectangle(left, top, right, bottom, fill="#020617", outline="", tags=("pulse", "pulse_bg"))
            canvas.create_rectangle(left, top, right, bottom, fill="", outline="#38bdf8", width=1, tags=("pulse", "pulse_bg"))
        else:
            canvas.create_line(left, bottom, right, bottom, fill="#38bdf8", width=1, tags=("pulse", "pulse_bg"))
        channel_draw_cache = []
        for channel_index, item in enumerate(self.overlay_channels):
            pairs = self._sample_pulse_pairs(item, view_start, view_end)
            if len(pairs) <= 1:
                channel_draw_cache.append(([], None, None, None))
                continue
            values = [v for _t, v in pairs]
            v_min = min(values)
            v_max = max(values)
            v_span = max(1e-9, v_max - v_min)
            draw_pairs = pairs
            if self.pulse_view_mode == 2:
                draw_pairs = [(t, v) for t, v in pairs if t <= self.overlay_cursor_ms]
            points = []
            for t, v in draw_pairs:
                x = x_for_time(t)
                y_ratio = (v - v_min) / v_span
                y = bottom - 6 - y_ratio * max(1, (bottom - top - 12))
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=colors[channel_index % len(colors)], width=1.40, smooth=True, tags=("pulse", "pulse_curve", "pulse_fg"))
            channel_draw_cache.append((pairs, v_min, v_span, colors[channel_index % len(colors)]))

        for channel_index, item in enumerate(self.overlay_channels):
            try:
                peak_time = float(item.get("peak_time_ms"))
            except (TypeError, ValueError):
                continue
            if not (view_start <= peak_time <= view_end):
                continue
            if self.pulse_view_mode == 2 and peak_time > self.overlay_cursor_ms:
                continue
            peak_x = x_for_time(peak_time)
            if self.pulse_view_mode == 2:
                try:
                    peak_value = float(item.get("peak_value"))
                except (TypeError, ValueError):
                    continue
                if channel_index >= len(channel_draw_cache):
                    continue
                _pairs, v_min, v_span, color = channel_draw_cache[channel_index]
                if v_min is None or v_span is None:
                    continue
                y_ratio = (peak_value - v_min) / max(1e-9, v_span)
                peak_y = bottom - 6 - y_ratio * max(1, (bottom - top - 12))
                canvas.create_oval(peak_x - 3, peak_y - 3, peak_x + 3, peak_y + 3, fill=color, outline="", tags=("pulse", "pulse_peak", "pulse_fg"))
            else:
                canvas.create_line(
                    peak_x,
                    top + 2,
                    peak_x,
                    bottom - 2,
                    fill=colors[channel_index % len(colors)],
                    width=1.2,
                    tags=("pulse", "pulse_peak", "pulse_fg"),
                )

        t0_x = x_for_time(0.0)
        if left <= t0_x <= right:
            dash_top = top + 2
            dash_bottom = bottom - 2
            canvas.create_line(t0_x, dash_top, t0_x, dash_bottom, fill="#ef4444", width=1.4, dash=(4, 3), tags=("pulse", "pulse_fg"))

        self._draw_pulse_dynamic(left, right, top, bottom, colors, x_for_time)

    def _draw_pulse_dynamic(self, left, right, top, bottom, colors, x_for_time):
        canvas = self.canvas
        time_text = f"Time: {self.overlay_cursor_ms:.0f}ms"
        if self.pulse_background_enabled:
            time_box_right = left + 88
            self._draw_textured_box(left + 4, bottom - 23, time_box_right, bottom - 4, outline=self._background_box_outline())
            time_fill = "#f8fafc"
        else:
            time_fill = "#e5e7eb"
        canvas.create_text(
            left + 8,
            bottom - 8,
            text=time_text,
            anchor="sw",
            fill=time_fill,
            font=("Arial", 8, "bold"),
            tags=("pulse", "pulse_dynamic", "pulse_fg", "pulse_time_text"),
        )

        cursor_x = x_for_time(self.overlay_cursor_ms)
        if self.pulse_view_mode == 1:
            canvas.create_line(
                cursor_x,
                top - 5,
                cursor_x,
                bottom + 5,
                fill="#00ff00",
                width=1,
                tags=("pulse", "pulse_dynamic", "pulse_fg"),
            )
        self._draw_overlay_legend(left, right, top, colors)
        canvas.tag_raise("pulse_fg")
        canvas.tag_raise("pulse_time_text")
        canvas.tag_raise("pulse_legend_text")

    def _pulse_static_draw_signature(self, width, height, view_start, view_end):
        channel_signature = []
        for item in self.overlay_channels:
            time_source = item.get("time_ms")
            signal_source = item.get("values")
            channel_signature.append((
                id(time_source),
                id(signal_source),
                len(time_source) if time_source is not None else 0,
                len(signal_source) if signal_source is not None else 0,
                item.get("peak_time_ms"),
                item.get("peak_value"),
            ))
        return (
            int(width),
            int(height),
            int(self.pulse_view_mode),
            round(float(self.overlay_start_ms), 3),
            round(float(self.overlay_end_ms), 3),
            round(float(view_start), 3),
            round(float(view_end), 3),
            round(float(self.pulse_zoom_scale or 1.0), 3),
            round(float(self.overlay_cursor_ms), 3) if self.pulse_view_mode == 2 else None,
            bool(self.pulse_background_enabled),
            tuple(channel_signature),
        )

    def _load_pulse_bg_texture(self):
        theme = str(self.pulse_background_theme or "dark").lower()
        if theme not in ("dark", "light"):
            theme = "dark"
        cached = self._pulse_bg_textures.get(theme)
        if cached is not None:
            return cached if cached is not False else None
        filename = "pulse_overlay_bg_light.png" if theme == "light" else "pulse_overlay_bg.png"
        texture_path = Path(__file__).resolve().parents[3] / "resources" / "video" / filename
        try:
            self._pulse_bg_textures[theme] = tk.PhotoImage(file=str(texture_path))
        except Exception:
            self._pulse_bg_textures[theme] = False
        cached = self._pulse_bg_textures.get(theme)
        return cached if cached is not False else None

    def _pulse_bg_image_for_size(self, width, height):
        source = self._load_pulse_bg_texture()
        if source is None:
            return None
        width = max(1, int(width))
        height = max(1, int(height))
        key = (str(self.pulse_background_theme or "dark"), width, height)
        cached = self._pulse_bg_sized_images.get(key)
        if cached is not None:
            return cached
        try:
            image = tk.PhotoImage(width=width, height=height)
            source_width = max(1, int(source.width()))
            source_height = max(1, int(source.height()))
            for y in range(0, height, source_height):
                copy_h = min(source_height, height - y)
                for x in range(0, width, source_width):
                    copy_w = min(source_width, width - x)
                    image.tk.call(
                        image,
                        "copy",
                        source,
                        "-from",
                        0,
                        0,
                        copy_w,
                        copy_h,
                        "-to",
                        x,
                        y,
                    )
        except Exception:
            return None
        if len(self._pulse_bg_sized_images) > 8:
            self._pulse_bg_sized_images.clear()
        self._pulse_bg_sized_images[key] = image
        return image

    def _draw_textured_box(self, left, top, right, bottom, outline="#334155", extra_tags=()):
        canvas = self.canvas
        width = max(1, int(right - left))
        height = max(1, int(bottom - top))
        tags = ("pulse", "pulse_dynamic", "pulse_fg", *tuple(extra_tags or ()))
        bg_image = self._pulse_bg_image_for_size(width, height)
        if bg_image is not None:
            canvas.create_image(left, top, image=bg_image, anchor="nw", tags=tags)
            canvas.create_rectangle(left, top, right, bottom, fill="", outline=outline, tags=tags)
            return
        canvas.create_rectangle(left, top, right, bottom, fill="#020617", outline=outline, tags=tags)

    def _background_box_outline(self):
        return "#9ca3af" if str(self.pulse_background_theme or "dark").lower() == "light" else "#334155"

    def _sample_pulse_pairs(self, item, view_start, view_end):
        time_source = item.get("time_ms")
        signal_source = item.get("values")
        if time_source is None or signal_source is None:
            return []
        n = min(len(time_source), len(signal_source))
        if n <= 1:
            return []
        key = (
            id(time_source),
            id(signal_source),
            n,
            round(float(view_start), 3),
            round(float(view_end), 3),
        )
        cached = self._pulse_sample_cache.get(key)
        if cached is not None:
            return cached
        step = max(1, n // 900)
        pairs = []
        for idx in range(0, n, step):
            try:
                t = float(time_source[idx])
                v = float(signal_source[idx])
            except (TypeError, ValueError, IndexError):
                continue
            if view_start <= t <= view_end:
                pairs.append((t, v))
        if len(self._pulse_sample_cache) > 48:
            self._pulse_sample_cache.clear()
        self._pulse_sample_cache[key] = pairs
        return pairs

    def _pulse_view_range(self):
        total_start = self.overlay_start_ms
        total_end = self.overlay_end_ms
        total_span = max(1.0, total_end - total_start)
        scale = max(1.0, float(self.pulse_zoom_scale or 1.0))
        view_span = max(1.0, total_span / scale)
        center = self.pulse_zoom_center_ms
        if center is None:
            center = self.overlay_cursor_ms
        center = max(total_start, min(float(center), total_end))
        start = center - view_span / 2.0
        end = center + view_span / 2.0
        if start < total_start:
            end += total_start - start
            start = total_start
        if end > total_end:
            start -= end - total_end
            end = total_end
        start = max(total_start, start)
        end = min(total_end, max(start + 1.0, end))
        return start, end

    def _draw_overlay_legend(self, left, right, top, colors):
        if not self.overlay_channels:
            return
        canvas = self.canvas
        legend_items = [self._legend_parts(item) for item in self.overlay_channels]
        overlay_width = max(1, right - left)
        name_width = max(90, max(len(name) for name, _value in legend_items) * 7)
        value_width = max(74, max(len(value) for _name, value in legend_items) * 7)
        legend_width = min(max(150, name_width + value_width + 28), max(150, overlay_width - 12))
        line_height = 18
        legend_height = 10 + line_height * len(legend_items)
        legend_left = max(left + 6, right - legend_width - 6)
        legend_top = top + 6
        value_x = legend_left + legend_width - 9
        if self.pulse_background_enabled:
            self._draw_textured_box(
                legend_left,
                legend_top,
                legend_left + legend_width,
                legend_top + legend_height,
                outline=self._background_box_outline(),
                extra_tags=("pulse_legend_bg",),
            )
        for index, (name, value) in enumerate(legend_items):
            y = legend_top + 9 + index * line_height
            color = colors[index % len(colors)]
            canvas.create_text(
                legend_left + 9,
                y,
                text=name,
                anchor="w",
                fill=color,
                font=("Arial", 8, "bold"),
                tags=("pulse", "pulse_dynamic", "pulse_fg", "pulse_legend_text"),
            )
            canvas.create_text(
                value_x,
                y,
                text=value,
                anchor="e",
                fill=color,
                font=("Arial", 8, "bold"),
                tags=("pulse", "pulse_dynamic", "pulse_fg", "pulse_legend_text"),
            )
        canvas.tag_raise("pulse_legend_text")

    def _legend_parts(self, item):
        item = dict(item or {})
        label = str(item.get("isocode") or item.get("name") or "-")
        value = item.get("current_value")
        unit = str(item.get("unit") or "").strip()
        try:
            value_text = f"{float(value):.4f}"
        except (TypeError, ValueError):
            value_text = "-"
        return label, f"{value_text} [{unit or '-'}]"

    def _on_mouse_wheel(self, event):
        direction = 1
        if getattr(event, "num", None) == 5 or getattr(event, "delta", 0) < 0:
            direction = -1
        pulse_hit = self._is_inside_pulse_box(event.x, event.y)
        if pulse_hit:
            self._zoom_pulse(direction, event.x)
        else:
            self._zoom_video(direction)
        return "break"

    def _is_inside_pulse_box(self, x, y):
        if self._pulse_box is None:
            return False
        left, top, right, bottom = self._pulse_box
        return left <= x <= right and top <= y <= bottom

    def _zoom_video(self, direction):
        factor = 1.12 if direction > 0 else 1.0 / 1.12
        self.zoom_scale = max(1.0, min(6.0, self.zoom_scale * factor))
        if self.zoom_scale <= 1.0:
            self.pan_x = 0.0
            self.pan_y = 0.0
        if callable(self._zoom_callback):
            self._zoom_callback(self.pulse_zoom_scale, self.pulse_zoom_center_ms)
        self._redraw()

    def _zoom_pulse(self, direction, x):
        factor = 1.2 if direction > 0 else 1.0 / 1.2
        self.pulse_zoom_scale = max(1.0, min(50.0, self.pulse_zoom_scale * factor))
        if self._pulse_box is not None:
            left, _top, right, _bottom = self._pulse_box
            ratio = max(0.0, min((float(x) - left) / max(1.0, right - left), 1.0))
            view_start, view_end = self._pulse_view_range()
            self.pulse_zoom_center_ms = view_start + ratio * (view_end - view_start)
        if callable(self._zoom_callback):
            self._zoom_callback(self.pulse_zoom_scale, self.pulse_zoom_center_ms)
        self._redraw()

    def _on_drag_start(self, event):
        self._drag_last_x = int(event.x)
        self._drag_last_y = int(event.y)
        self._drag_mode = "pulse" if self._is_inside_pulse_box(event.x, event.y) else "video"
        return "break"

    def _on_drag_move(self, event):
        dx = int(event.x) - int(self._drag_last_x)
        dy = int(event.y) - int(self._drag_last_y)
        self._drag_last_x = int(event.x)
        self._drag_last_y = int(event.y)
        if self._drag_mode == "pulse":
            self._pan_pulse(dx)
        elif self._drag_mode == "video":
            self._pan_video(dx, dy)
        return "break"

    def _on_drag_end(self, _event):
        self._drag_mode = None
        return "break"

    def _pan_video(self, dx, dy):
        if self.zoom_scale <= 1.0:
            return
        self.pan_x += float(dx)
        self.pan_y += float(dy)
        self._redraw()

    def _pan_pulse(self, dx):
        if self.pulse_zoom_scale <= 1.0 or self._pulse_box is None:
            return
        left, _top, right, _bottom = self._pulse_box
        box_width = max(1.0, float(right - left))
        view_start, view_end = self._pulse_view_range()
        view_span = max(1.0, view_end - view_start)
        shift_ms = -(float(dx) / box_width) * view_span
        center = self.pulse_zoom_center_ms
        if center is None:
            center = (view_start + view_end) / 2.0
        total_start = self.overlay_start_ms
        total_end = self.overlay_end_ms
        half_span = view_span / 2.0
        center = max(total_start + half_span, min(float(center) + shift_ms, total_end - half_span))
        self.pulse_zoom_center_ms = center
        if callable(self._zoom_callback):
            self._zoom_callback(self.pulse_zoom_scale, self.pulse_zoom_center_ms)
        self._redraw()

    def _clamp_pan(self, width, height):
        if self._photo is None or self.zoom_scale <= 1.0:
            self.pan_x = 0.0
            self.pan_y = 0.0
            return
        image_width = max(1, int(self._photo.width()))
        image_height = max(1, int(self._photo.height()))
        max_x = max(0.0, (image_width - width) / 2.0)
        max_y = max(0.0, (image_height - height) / 2.0)
        self.pan_x = max(-max_x, min(float(self.pan_x), max_x))
        self.pan_y = max(-max_y, min(float(self.pan_y), max_y))


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
        self._cursor_item_ids = []
        self._track_geometry = None
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
        self.cursor_ms = self._snap_time_ms(cursor_ms)
        self.keyframes = list(keyframes or [])
        self._draw()

    def _draw(self):
        canvas = self.canvas
        canvas.delete("all")
        self._cursor_item_ids = []
        width = max(1, int(canvas.winfo_width()))
        height = max(1, int(canvas.winfo_height()))
        canvas.create_rectangle(0, 0, width, height, fill="#0f172a", outline="")
        left = 22
        right = width - 22
        track_top = 14
        track_bottom = 26
        track_mid = (track_top + track_bottom) / 2
        self._track_geometry = (left, right, track_top, track_bottom, track_mid, height)
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

        self._draw_cursor()

    def _draw_cursor(self):
        canvas = self.canvas
        for item_id in self._cursor_item_ids:
            try:
                canvas.delete(item_id)
            except Exception:
                pass
        self._cursor_item_ids = []
        if self._track_geometry is None:
            return
        left, right, track_top, track_bottom, track_mid, height = self._track_geometry
        cursor_x = self._x_for_time(self.cursor_ms, left, right)
        self._cursor_item_ids.append(canvas.create_rectangle(left, track_top, cursor_x, track_bottom, fill="#2563eb", outline=""))
        self._cursor_item_ids.append(canvas.create_line(cursor_x, 6, cursor_x, height - 6, fill="#f8fafc", width=2))
        self._cursor_item_ids.append(canvas.create_oval(cursor_x - 5, track_mid - 5, cursor_x + 5, track_mid + 5, fill="#f8fafc", outline="#38bdf8", width=2))
        label = f"{int(round(self.cursor_ms))}ms"
        label_width = max(54, len(label) * 7 + 14)
        width = max(1, int(canvas.winfo_width()))
        label_left = max(4, min(cursor_x + 8, width - label_width - 4))
        self._cursor_item_ids.append(canvas.create_rectangle(label_left, 3, label_left + label_width, 18, fill="#e0f2fe", outline="#38bdf8"))
        self._cursor_item_ids.append(canvas.create_text(label_left + label_width / 2, 10.5, text=label, fill="#0f172a", font=("Arial", 8, "bold")))

    def _x_for_time(self, value_ms, left, right):
        if self.duration_ms <= 0.0:
            return left
        ratio = max(0.0, min((float(value_ms) - self.start_ms) / self.duration_ms, 1.0))
        return left + ratio * (right - left)

    def _time_for_x(self, x):
        width = max(1, int(self.canvas.winfo_width()))
        left = 18
        right = width - 18
        if right <= left or self.duration_ms <= 0.0:
            return self._snap_time_ms(self.start_ms)
        ratio = max(0.0, min((float(x) - left) / float(right - left), 1.0))
        return self._snap_time_ms(self.start_ms + ratio * self.duration_ms)

    def _snap_time_ms(self, value_ms):
        value = int(round(float(value_ms or 0.0)))
        start = int(round(float(self.start_ms or 0.0)))
        end = int(round(float(self.end_ms or start)))
        if end < start:
            end = start
        return float(max(start, min(value, end)))

    def _seek_event(self, event):
        value_ms = self._time_for_x(event.x)
        self.cursor_ms = value_ms
        self._draw_cursor()
        if callable(self.on_seek):
            self.on_seek(value_ms, final=False)

    def _on_press(self, event):
        self._dragging = True
        self._seek_event(event)

    def _on_drag(self, event):
        if self._dragging:
            self._seek_event(event)

    def _on_release(self, event):
        if self._dragging:
            self._dragging = False
            value_ms = self._time_for_x(event.x)
            self.cursor_ms = value_ms
            self._draw_cursor()
            if callable(self.on_seek):
                self.on_seek(value_ms, final=True)
