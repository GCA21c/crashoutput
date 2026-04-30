from __future__ import annotations

from threading import RLock


class FrameCache:
    """Small frame cache keyed by fixed video slot and raw frame index."""

    def __init__(self, radius: int = 3, max_items: int = 32):
        self.radius = max(0, int(radius))
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

    def set(self, slot_index: int, frame_index: int, frame, active_slots=None) -> None:
        with self._lock:
            self._frames[(int(slot_index), int(frame_index))] = frame
            self.trim(int(frame_index), active_slots)

    def trim(self, center_frame: int, active_slots=None) -> None:
        with self._lock:
            if active_slots is None:
                active_slot_set = {slot for slot, _frame in self._frames}
            else:
                active_slot_set = {int(slot) for slot in active_slots}
            center = int(center_frame)
            keep = {
                (slot, center + delta)
                for slot in active_slot_set
                for delta in range(-self.radius, self.radius + 1)
            }
            for key in list(self._frames):
                if key not in keep:
                    self._frames.pop(key, None)
            if len(self._frames) <= self.max_items:
                return
            for key in list(self._frames)[: len(self._frames) - self.max_items]:
                self._frames.pop(key, None)
