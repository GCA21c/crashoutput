from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VideoInfo:
    path: str
    fps: float
    frame_count: int
    duration_ms: float


@dataclass
class VideoAnalysisState:
    video_paths: list[str] = field(default_factory=list)
    fps: float = 1000.0
    frame_count: int = 0
    current_raw_frame: int = 0
    sync_frame_offset: int = 0
    selected_channels: list[str] = field(default_factory=list)
    is_playing: bool = False
    playback_rate_fps: float = 30.0
    keyframes: list[dict] = field(default_factory=list)

    def reset_videos(self) -> None:
        self.video_paths.clear()
        self.fps = 1000.0
        self.frame_count = 0
        self.current_raw_frame = 0
        self.is_playing = False

    def set_video_master(self, paths: list[str], fps: float, frame_count: int) -> None:
        self.video_paths = [str(path) for path in paths[:2]]
        self.fps = float(fps or 1000.0)
        self.frame_count = max(0, int(frame_count or 0))
        self.current_raw_frame = clamp_frame(self.current_raw_frame, self.frame_count)

    @property
    def synced_frame(self) -> int:
        return int(self.current_raw_frame) + int(self.sync_frame_offset)

    @property
    def synced_time_ms(self) -> float:
        # Video analysis sync is frame-based: high-speed video uses 1 frame = 1 ms.
        # fps remains metadata/playback information, not the pulse matching unit.
        return float(self.synced_frame)

    @property
    def duration_ms(self) -> float:
        return float(max(0, self.frame_count - 1))

    def set_frame(self, frame_index: int) -> None:
        self.current_raw_frame = clamp_frame(frame_index, self.frame_count)

    def step_frame(self, delta: int) -> None:
        self.set_frame(int(self.current_raw_frame) + int(delta))

    def set_sync_offset(self, offset: int) -> None:
        self.sync_frame_offset = int(offset or 0)

    def move_to_synced_zero(self) -> None:
        if int(self.sync_frame_offset) < 0:
            self.set_frame(abs(int(self.sync_frame_offset)))
        else:
            self.set_frame(0)


def clamp_frame(frame_index: int, frame_count: int) -> int:
    count = int(frame_count or 0)
    if count <= 0:
        return 0
    return max(0, min(int(frame_index or 0), count - 1))
