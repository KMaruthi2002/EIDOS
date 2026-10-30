"""Reading frames from a video file at fixed times."""
from __future__ import annotations

import cv2

WIDTH = 448          # frames sent to the models are this wide; enough for hands, tools and labels


def small(frame, width: int = WIDTH):
    h, w = frame.shape[:2]
    return cv2.resize(frame, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)


def duration(path: str) -> float:
    cap = cv2.VideoCapture(path)
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.release()
    return n / fps if fps else 0.0


def sample(path: str, fps: float = 1.0, width: int = WIDTH, start: float = 0.0, end: float | None = None) -> list[tuple[float, object]]:
    """Frames at `fps`, as (seconds, image). Reads sequentially (fast on long videos)."""
    cap = cv2.VideoCapture(path)
    src = cap.get(cv2.CAP_PROP_FPS) or 30
    total = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / src
    end = total if end is None else min(end, total)
    out, nxt, i = [], start, 0
    if start > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
        i = int(start * src)
    while True:
        ok = cap.grab()
        if not ok:
            break
        t = i / src
        i += 1
        if t + 1e-6 < nxt:
            continue
        if t > end:
            break
        ok, f = cap.retrieve()
        if ok:
            out.append((round(t, 2), small(f, width)))
        nxt += 1.0 / fps
    cap.release()
    return out
