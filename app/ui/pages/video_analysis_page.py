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
        self._play_after_id = None
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
        tk.Button(toolbar, text="Add channel", command=self.add_channel, width=13).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Sync adjust", command=self.adjust_sync, width=13).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(toolbar, text="Reset", command=self.reset_session_state, width=10).pack(side=tk.LEFT, padx=(8, 0))

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

        pulse_box = tk.LabelFrame(outer, text="Pulse", bg=PAGE_BG)
        pulse_box.pack(fill=tk.X, pady=(0, 10))
        pulse_header = tk.Frame(pulse_box, bg=PAGE_BG)
        pulse_header.pack(fill=tk.X, padx=8, pady=(6, 0))
        self.channel_label_var = tk.StringVar(value="Selected channels: -")
        tk.Label(pulse_header, textvariable=self.channel_label_var, bg=PAGE_BG, fg=MUTED_FG, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(pulse_header, text="Clear channels", command=self.clear_channels, width=14).pack(side=tk.RIGHT)
        self.pulse_timeline = PulseTimeline(pulse_box)
        self.pulse_timeline.pack(fill=tk.X, padx=8, pady=8)

        keyframe_box = tk.LabelFrame(outer, text="Key frame", bg=PAGE_BG)
        keyframe_box.pack(fill=tk.X)
        self.keyframe_timeline = KeyframeTimeline(keyframe_box)
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
            root.bind_all("<Left>", self._on_left)
            root.bind_all("<Right>", self._on_right)
            self._key_bindings_ready = True
        self.focus_set()
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
        master_fps = float(self.video_infos[0]["fps"])
        mismatched = [info for info in self.video_infos[1:] if abs(float(info["fps"]) - master_fps) > 0.01]
        if mismatched:
            messagebox.showwarning(
                "VIDEO ANALYSIS",
                "동영상 FPS가 서로 다릅니다. 초기 구현에서는 첫 번째 영상 FPS를 master로 사용합니다.",
            )
        frame_count = min(int(info["frame_count"]) for info in self.video_infos)
        self.state.set_video_master([info["path"] for info in self.video_infos], master_fps, frame_count)
        self._refresh_all()

    def add_channel(self):
        viewer = self.workbench.viewer
        if getattr(viewer, "df", None) is None or getattr(viewer, "time_column", None) is None:
            messagebox.showwarning("VIDEO ANALYSIS", "먼저 데이터를 로드하세요.")
            return
        if len(self.channel_data) >= MAX_CHANNELS:
            messagebox.showinfo("VIDEO ANALYSIS", "채널은 최대 3개까지 추가할 수 있습니다.")
            return
        columns = [str(col) for col in list(viewer.df.columns) if str(col) != str(viewer.time_column)]
        if not columns:
            messagebox.showwarning("VIDEO ANALYSIS", "추가할 데이터 채널이 없습니다.")
            return
        selected = self._select_channel(columns)
        if not selected:
            return
        if selected in self.state.selected_channels:
            messagebox.showinfo("VIDEO ANALYSIS", "이미 추가된 채널입니다.")
            return
        time_s = viewer.get_numeric_column(viewer.time_column)
        values = viewer.get_numeric_column(selected)
        self.state.selected_channels.append(selected)
        self.channel_data.append({"name": selected, "time_ms": np.asarray(time_s, dtype=float) * 1000.0, "values": np.asarray(values, dtype=float)})
        self._refresh_pulse()

    def clear_channels(self):
        self.state.selected_channels.clear()
        self.channel_data.clear()
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
        self.state.move_to_synced_zero()
        self._refresh_all()

    def prev_frame(self):
        self.pause()
        self.state.step_frame(-1)
        self._refresh_all()

    def next_frame(self):
        self.pause()
        self.state.step_frame(1)
        self._refresh_all()

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
        self._refresh_all()
        self._schedule_play_step()

    def _on_space(self, event):
        if self._is_active_page():
            self.toggle_play()
            return "break"
        return None

    def _on_left(self, event):
        if self._is_active_page():
            self.prev_frame()
            return "break"
        return None

    def _on_right(self, event):
        if self._is_active_page():
            self.next_frame()
            return "break"
        return None

    def _is_active_page(self):
        return getattr(self.workbench, "current_page_key", None) == "video_analysis"

    def _select_channel(self, columns):
        dialog = tk.Toplevel(self)
        dialog.title("Add channel")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.configure(bg=PAGE_BG)
        selected_var = tk.StringVar(value=columns[0])
        result = {"value": None}
        tk.Label(dialog, text="Pulse channel", bg=PAGE_BG, fg=TEXT_FG).pack(anchor="w", padx=12, pady=(12, 4))
        combo = ttk.Combobox(dialog, textvariable=selected_var, values=columns, state="readonly", width=72)
        combo.pack(fill=tk.X, padx=12, pady=(0, 10))
        buttons = tk.Frame(dialog, bg=PAGE_BG)
        buttons.pack(fill=tk.X, padx=12, pady=(0, 12))

        def accept():
            result["value"] = selected_var.get()
            dialog.destroy()

        def cancel():
            dialog.destroy()

        tk.Button(buttons, text="Add", command=accept, width=10).pack(side=tk.RIGHT)
        tk.Button(buttons, text="Cancel", command=cancel, width=10).pack(side=tk.RIGHT, padx=(0, 8))
        combo.focus_set()
        dialog.wait_window()
        return result["value"]

    def _refresh_all(self):
        self._refresh_status()
        self._refresh_video_frames()
        self._refresh_pulse()
        self._refresh_keyframe()

    def _refresh_status(self):
        self.time_var.set(f"Time : {self.state.synced_time_ms:.1f}ms")
        self.frame_var.set(f"Frame : {self.state.synced_frame:04d}")

    def _refresh_pulse(self):
        self.channel_label_var.set("Selected channels: " + (", ".join(self.state.selected_channels) if self.state.selected_channels else "-"))
        self.pulse_timeline.set_channels(self.channel_data)
        self.pulse_timeline.set_cursor(self.state.synced_time_ms, duration_ms=self._timeline_duration_ms())

    def _refresh_keyframe(self):
        self.keyframe_timeline.set_state(self._timeline_duration_ms(), self.state.synced_time_ms, self.state.keyframes)

    def _timeline_duration_ms(self):
        video_duration = self.state.duration_ms
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
        return max(video_duration, data_duration)

    def _refresh_video_frames(self):
        viewers = (self.video_left, self.video_right)
        for index, viewer in enumerate(viewers):
            if index >= len(self.captures):
                viewer.show_placeholder()
                continue
            frame = self._read_frame(index, self.state.current_raw_frame)
            if frame is None:
                viewer.show_placeholder("Frame read failed")
                continue
            viewer.show_frame(self._frame_to_photo(frame, viewer))

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
        self.state = VideoAnalysisState()
        self.video_left.show_placeholder()
        self.video_right.show_placeholder()
        self._refresh_all()
