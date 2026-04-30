from __future__ import annotations

import threading


class FramePrefetchManager:
    """Slot-owned background frame prefetch using separate OpenCV captures."""

    def __init__(self, frame_cache, radius: int = 8):
        self.frame_cache = frame_cache
        self.radius = max(0, int(radius))
        self._workers = {}

    def start_slot(self, slot_index: int, path: str) -> None:
        self.stop_slot(slot_index)
        worker = _FramePrefetchWorker(int(slot_index), str(path), self.frame_cache, self.radius)
        self._workers[int(slot_index)] = worker
        worker.start()

    def stop_slot(self, slot_index: int) -> None:
        worker = self._workers.pop(int(slot_index), None)
        if worker is not None:
            worker.stop()

    def stop_all(self) -> None:
        for slot in list(self._workers):
            self.stop_slot(slot)

    def request(
        self,
        slot_index: int,
        center_frame: int,
        frame_count: int,
        active_slots=None,
        radius=None,
        before_radius=None,
        after_radius=None,
    ) -> None:
        worker = self._workers.get(int(slot_index))
        if worker is None:
            return
        worker.request(
            center_frame,
            frame_count,
            active_slots,
            radius=radius,
            before_radius=before_radius,
            after_radius=after_radius,
        )


class _FramePrefetchWorker:
    def __init__(self, slot_index: int, path: str, frame_cache, radius: int):
        self.slot_index = int(slot_index)
        self.path = str(path)
        self.frame_cache = frame_cache
        self.radius = max(0, int(radius))
        self._stop_event = threading.Event()
        self._request_event = threading.Event()
        self._lock = threading.Lock()
        self._request = None
        self._thread = threading.Thread(target=self._run, name=f"VideoPrefetch-{slot_index}", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._request_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=0.8)

    def request(self, center_frame: int, frame_count: int, active_slots=None, radius=None, before_radius=None, after_radius=None) -> None:
        request_radius = self.radius if radius is None else max(0, int(radius))
        before = request_radius if before_radius is None else max(0, int(before_radius))
        after = request_radius if after_radius is None else max(0, int(after_radius))
        with self._lock:
            self._request = (
                int(center_frame),
                int(frame_count or 0),
                tuple(int(slot) for slot in (active_slots or (self.slot_index,))),
                before,
                after,
            )
        self._request_event.set()

    def _take_request(self):
        with self._lock:
            request = self._request
            self._request = None
            self._request_event.clear()
            return request

    def _run(self) -> None:
        try:
            import cv2  # type: ignore
        except ImportError:
            return
        capture = cv2.VideoCapture(self.path)
        try:
            if not capture.isOpened():
                return
            while not self._stop_event.is_set():
                self._request_event.wait(timeout=0.25)
                if self._stop_event.is_set():
                    break
                request = self._take_request()
                if request is None:
                    continue
                center_frame, frame_count, active_slots, before, after = request
                if frame_count <= 0:
                    continue
                start = max(0, center_frame - before)
                end = min(frame_count - 1, center_frame + after)
                capture.set(cv2.CAP_PROP_POS_FRAMES, start)
                for frame_index in range(start, end + 1):
                    if self._stop_event.is_set() or self._request_event.is_set():
                        break
                    if self.frame_cache.contains(self.slot_index, frame_index):
                        capture.grab()
                        continue
                    ok, frame = capture.read()
                    if not ok:
                        break
                    self.frame_cache.set(self.slot_index, frame_index, frame, active_slots, trim_center=center_frame)
        finally:
            capture.release()
