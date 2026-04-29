import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import numpy as np

from app.core.video.video_sync import VideoAnalysisState
from app.ui.components.pulse_timeline import PulseTimeline
from app.ui.components.video_viewer import KeyframeTimeline, VideoSlotViewer
from app.ui.styles import HEADER_FONT, MUTED_FG, PAGE_BG, TEXT_FG


PAGE_TITLE = "VIDEO ANALYSIS"
MAX_VIDEOS = 2
MAX_CHANNELS = 3


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
        self.captures = []
        self.video_infos = []
        self.channel_data = []
        self.channel_select_var = tk.StringVar()
        self._play_after_id = None
        self._refresh_after_id = None
        self._frame_cache = {}
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

        toolbar = tk.Frame(outer, bg=PAGE_BG)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        tk.Button(toolbar, text="Video Load", command=self.load_video, width=13).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Sync adjust", command=self.adjust_sync, width=13).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Reset", command=self.reset_session_state, width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Clear V1", command=lambda: self.clear_video(0), width=10).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Clear V2", command=lambda: self.clear_video(1), width=10).pack(side=tk.LEFT, padx=(8, 0))
        self.channel_combo = ttk.Combobox(toolbar, textvariable=self.channel_select_var, state="readonly", width=34)
        self.channel_combo.pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Add channel", command=self.add_channel, width=13).pack(side=tk.LEFT, padx=(8, 0))

        controls = tk.Frame(toolbar, bg=PAGE_BG)
        controls.pack(side=tk.LEFT, expand=True)
        tk.Button(controls, text="◀◀", command=self.prev_frame, width=7).pack(side=tk.LEFT, padx=4)
        self.play_button = tk.Button(controls, text="▶", command=self.toggle_play, width=7)
        self.play_button.pack(side=tk.LEFT, padx=4)
        tk.Button(controls, text="▶▶", command=self.next_frame, width=7).pack(side=tk.LEFT, padx=4)

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
        self.video_left.set_zoom_callback(lambda _scale=None, _center=None: self._schedule_refresh())
        self.video_right.set_zoom_callback(lambda _scale=None, _center=None: self._schedule_refresh())

        self.pulse_timeline = PulseTimeline(outer)

        keyframe_box = tk.LabelFrame(outer, text="Key frame", bg=PAGE_BG)
        keyframe_box.pack(fill=tk.X)
        self.keyframe_timeline = KeyframeTimeline(keyframe_box, on_seek=self._seek_timeline_ms)
        self.keyframe_timeline.pack(fill=tk.X, padx=8, pady=8)

        note = tk.Label(
            outer,
            text="Space: Play/Pause | Left/Right: 1 frame 이동 | Sync offset은 frame 단위이며 음수 frame/time 표시를 허용한다.",
            bg=PAGE_BG,
            fg=MUTED_FG,
            anchor="w",
        )
        note.pack(fill=tk.X, pady=(8, 0))

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
        if len(self.captures) >= MAX_VIDEOS:
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
        free_slots = MAX_VIDEOS - len(self.captures)
        selected = list(paths)[:free_slots]
        if len(paths) > free_slots:
            messagebox.showinfo("VIDEO ANALYSIS", "동영상은 최대 2개까지만 추가합니다.")

        new_captures = []
        new_infos = []
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
            new_captures.append(capture)
            new_infos.append({"path": str(path), "fps": fps, "frame_count": frame_count, "duration_ms": duration_ms})

        if not new_captures:
            return

        self.captures.extend(new_captures)
        self.video_infos.extend(new_infos)
        self._frame_cache.clear()
        self.video_left.reset_zoom()
        self.video_right.reset_zoom()
        master_fps = float(self.video_infos[0]["fps"])
        mismatched = [info for info in self.video_infos[1:] if abs(float(info["fps"]) - master_fps) > 0.01]
        if mismatched:
            messagebox.showwarning(
                "VIDEO ANALYSIS",
                "동영상 FPS가 서로 다릅니다. 초기 구현에서는 첫 번째 영상 FPS를 master로 사용합니다.",
            )
        frame_count = min(int(info["frame_count"]) for info in self.video_infos)
        self.state.set_video_master([info["path"] for info in self.video_infos], master_fps, frame_count)
        self._refresh_video_layout()
        self._refresh_all()

    def clear_video(self, index):
        if index < 0 or index >= len(self.captures):
            return
        self.pause()
        try:
            self.captures[index].release()
        except Exception:
            pass
        self.captures.pop(index)
        self.video_infos.pop(index)
        self._frame_cache.clear()
        self.video_left.reset_zoom()
        self.video_right.reset_zoom()
        if self.video_infos:
            master_fps = float(self.video_infos[0]["fps"])
            frame_count = min(int(info["frame_count"]) for info in self.video_infos)
            self.state.set_video_master([info["path"] for info in self.video_infos], master_fps, frame_count)
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
        self.state.selected_channels.append(selected)
        self.channel_data.append({
            "name": selected,
            "isocode": selected,
            "unit": unit,
            "time_ms": np.asarray(time_s, dtype=float) * 1000.0,
            "values": np.asarray(values, dtype=float),
        })
        self.pulse_timeline.set_channels(self.channel_data)
        self._refresh_channel_options()
        self._refresh_pulse()

    def clear_channels(self):
        self.state.selected_channels.clear()
        self.channel_data.clear()
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

    def _seek_timeline_ms(self, value_ms):
        self.pause()
        raw_frame = int(round(float(value_ms or 0.0) - float(self.state.sync_frame_offset)))
        self.state.set_frame(raw_frame)
        self._schedule_refresh()

    def _step_frame(self, delta, pause=True):
        if pause:
            self.pause()
        self.state.step_frame(delta)
        self._schedule_refresh()

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

    def toggle_play(self):
        if self.state.is_playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if not self.captures or self.state.frame_count <= 0:
            return
        self.state.is_playing = True
        self.play_button.configure(text="Ⅱ")
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

    def _schedule_play_step(self):
        if not self.state.is_playing:
            return
        delay_ms = max(1, int(round(1000.0 / max(1.0, float(self.state.playback_rate_fps or 30.0)))))
        self._play_after_id = self.after(delay_ms, self._play_step)

    def _play_step(self):
        self._play_after_id = None
        if not self.state.is_playing:
            return
        if self.state.current_raw_frame >= max(0, self.state.frame_count - 1):
            self.pause()
            return
        self.state.step_frame(1)
        self._schedule_refresh()
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

    def _refresh_video_layout(self):
        self.video_left.pack_forget()
        self.video_right.pack_forget()
        if len(self.captures) <= 1:
            self.video_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
            return
        self.video_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4), pady=8)
        self.video_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)

    def _refresh_all(self):
        self._refresh_status()
        self._refresh_video_frames()
        self._refresh_pulse()
        self._refresh_keyframe()

    def _refresh_status(self):
        self.time_var.set(f"Time : {self.state.synced_time_ms:.1f}ms")
        self.frame_var.set(f"Frame : {self.state.synced_frame:04d}")

    def _refresh_pulse(self):
        start_ms, end_ms = self._timeline_range_ms()
        self.pulse_timeline.set_cursor(self.state.synced_time_ms, start_ms=start_ms, end_ms=end_ms)
        overlay_channels = self._overlay_channel_snapshot()
        for viewer in (self.video_left, self.video_right):
            viewer.set_pulse_overlay(overlay_channels, start_ms, end_ms, self.state.synced_time_ms)

    def _overlay_channel_snapshot(self):
        current_ms = float(self.state.synced_time_ms)
        out = []
        for item in self.channel_data:
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
            out.append(data)
        return out

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

    def _refresh_video_frames(self):
        viewers = (self.video_left, self.video_right)
        for index, viewer in enumerate(viewers):
            if index >= len(self.captures):
                viewer.show_placeholder()
                continue
            frame = self._read_frame_cached(index, self.state.current_raw_frame)
            if frame is None:
                viewer.show_placeholder("Frame read failed")
                continue
            viewer.show_frame(self._frame_to_photo(frame, viewer))

    def _read_frame_cached(self, index, frame_index):
        key = (int(index), int(frame_index))
        cached = self._frame_cache.get(key)
        if cached is not None:
            return cached
        frame = self._read_frame(index, frame_index)
        if frame is None:
            return None
        self._frame_cache[key] = frame
        current = int(frame_index)
        keep = {
            (int(index), current + delta)
            for index in range(len(self.captures))
            for delta in range(-3, 4)
        }
        for cache_key in list(self._frame_cache.keys()):
            if cache_key not in keep:
                self._frame_cache.pop(cache_key, None)
        return frame

    def _read_frame(self, index, frame_index):
        cv2 = _load_cv2()
        if cv2 is None or index >= len(self.captures):
            return None
        capture = self.captures[index]
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ok, frame = capture.read()
        if not ok:
            return None
        return frame

    def _frame_to_photo(self, frame, viewer):
        cv2 = _load_cv2()
        Image, ImageTk = _load_pillow()
        if cv2 is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        max_width, max_height = viewer.image_size()
        if Image is not None and ImageTk is not None:
            image = Image.fromarray(rgb)
            image.thumbnail((max_width, max_height))
            return ImageTk.PhotoImage(image)

        height, width = rgb.shape[:2]
        scale = min(max_width / max(1, width), max_height / max(1, height), 1.0)
        if scale < 1.0:
            rgb = cv2.resize(rgb, (max(1, int(width * scale)), max(1, int(height * scale))))
        ok, encoded = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        if not ok:
            return None
        try:
            return tk.PhotoImage(data=encoded.tobytes())
        except Exception:
            return None

    def reset_session_state(self):
        self.pause()
        for capture in self.captures:
            try:
                capture.release()
            except Exception:
                pass
        self.captures = []
        self.video_infos = []
        self.channel_data = []
        self._frame_cache.clear()
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
