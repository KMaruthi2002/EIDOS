"""Find coloured objects in images and turn pixels into table coordinates.

Used both on the person's demonstration video (to see what they did) and on
the robot's own cameras (to check each step). In live mode SAM 3.1 would
segment the objects by name ("the green block"); offline we segment by colour,
which is why the demonstration uses solid, distinct colours.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

# Hue ranges in OpenCV HSV (0-179). Saturation/value floors reject the table,
# shadows and skin.
COLORS = {
    "blue": [((95, 120, 60), (130, 255, 255))],
    "green": [((40, 90, 50), (88, 255, 255))],
    "yellow": [((18, 120, 120), (36, 255, 255))],
}


@dataclass
class Blob:
    name: str
    cx: float
    cy: float
    x: int
    y: int
    w: int
    h: int
    area: int

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h


def find(img_rgb: np.ndarray, names=None, min_area: int = 30) -> dict[str, Blob]:
    """Largest blob of each colour. Input is RGB (simulator) or BGR flipped by caller."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    out = {}
    for name, ranges in COLORS.items():
        if names and name not in names:
            continue
        mask = np.zeros(hsv.shape[:2], np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, stats, cents = cv2.connectedComponentsWithStats(mask)
        if n <= 1:
            continue
        i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        x, y, w, h, a = stats[i]
        if a < min_area:
            continue
        out[name] = Blob(name, float(cents[i][0]), float(cents[i][1]), int(x), int(y), int(w), int(h), int(a))
    return out


class TopCamera:
    """Pinhole model of the simulator's overhead camera (looking straight down)."""

    def __init__(self, pos=(0.5, 0.0, 1.05), fovy_deg=36.0, w=960, h=540):
        self.pos, self.w, self.h = pos, w, h
        self.f = (h / 2) / math.tan(math.radians(fovy_deg) / 2)

    def to_table(self, u: float, v: float, z: float = 0.0):
        depth = self.pos[2] - z
        # camera x-axis = world -y, camera y-axis (image up) = world +x
        wy = self.pos[1] - (u - self.w / 2) / self.f * depth
        wx = self.pos[0] - (v - self.h / 2) / self.f * depth
        return wx, wy


class SideCamera:
    """Low camera looking along +y at the table edge; gives heights."""

    def __init__(self, pos=(0.5, -0.85, 0.07), fovy_deg=30.0, w=960, h=540):
        self.pos, self.w, self.h = pos, w, h
        self.f = (h / 2) / math.tan(math.radians(fovy_deg) / 2)

    def height(self, v: float, world_y: float) -> float:
        depth = world_y - self.pos[1]
        return self.pos[2] - (v - self.h / 2) / self.f * depth


def relation(a: Blob, b: Blob, a_top: Blob | None = None, b_top: Blob | None = None) -> str:
    """Spatial relation of object a to object b in a side view (image coords).

    'on' when a's bottom edge meets b's top edge and they overlap
    horizontally; otherwise 'beside'.
    """
    overlap = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    touching = abs(a.bottom - b.top) <= max(4, 0.25 * b.h)
    if overlap > 0.5 * min(a.w, b.w) and touching and a.cy < b.cy:
        if a_top is not None and b_top is not None:
            # from above, a must sit over b
            if math.hypot(a_top.cx - b_top.cx, a_top.cy - b_top.cy) > 0.6 * max(b_top.w, b_top.h):
                return "beside"
        return "on"
    return "beside"


class Side2Camera:
    """Low camera on the far side of the table looking along -x; gives y and heights."""

    def __init__(self, pos=(1.25, 0.0, 0.07), fovy_deg=30.0, w=960, h=540):
        self.pos, self.w, self.h = pos, w, h
        self.f = (h / 2) / math.tan(math.radians(fovy_deg) / 2)


def locate_from_sides(b1: Blob, b2: Blob, cam1, cam2, iters: int = 4):
    """3D centre of an object from two level side views (cam1 along +y, cam2 along -x)."""
    x, y = 0.5, 0.0
    for _ in range(iters):
        d1 = y - cam1.pos[1]            # depth for cam1 (looks along +y; image right = +x)
        x = cam1.pos[0] + (b1.cx - cam1.w / 2) / cam1.f * d1
        d2 = cam2.pos[0] - x            # depth for cam2 (looks along -x; image right = +y)
        y = cam2.pos[1] + (b2.cx - cam2.w / 2) / cam2.f * d2
    z1 = cam1.pos[2] - (b1.cy - cam1.h / 2) / cam1.f * (y - cam1.pos[1])
    z2 = cam2.pos[2] - (b2.cy - cam2.h / 2) / cam2.f * (cam2.pos[0] - x)
    return x, y, (z1 + z2) / 2
