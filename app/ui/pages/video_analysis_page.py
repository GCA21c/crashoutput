import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import numpy as np

from app.core.video.frame_cache import FrameCache
from app.core.video.frame_prefetcher import FramePrefetchManager
from app.core.video.video_sync import VideoAnalysisState
from app.ui.components.pulse_timeline import PulseTimeline
from app.ui.components.video_viewer import KeyframeTimeline, VideoSlotViewer
from app.ui.styles import HEADER_FONT, MUTED_FG, PAGE_BG, TEXT_FG


PAGE_TITLE = "VIDEO ANALYSIS"
MAX_VIDEOS = 2
MAX_CHANNELS = 3
SEGMENT_BACKWARD_MS = 50
SEGMENT_FORWARD_MS = 200
SEGMENT_CACHE_MAX_ITEMS = 560
PLAYBACK_BUFFER_AHEAD = 12
PLAYBACK_BUFFER_REFILL_BATCH = 3


def _load_cv2():
    try:
        import cv2  # type: ignore
    except ImportError:
        return None
    return cv2


def _load_pillow():
    try:
        from PIL import Image, ImageTk  # type: ignore
    except ImportError:
        return None, None
    return Image, ImageTk


class VideoAnalysisPage(tk.Frame):
    def __init__(self, parent, workbench):
        super().__init__(parent, bg=PAGE_BG)
        self.workbench = workbench
        self.state = VideoAnalysisState()
        self.captures = [None] * MAX_VIDEOS
        self.video_infos = [None] * MAX_VIDEOS
        self.channel_data = []
        self.channel_select_var = tk.StringVar()
        self.pulse_view_mode_var = tk.IntVar(value=1)
        self.pulse_background_var = tk.BooleanVar(value=True)
        self.pulse_background_theme_var = tk.StringVar(value="dark")
        self.playback_speed_var = tk.StringVar(value="x1.0")
        self._layout_refresh_after_id = None
        self._play_after_id = None
        self._refresh_after_id = None
        self._timeline_seek_after_id = None
        self._pending_timeline_seek_ms = None
        self._frame_cache = FrameCache(
            radius=SEGMENT_FORWARD_MS,
            max_items=SEGMENT_CACHE_MAX_ITEMS,
            before_radius=SEGMENT_BACKWARD_MS,
            after_radius=SEGMENT_FORWARD_MS,
        )
        self._frame_prefetcher = FramePrefetchManager(self._frame_cache, radius=8)
        self._prefetch_enabled = False
        self._pulse_base_snapshot = []
        self._photo_cache = {}
        self._capture_next_frames = [None] * MAX_VIDEOS
        self._playback_buffers = [dict() for _ in range(MAX_VIDEOS)]
        self._playback_buffer_after_id = None
        self._playback_ui_frame_counter = 0
        self._held_key = None
        self._key_hold_after_id = None
        self._key_hold_started = False
        self._key_bindings_ready = False
        self._build_ui()

    def _build_ui(self):
        outer = tk.Frame(self, bg=PAGE_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(outer, bg=PAGE_BG)
        header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header, text=PAGE_TITLE, font=HEADER_FONT, bg=PAGE_BG).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="Space: Play/Pause | Left/Right: 1 frame 이동 | Sync offset은 frame 단위이며 음수 frame/time 표시를 허용한다.",
            bg=PAGE_BG,
            fg=MUTED_FG,
            anchor="w",
        ).pack(side=tk.LEFT, padx=(12, 0))

        toolbar = tk.Frame(outer, bg=PAGE_BG)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        tk.Button(toolbar, text="Video Load", command=self.load_video, width=13).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Sync adjust", command=self.adjust_sync, width=13).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Reset", command=self.confirm_reset_session_state, width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Clear V1", command=lambda: self.clear_video(0), width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Clear V2", command=lambda: self.clear_video(1), width=10).pack(side=tk.LEFT, padx=(8, 0))
        self.channel_combo = ttk.Combobox(toolbar, textvariable=self.channel_select_var, state="readonly", width=34)
        self.channel_combo.pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Add channel", command=self.add_channel, width=13).pack(side=tk.LEFT, padx=(8, 0))

        status = tk.Frame(toolbar, bg=PAGE_BG)
        status.pack(side=tk.RIGHT)
        self.time_var = tk.StringVar(value="Time : 000ms")
        self.frame_var = tk.StringVar(value="Frame : 0000")
        tk.Label(status, textvariable=self.time_var, bg="#f8fafc", fg=TEXT_FG, bd=1, relief=tk.SOLID, width=18, padx=8).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(status, textvariable=self.frame_var, bg="#f8fafc", fg=TEXT_FG, bd=1, relief=tk.SOLID, width=18, padx=8).pack(side=tk.LEFT)

        video_box = tk.LabelFrame(outer, text="Video", bg=PAGE_BG)
        video_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.video_left = VideoSlotViewer(video_box, "VIDEO 1")
        self.video_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4), pady=8)
        self.video_right = VideoSlotViewer(video_box, "VIDEO 2")
        self.video_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)
        self.video_left.set_zoom_callback(lambda _scale=None, _center=None: self._on_viewer_zoom_changed(0))
        self.video_right.set_zoom_callback(lambda _scale=None, _center=None: self._on_viewer_zoom_changed(1))

        self.pulse_timeline = PulseTimeline(outer)

        keyframe_box = tk.LabelFrame(outer, text="Key frame", bg=PAGE_BG)
        keyframe_box.pack(fill=tk.X)
        self.keyframe_timeline = KeyframeTimeline(keyframe_box, on_seek=self._seek_timeline_ms)
        self.keyframe_timeline.pack(fill=tk.X, padx=8, pady=8)

        footer = tk.Frame(outer, bg=PAGE_BG)
        footer.pack(fill=tk.X, pady=(8, 0))
        speed_box = tk.Frame(footer, bg=PAGE_BG)
        speed_box.pack(side=tk.LEFT)
        tk.Label(speed_box, text="Speed", bg=PAGE_BG, fg=MUTED_FG).pack(side=tk.LEFT, padx=(0, 4))
        for value in ("x0.3", "x1.0", "x2.5"):
            tk.Radiobutton(
                speed_box,
                text=value,
                value=value,
                variable=self.playback_speed_var,
                command=self._on_playback_speed_changed,
                bg=PAGE_BG,
                fg=MUTED_FG,
                selectcolor=PAGE_BG,
                indicatoron=False,
                width=6,
                bd=1,
                relief=tk.RIDGE,
            ).pack(side=tk.LEFT, padx=(3, 0))

        controls = tk.Frame(footer, bg=PAGE_BG)
        controls.pack(side=tk.LEFT, expand=True)
        tk.Button(controls, text="|◀", command=self.first_frame, width=7).pack(side=tk.LEFT, padx=4)
        tk.Button(controls, text="◀◀", command=self.prev_frame, width=7).pack(side=tk.LEFT, padx=4)
        self.play_button = tk.Button(controls, text="▶", command=self.toggle_play, width=7)
        self.play_button.pack(side=tk.LEFT, padx=4)
        tk.Button(controls, text="▶▶", command=self.next_frame, width=7).pack(side=tk.LEFT, padx=4)
        tk.Button(controls, text="▶|", command=self.last_frame, width=7).pack(side=tk.LEFT, padx=4)

        pulse_view_box = tk.Frame(footer, bg=PAGE_BG)
        pulse_view_box.pack(side=tk.RIGHT)
        pulse_view_row = tk.Frame(pulse_view_box, bg=PAGE_BG)
        pulse_view_row.pack(side=tk.TOP, anchor="e")
        pulse_bg_row = tk.Frame(pulse_view_box, bg=PAGE_BG)
        pulse_bg_row.pack(side=tk.TOP, anchor="e", pady=(3, 0))
        pulse_bg_theme_row = tk.Frame(pulse_view_box, bg=PAGE_BG)
        pulse_bg_theme_row.pack(side=tk.TOP, anchor="e", pady=(3, 0))
        tk.Label(pulse_view_row, text="Pulse", bg=PAGE_BG, fg=MUTED_FG).pack(side=tk.LEFT, padx=(0, 4))
        for value, text in ((1, "View 1"), (2, "View 2")):
            tk.Radiobutton(
                pulse_view_row,
                text=text,
                value=value,
                variable=self.pulse_view_mode_var,
                command=self._apply_pulse_view_mode,
                bg=PAGE_BG,
                fg=MUTED_FG,
                selectcolor=PAGE_BG,
                indicatoron=False,
                width=7,
                bd=1,
                relief=tk.RIDGE,
            ).pack(side=tk.LEFT, padx=(3, 0))
        tk.Label(pulse_bg_row, text="BG", bg=PAGE_BG, fg=MUTED_FG).pack(side=tk.LEFT, padx=(0, 4))
        for value, text in ((True, "ON"), (False, "OFF")):
            tk.Radiobutton(
                pulse_bg_row,
                text=text,
                value=value,
                variable=self.pulse_background_var,
                command=self._apply_pulse_background,
                bg=PAGE_BG,
                fg=MUTED_FG,
                selectcolor=PAGE_BG,
                indicatoron=False,
                width=7,
                bd=1,
                relief=tk.RIDGE,
            ).pack(side=tk.LEFT, padx=(3, 0))
        tk.Label(pulse_bg_theme_row, text="Tone", bg=PAGE_BG, fg=MUTED_FG).pack(side=tk.LEFT, padx=(0, 4))
        for value, text in (("dark", "Dark"), ("light", "Light")):
            tk.Radiobutton(
                pulse_bg_theme_row,
                text=text,
                value=value,
                variable=self.pulse_background_theme_var,
                command=self._apply_pulse_background_theme,
                bg=PAGE_BG,
                fg=MUTED_FG,
                selectcolor=PAGE_BG,
                indicatoron=False,
                width=7,
                bd=1,
                relief=tk.RIDGE,
            ).pack(side=tk.LEFT, padx=(3, 0))

    def on_show(self):
        if not self._key_bindings_ready:
            root = self.winfo_toplevel()
            root.bind_all("<space>", self._on_space)
            root.bind_all("<KeyPress-Left>", self._on_left_press)
            root.bind_all("<KeyRelease-Left>", self._on_left_release)
            root.bind_all("<KeyPress-Right>", self._on_right_press)
            root.bind_all("<KeyRelease-Right>", self._on_right_release)
            self._key_bindings_ready = True
        self.focus_set()
        self._refresh_channel_options()
        self._refresh_video_layout()
        self._refresh_all()

    def load_video(self):
        cv2 = _load_cv2()
        if cv2 is None:
            messagebox.showwarning("VIDEO ANALYSIS", "OpenCV(cv2)가 필요합니다. opencv-python 설치 후 다시 시도하세요.")
            return
        free_slots = [index for index, capture in enumerate(self.captures) if capture is None]
        if not free_slots:
            messagebox.showinfo("VIDEO ANALYSIS", "동영상은 최대 2개까지 로드할 수 있습니다.")
            return
        paths = filedialog.askopenfilenames(
            parent=self,
            title="Select video file",
            filetypes=(
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv"),
                ("All files", "*.*"),
            ),
        )
        if not paths:
            return
        selected = list(paths)[:len(free_slots)]
        if len(paths) > len(free_slots):
            messagebox.showinfo("VIDEO ANALYSIS", "동영상은 최대 2개까지만 추가합니다.")

        assigned = 0
        for path in selected:
            capture = cv2.VideoCapture(str(path))
            if not capture.isOpened():
                messagebox.showwarning("VIDEO ANALYSIS", f"동영상을 열 수 없습니다.\n{path}")
                capture.release()
                continue
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0) or 1000.0
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if frame_count <= 0:
                messagebox.showwarning("VIDEO ANALYSIS", f"프레임 정보를 읽을 수 없습니다.\n{path}")
                capture.release()
                continue
            duration_ms = float(max(0, frame_count - 1))
            slot_index = free_slots[assigned]
            self.captures[slot_index] = capture
            self.video_infos[slot_index] = {"path": str(path), "fps": fps, "frame_count": frame_count, "duration_ms": duration_ms}
            self._capture_next_frames[slot_index] = None
            self._frame_prefetcher.start_slot(slot_index, str(path))
            assigned += 1

        if assigned <= 0:
            return

        self._frame_cache.clear()
        self._photo_cache.clear()
        self._reset_playback_buffers()
        self.video_left.reset_zoom()
        self.video_right.reset_zoom()
        active_infos = self._active_video_infos()
        master_fps = float(active_infos[0]["fps"])
        mismatched = [info for info in active_infos[1:] if abs(float(info["fps"]) - master_fps) > 0.01]
        if mismatched:
            messagebox.showwarning(
                "VIDEO ANALYSIS",
                "동영상 FPS가 서로 다릅니다. 초기 구현에서는 첫 번째 영상 FPS를 master로 사용합니다.",
            )
        frame_count = min(int(info["frame_count"]) for info in active_infos)
        self.state.set_video_master([info["path"] for info in active_infos], master_fps, frame_count)
        self._refresh_video_layout()
        self._refresh_all()

    def clear_video(self, index):
        if index < 0 or index >= MAX_VIDEOS or self.captures[index] is None:
            return
        self.pause()
        try:
            self.captures[index].release()
        except Exception:
            pass
        self.captures[index] = None
        self.video_infos[index] = None
        self._frame_prefetcher.stop_slot(index)
        self._frame_cache.clear_slot(index)
        self._clear_photo_cache_slot(index)
        self._capture_next_frames[index] = None
        self._clear_playback_buffer(index)
        self.video_left.reset_zoom()
        self.video_right.reset_zoom()
        active_infos = self._active_video_infos()
        if active_infos:
            master_fps = float(active_infos[0]["fps"])
            frame_count = min(int(info["frame_count"]) for info in active_infos)
            self.state.set_video_master([info["path"] for info in active_infos], master_fps, frame_count)
        else:
            self.state.reset_videos()
        self._refresh_video_layout()
        self._refresh_all()

    def add_channel(self):
        viewer = self.workbench.viewer
        if getattr(viewer, "df", None) is None or getattr(viewer, "time_column", None) is None:
            messagebox.showwarning("VIDEO ANALYSIS", "먼저 데이터를 로드하세요.")
            return
        if len(self.channel_data) >= MAX_CHANNELS:
            messagebox.showinfo("VIDEO ANALYSIS", "채널은 최대 3개까지 추가할 수 있습니다.")
            return
        columns = self._available_channel_names()
        if not columns:
            messagebox.showwarning("VIDEO ANALYSIS", "추가할 데이터 채널이 없습니다.")
            return
        selected = str(self.channel_select_var.get() or "").strip()
        if not selected:
            messagebox.showwarning("VIDEO ANALYSIS", "추가할 채널을 선택하세요.")
            return
        if selected in self.state.selected_channels:
            messagebox.showinfo("VIDEO ANALYSIS", "이미 추가된 채널입니다.")
            return
        time_s = viewer.get_numeric_column(viewer.time_column)
        values = viewer.get_numeric_column(selected)
        unit = str((getattr(viewer, "external_units", {}) or {}).get(selected) or "").strip()
        time_ms = np.asarray(time_s, dtype=float) * 1000.0
        signal_values = np.asarray(values, dtype=float)
        peak = self._channel_abs_peak(time_ms, signal_values)
        self.state.selected_channels.append(selected)
        self.channel_data.append({
            "name": selected,
            "isocode": selected,
            "unit": unit,
            "time_ms": time_ms,
            "values": signal_values,
            "peak_time_ms": peak[0],
            "peak_value": peak[1],
        })
        self._rebuild_pulse_base_snapshot()
        self.pulse_timeline.set_channels(self.channel_data)
        self._refresh_channel_options()
        self._refresh_pulse()

    def clear_channels(self):
        self.state.selected_channels.clear()
        self.channel_data.clear()
        self._rebuild_pulse_base_snapshot()
        self.pulse_timeline.set_channels([])
        self._refresh_channel_options()
        self._refresh_pulse()

    def adjust_sync(self):
        value = simpledialog.askinteger(
            "Sync adjust",
            "동영상 시작 frame offset을 입력하세요. 예: -50\n-50이면 raw frame 50을 test T0(0ms)으로 맞춥니다.",
            parent=self,
            initialvalue=int(self.state.sync_frame_offset),
        )
        if value is None:
            return
        self.state.set_sync_offset(value)
        self._schedule_refresh()

    def _seek_timeline_ms(self, value_ms, final=False):
        self.pause()
        self._pending_timeline_seek_ms = float(int(round(float(value_ms or 0.0))))
        if final:
            if self._timeline_seek_after_id is not None:
                try:
                    self.after_cancel(self._timeline_seek_after_id)
                except Exception:
                    pass
                self._timeline_seek_after_id = None
            self._apply_pending_timeline_seek()
            return
        if self._timeline_seek_after_id is None:
            self._timeline_seek_after_id = self.after(33, self._apply_pending_timeline_seek)

    def _apply_pending_timeline_seek(self):
        self._timeline_seek_after_id = None
        value_ms = self._pending_timeline_seek_ms
        self._pending_timeline_seek_ms = None
        if value_ms is None:
            return
        raw_frame = int(round(float(value_ms) - float(self.state.sync_frame_offset)))
        self.state.set_frame(raw_frame)
        self._reset_capture_positions()
        self._refresh_all()
        self._request_segment_frame_prefetch()

    def _cancel_pending_timeline_seek(self):
        if self._timeline_seek_after_id is not None:
            try:
                self.after_cancel(self._timeline_seek_after_id)
            except Exception:
                pass
            self._timeline_seek_after_id = None
        self._pending_timeline_seek_ms = None

    def _step_frame(self, delta, pause=True):
        self._cancel_pending_timeline_seek()
        if pause:
            self.pause()
        self.state.step_frame(delta)
        self._reset_capture_positions()
        self._schedule_refresh()
        self._request_segment_frame_prefetch()

    def _start_key_hold(self, key_name, delta):
        if not self._is_active_page():
            return None
        self.pause()
        first_press = self._held_key != key_name
        self._held_key = key_name
        if first_press:
            self._key_hold_started = False
            self._step_frame(delta, pause=False)
            self._schedule_key_hold(delta, initial=True)
        return "break"

    def _schedule_key_hold(self, delta, initial=False):
        if self._key_hold_after_id is not None:
            return
        delay = 220 if initial else 34
        self._key_hold_after_id = self.after(delay, lambda: self._key_hold_step(delta))

    def _key_hold_step(self, delta):
        self._key_hold_after_id = None
        if self._held_key is None or not self._is_active_page():
            return
        self._key_hold_started = True
        self._step_frame(delta * 2, pause=False)
        self._schedule_key_hold(delta, initial=False)

    def _stop_key_hold(self, key_name):
        if self._held_key == key_name:
            self._held_key = None
        if self._key_hold_after_id is not None:
            try:
                self.after_cancel(self._key_hold_after_id)
            except Exception:
                pass
            self._key_hold_after_id = None
        self._key_hold_started = False
        return "break" if self._is_active_page() else None

    def _schedule_refresh(self):
        if self._refresh_after_id is not None:
            return
        self._refresh_after_id = self.after(1, self._refresh_all_scheduled)

    def _refresh_all_scheduled(self):
        self._refresh_after_id = None
        self._refresh_all()

    def prev_frame(self):
        self._step_frame(-1)

    def next_frame(self):
        self._step_frame(1)

    def first_frame(self):
        self._cancel_pending_timeline_seek()
        self.pause()
        self.state.set_frame(0)
        self._reset_capture_positions()
        self._schedule_refresh()
        self._request_segment_frame_prefetch()

    def last_frame(self):
        self._cancel_pending_timeline_seek()
        self.pause()
        self.state.set_frame(max(0, self.state.frame_count - 1))
        self._reset_capture_positions()
        self._schedule_refresh()
        self._request_segment_frame_prefetch()

    def toggle_play(self):
        if self.state.is_playing:
            self.pause()
            self._schedule_refresh()
        else:
            self.play()

    def play(self):
        if not self._active_video_indices() or self.state.frame_count <= 0:
            return
        self._cancel_pending_timeline_seek()
        self._playback_ui_frame_counter = 0
        self._reset_playback_buffers()
        self.state.is_playing = True
        self.play_button.configure(text="❚❚")
        self._schedule_play_step()

    def pause(self):
        self.state.is_playing = False
        self.play_button.configure(text="▶")
        if self._play_after_id is not None:
            try:
                self.after_cancel(self._play_after_id)
            except Exception:
                pass
            self._play_after_id = None
        self._held_key = None
        self._playback_ui_frame_counter = 0
        self._cancel_playback_buffer_refill()

    def _schedule_play_step(self):
        if not self.state.is_playing:
            return
        playback_fps = max(1.0, float(self.state.playback_rate_fps or 30.0) * self._playback_speed_multiplier())
        delay_ms = max(1, int(round(1000.0 / playback_fps)))
        self._play_after_id = self.after(delay_ms, self._play_step)

    def _playback_speed_multiplier(self):
        value = str(self.playback_speed_var.get() or "x1.0").lower().strip()
        if value.startswith("x"):
            value = value[1:]
        try:
            return max(0.1, float(value))
        except ValueError:
            return 1.0

    def _on_playback_speed_changed(self, _event=None):
        if not self.state.is_playing:
            return
        if self._play_after_id is not None:
            try:
                self.after_cancel(self._play_after_id)
            except Exception:
                pass
            self._play_after_id = None
        self._schedule_play_step()

    def _play_step(self):
        self._play_after_id = None
        if not self.state.is_playing:
            return
        last_frame = max(0, self.state.frame_count - 1)
        if self.state.current_raw_frame >= last_frame:
            self.pause()
            self._schedule_refresh()
            return
        self.state.step_frame(1)
        self._refresh_playback_view()
        self._schedule_play_step()

    def _on_space(self, event):
        if self._is_active_page():
            self.toggle_play()
            return "break"
        return None

    def _on_left_press(self, event):
        return self._start_key_hold("left", -1)

    def _on_left_release(self, event):
        return self._stop_key_hold("left")

    def _on_right_press(self, event):
        return self._start_key_hold("right", 1)

    def _on_right_release(self, event):
        return self._stop_key_hold("right")

    def _is_active_page(self):
        return getattr(self.workbench, "current_page_key", None) == "video_analysis"

    def _available_channel_names(self):
        viewer = self.workbench.viewer
        if getattr(viewer, "df", None) is None or getattr(viewer, "time_column", None) is None:
            return []
        selected = set(self.state.selected_channels)
        return [str(col) for col in list(viewer.df.columns) if str(col) != str(viewer.time_column) and str(col) not in selected]

    def _refresh_channel_options(self):
        values = self._available_channel_names()
        self.channel_combo.configure(values=values)
        current = str(self.channel_select_var.get() or "")
        if current not in values:
            self.channel_select_var.set(values[0] if values else "")

    def _active_video_infos(self):
        return [info for info in self.video_infos if info is not None]

    def _active_video_indices(self):
        return [index for index, capture in enumerate(self.captures) if capture is not None]

    def _visible_video_viewers(self):
        active_indices = self._active_video_indices()
        if active_indices == [1]:
            return (self.video_right,)
        if active_indices == [0, 1]:
            return (self.video_left, self.video_right)
        return (self.video_left,)

    def _refresh_video_layout(self):
        self._refresh_video_titles()
        self.video_left.pack_forget()
        self.video_right.pack_forget()
        active_indices = self._active_video_indices()
        if not active_indices or active_indices == [0]:
            self.video_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
            self._schedule_post_layout_refresh()
            return
        if active_indices == [1]:
            self.video_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
            self._schedule_post_layout_refresh()
            return
        self.video_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4), pady=8)
        self.video_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)
        self._schedule_post_layout_refresh()

    def _refresh_video_titles(self):
        for index, viewer in enumerate((self.video_left, self.video_right)):
            info = self.video_infos[index]
            filename = Path(str(info.get("path", ""))).name if info else ""
            viewer.set_title_suffix(filename)

    def _schedule_post_layout_refresh(self):
        if self._layout_refresh_after_id is not None:
            try:
                self.after_cancel(self._layout_refresh_after_id)
            except Exception:
                pass
        self.update_idletasks()
        self._layout_refresh_after_id = self.after(60, self._refresh_after_layout)

    def _refresh_after_layout(self):
        self._layout_refresh_after_id = None
        self.update_idletasks()
        self._photo_cache.clear()
        self._refresh_video_frames()
        self._refresh_pulse()

    def _refresh_all(self):
        self._refresh_status()
        if self._prefetch_enabled:
            self._request_frame_prefetch()
        self._refresh_video_frames()
        self._schedule_playback_buffer_refill()
        self._refresh_pulse()
        self._refresh_keyframe()

    def _refresh_playback_view(self):
        self._playback_ui_frame_counter += 1
        self._refresh_status()
        if self._prefetch_enabled:
            self._request_frame_prefetch()
        self._refresh_video_frames()
        self._refresh_pulse()
        self._refresh_keyframe()

    def _refresh_status(self):
        self.time_var.set(f"Time : {self.state.synced_time_ms:.1f}ms")
        self.frame_var.set(f"Frame : {self.state.synced_frame:04d}")

    def _refresh_pulse(self):
        start_ms, end_ms = self._timeline_range_ms()
        self.pulse_timeline.set_cursor(self.state.synced_time_ms, start_ms=start_ms, end_ms=end_ms)
        overlay_start_ms, overlay_end_ms = self._video_time_range_ms()
        overlay_channels = self._overlay_channel_snapshot()
        for viewer in self._visible_video_viewers():
            viewer.set_pulse_view_mode(self.pulse_view_mode_var.get())
            viewer.set_pulse_background_enabled(self.pulse_background_var.get())
            viewer.set_pulse_background_theme(self.pulse_background_theme_var.get())
            viewer.set_pulse_overlay(overlay_channels, overlay_start_ms, overlay_end_ms, self.state.synced_time_ms)

    def _apply_pulse_view_mode(self):
        mode = self.pulse_view_mode_var.get()
        self.video_left.set_pulse_view_mode(mode)
        self.video_right.set_pulse_view_mode(mode)

    def _apply_pulse_background(self):
        enabled = self.pulse_background_var.get()
        self.video_left.set_pulse_background_enabled(enabled)
        self.video_right.set_pulse_background_enabled(enabled)

    def _apply_pulse_background_theme(self):
        theme = self.pulse_background_theme_var.get()
        self.video_left.set_pulse_background_theme(theme)
        self.video_right.set_pulse_background_theme(theme)

    def _overlay_channel_snapshot(self):
        current_ms = float(self.state.synced_time_ms)
        out = []
        source_items = self._pulse_base_snapshot if self._pulse_base_snapshot else self.channel_data
        for item in source_items:
            data = dict(item)
            time_values = np.asarray(data.get("time_ms") if data.get("time_ms") is not None else [], dtype=float)
            signal_values = np.asarray(data.get("values") if data.get("values") is not None else [], dtype=float)
            n = min(len(time_values), len(signal_values))
            if n > 0:
                distance = np.abs(time_values[:n] - current_ms)
                finite = np.isfinite(distance) & np.isfinite(signal_values[:n])
                if np.any(finite):
                    candidate_indexes = np.flatnonzero(finite)
                    idx = int(candidate_indexes[int(np.argmin(distance[finite]))])
                    data["current_value"] = float(signal_values[idx])
                else:
                    data["current_value"] = None
            else:
                data["current_value"] = None
            if data.get("peak_time_ms") is None or data.get("peak_value") is None:
                peak_time, peak_value = self._channel_abs_peak(time_values[:n], signal_values[:n])
                data["peak_time_ms"] = peak_time
                data["peak_value"] = peak_value
            out.append(data)
        return out

    def _rebuild_pulse_base_snapshot(self):
        self._pulse_base_snapshot = []
        for item in self.channel_data:
            data = dict(item)
            data["current_value"] = None
            self._pulse_base_snapshot.append(data)

    @staticmethod
    def _channel_abs_peak(time_values, signal_values):
        times = np.asarray([] if time_values is None else time_values, dtype=float)
        values = np.asarray([] if signal_values is None else signal_values, dtype=float)
        n = min(len(times), len(values))
        if n <= 0:
            return None, None
        times = times[:n]
        values = values[:n]
        finite = np.isfinite(times) & np.isfinite(values)
        if not np.any(finite):
            return None, None
        finite_indexes = np.flatnonzero(finite)
        peak_pos = int(np.argmax(np.abs(values[finite])))
        peak_index = int(finite_indexes[peak_pos])
        return float(times[peak_index]), float(values[peak_index])

    def _refresh_keyframe(self):
        start_ms, end_ms = self._timeline_range_ms()
        self.keyframe_timeline.set_state(end_ms - start_ms, self.state.synced_time_ms, self.state.keyframes, start_ms=start_ms, end_ms=end_ms)

    def _timeline_duration_ms(self):
        start_ms, end_ms = self._timeline_range_ms()
        return max(0.0, end_ms - start_ms)

    def _timeline_range_ms(self):
        start_ms = min(0.0, float(self.state.sync_frame_offset or 0))
        video_end_ms = float(max(0, self.state.frame_count - 1)) + float(self.state.sync_frame_offset or 0)
        data_duration = 0.0
        if self.channel_data:
            max_time = 0.0
            for item in self.channel_data:
                time_values = item.get("time_ms")
                arr = np.asarray([] if time_values is None else time_values, dtype=float)
                if arr.size:
                    finite = arr[np.isfinite(arr)]
                    if finite.size:
                        max_time = max(max_time, float(np.max(finite)))
            data_duration = max_time
        end_ms = max(0.0, video_end_ms, data_duration)
        if end_ms <= start_ms:
            end_ms = start_ms + 1.0
        return start_ms, end_ms

    def _video_time_range_ms(self):
        if self.state.frame_count <= 1 or not self._active_video_indices():
            return self._timeline_range_ms()
        start_ms = float(self.state.sync_frame_offset or 0)
        end_ms = start_ms + float(max(0, self.state.frame_count - 1))
        if end_ms <= start_ms:
            end_ms = start_ms + 1.0
        return start_ms, end_ms

    def _refresh_video_frames(self):
        viewers = (self.video_left, self.video_right)
        for index, viewer in enumerate(viewers):
            if self.captures[index] is None:
                if viewer.winfo_ismapped():
                    viewer.show_placeholder()
                continue
            frame = self._read_frame_cached(index, self.state.current_raw_frame)
            if frame is None:
                viewer.show_placeholder("Frame read failed")
                continue
            photo_frame = self._frame_to_photo_cached(index, self.state.current_raw_frame, frame, viewer)
            if isinstance(photo_frame, tuple):
                viewer.show_frame(photo_frame[0], photo_frame[1])
            else:
                viewer.show_frame(photo_frame)

    def _frame_to_photo_cached(self, slot_index, frame_index, frame, viewer):
        size = viewer.image_size()
        key = (int(slot_index), int(frame_index), int(size[0]), int(size[1]), round(float(viewer.zoom_scale or 1.0), 3))
        photo = self._photo_cache.get(key)
        if photo is not None:
            return photo
        photo = self._frame_to_photo(frame, viewer, size=size)
        if photo is None:
            return None
        if len(self._photo_cache) > 48:
            self._trim_photo_cache(int(frame_index))
        self._photo_cache[key] = photo
        return photo

    def _trim_photo_cache(self, center_frame):
        center = int(center_frame)
        active_slots = set(self._active_video_indices())
        for key in list(self._photo_cache):
            slot, frame, _width, _height, _zoom = key
            if slot not in active_slots or abs(int(frame) - center) > 4:
                self._photo_cache.pop(key, None)

    def _clear_photo_cache_slot(self, slot_index):
        slot = int(slot_index)
        for key in list(self._photo_cache):
            if key[0] == slot:
                self._photo_cache.pop(key, None)

    def _on_viewer_zoom_changed(self, slot_index):
        self._clear_photo_cache_slot(slot_index)
        self._schedule_refresh()

    def _request_frame_prefetch(self):
        active_slots = self._active_video_indices()
        if not active_slots or self.state.frame_count <= 0:
            return
        center = int(self.state.current_raw_frame)
        for index in active_slots:
            self._frame_prefetcher.request(index, center, self.state.frame_count, active_slots)

    def _request_segment_frame_prefetch(self):
        active_slots = self._active_video_indices()
        if not active_slots or self.state.frame_count <= 0:
            return
        center = int(self.state.current_raw_frame)
        for index in active_slots:
            self._frame_prefetcher.request(
                index,
                center,
                self.state.frame_count,
                active_slots,
                before_radius=SEGMENT_BACKWARD_MS,
                after_radius=SEGMENT_FORWARD_MS,
            )

    def _schedule_playback_buffer_refill(self):
        if not self.state.is_playing or self._playback_buffer_after_id is not None:
            return
        self._playback_buffer_after_id = self.after_idle(self._refill_playback_buffers)

    def _refill_playback_buffers(self):
        self._playback_buffer_after_id = None
        if not self.state.is_playing:
            return
        active_slots = self._active_video_indices()
        if not active_slots or self.state.frame_count <= 0:
            return
        center = int(self.state.current_raw_frame)
        end = min(int(self.state.frame_count) - 1, center + PLAYBACK_BUFFER_AHEAD)
        for slot_index in active_slots:
            filled = 0
            buffer = self._playback_buffers[slot_index]
            self._trim_playback_buffer(slot_index, center)
            for frame_index in range(center + 1, end + 1):
                if frame_index in buffer or self._frame_cache.contains(slot_index, frame_index):
                    continue
                frame = self._read_frame(slot_index, frame_index)
                if frame is None:
                    break
                buffer[frame_index] = frame
                self._frame_cache.set(
                    slot_index,
                    frame_index,
                    frame,
                    active_slots,
                    trim_center=center,
                    trim_before=SEGMENT_BACKWARD_MS,
                    trim_after=SEGMENT_FORWARD_MS,
                )
                filled += 1
                if filled >= PLAYBACK_BUFFER_REFILL_BATCH:
                    break
        if self.state.is_playing and any(
            any(frame_index not in self._playback_buffers[slot] and not self._frame_cache.contains(slot, frame_index)
                for frame_index in range(center + 1, end + 1))
            for slot in active_slots
        ):
            self._playback_buffer_after_id = self.after_idle(self._refill_playback_buffers)

    def _trim_playback_buffer(self, slot_index, center_frame):
        center = int(center_frame)
        keep_start = center
        keep_end = center + PLAYBACK_BUFFER_AHEAD
        buffer = self._playback_buffers[int(slot_index)]
        for frame_index in list(buffer):
            if frame_index < keep_start or frame_index > keep_end:
                buffer.pop(frame_index, None)

    def _reset_playback_buffers(self):
        self._cancel_playback_buffer_refill()
        for buffer in self._playback_buffers:
            buffer.clear()

    def _clear_playback_buffer(self, slot_index):
        self._playback_buffers[int(slot_index)].clear()

    def _cancel_playback_buffer_refill(self):
        if self._playback_buffer_after_id is not None:
            try:
                self.after_cancel(self._playback_buffer_after_id)
            except Exception:
                pass
            self._playback_buffer_after_id = None

    def _read_frame_cached(self, index, frame_index):
        if self.state.is_playing:
            buffered = self._playback_buffers[int(index)].pop(int(frame_index), None)
            if buffered is not None:
                return buffered
        cached = self._frame_cache.get(index, frame_index)
        if cached is not None:
            return cached
        frame = self._read_frame(index, frame_index)
        if frame is None:
            return None
        self._frame_cache.set(index, frame_index, frame, self._active_video_indices())
        return frame

    def _read_frame(self, index, frame_index):
        cv2 = _load_cv2()
        if cv2 is None or index < 0 or index >= MAX_VIDEOS or self.captures[index] is None:
            return None
        capture = self.captures[index]
        target_frame = int(frame_index)
        if self._capture_next_frames[index] != target_frame:
            capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ok, frame = capture.read()
        if not ok:
            self._capture_next_frames[index] = None
            return None
        self._capture_next_frames[index] = target_frame + 1
        return frame

    def _reset_capture_positions(self):
        self._capture_next_frames = [None] * MAX_VIDEOS
        self._reset_playback_buffers()

    def _frame_to_photo(self, frame, viewer, size=None):
        cv2 = _load_cv2()
        Image, ImageTk = _load_pillow()
        if cv2 is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        max_width, max_height = size or viewer.image_size()
        if Image is not None and ImageTk is not None:
            image = Image.fromarray(rgb)
            image.thumbnail((max_width, max_height))
            return ImageTk.PhotoImage(image), image.copy()

        height, width = rgb.shape[:2]
        scale = min(max_width / max(1, width), max_height / max(1, height), 1.0)
        if scale < 1.0:
            rgb = cv2.resize(rgb, (max(1, int(width * scale)), max(1, int(height * scale))))
        ok, encoded = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if not ok:
            return None
        try:
            return tk.PhotoImage(data=encoded.tobytes()), None
        except Exception:
            return None

    def confirm_reset_session_state(self):
        if not messagebox.askyesno(
            "VIDEO ANALYSIS",
            "현재 Video Analysis 상태를 초기화할까?\n로드된 동영상과 pulse 채널이 모두 해제된다.",
            parent=self,
        ):
            return
        self.reset_session_state()

    def reset_session_state(self):
        self.pause()
        self._cancel_pending_timeline_seek()
        for capture in self.captures:
            if capture is None:
                continue
            try:
                capture.release()
            except Exception:
                pass
        self.captures = [None] * MAX_VIDEOS
        self.video_infos = [None] * MAX_VIDEOS
        self.channel_data = []
        self._rebuild_pulse_base_snapshot()
        self._frame_prefetcher.stop_all()
        self._frame_cache.clear()
        self._photo_cache.clear()
        self._reset_capture_positions()
        self._playback_ui_frame_counter = 0
        self.state = VideoAnalysisState()
        self.video_left.show_placeholder()
        self.video_right.show_placeholder()
        self.video_left.reset_zoom()
        self.video_right.reset_zoom()
        self.pulse_timeline.set_channels([])
        for viewer in (self.video_left, self.video_right):
            viewer.set_pulse_overlay([], 0.0, 1.0, 0.0)
        self._refresh_channel_options()
        self._refresh_video_layout()
        self._refresh_all()
