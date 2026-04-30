from __future__ import annotations

from threading import RLock


class FrameCache:
    """Small frame cache keyed by fixed video slot and raw frame index."""

    def __init__(self, radius: int = 3, max_items: int = 32, before_radius=None, after_radius=None):
        self.radius = max(0, int(radius))
        self.before_radius = self.radius if before_radius is None else max(0, int(before_radius))
        self.after_radius = self.radius if after_radius is None else max(0, int(after_radius))
        self.max_items = max(1, int(max_items))
        self._frames = {}
        self._lock = RLock()

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()

    def clear_slot(self, slot_index: int) -> None:
        slot = int(slot_index)
        with self._lock:
            for key in list(self._frames):
                if key[0] == slot:
                    self._frames.pop(key, None)

    def get(self, slot_index: int, frame_index: int):
        with self._lock:
            return self._frames.get((int(slot_index), int(frame_index)))

    def contains(self, slot_index: int, frame_index: int) -> bool:
        with self._lock:
            return (int(slot_index), int(frame_index)) in self._frames

    def set(self, slot_index: int, frame_index: int, frame, active_slots=None, trim_center=None, trim_before=None, trim_after=None) -> None:
        with self._lock:
            self._frames[(int(slot_index), int(frame_index))] = frame
            center = int(frame_index if trim_center is None else trim_center)
            self.trim(center, active_slots, before_radius=trim_before, after_radius=trim_after)

    def trim(self, center_frame: int, active_slots=None, before_radius=None, after_radius=None) -> None:
        with self._lock:
            if active_slots is None:
                active_slot_set = {slot for slot, _frame in self._frames}
            else:
                active_slot_set = {int(slot) for slot in active_slots}
            center = int(center_frame)
            before = self.before_radius if before_radius is None else max(0, int(before_radius))
            after = self.after_radius if after_radius is None else max(0, int(after_radius))
            keep = {
                (slot, center + delta)
                for slot in active_slot_set
                for delta in range(-before, after + 1)
            }
            for key in list(self._frames):
                if key not in keep:
                    self._frames.pop(key, None)
            if len(self._frames) <= self.max_items:
                return
            for key in list(self._frames)[: len(self._frames) - self.max_items]:
                self._frames.pop(key, None)
