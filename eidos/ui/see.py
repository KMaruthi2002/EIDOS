"""Offline perception for everyday app screens, from pixels only.

  lines(img)          words read by OCR, grouped into text lines with boxes
  boxes(img)          rectangles drawn on screen: fields, buttons, switches
  find_text(...)      where a phrase appears, tolerant of case and OCR noise
  field_for(...)      the input box that belongs to a label (to its right or below it)
  switch_for(...)     the on/off switch on the same row as a label
  is_on(...)          a switch is "on" when it is filled with color, "off" when grey

Live mode hands these jobs to SAM 3.1 (segment "the text field labelled To")
and Muse Spark (read the screen).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

from .. import vision as V


@dataclass
class Line:
    text: str
    x: int
    y: int
    w: int
    h: int
    words: list

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


def _iou(a, b) -> float:
    ix = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    iy = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    inter = ix * iy
    return inter / max(1, min(a.w * a.h, b.w * b.h))


def norm(s: str) -> str:
    s = s.lower().replace("…", "").replace("|", "")
    return re.sub(r"\s+", " ", s).strip(" .:,;")


def lines(img) -> list[Line]:
    img = V.to_bgr(img)
    words = V.dedupe(V.ocr_words(img, scale=2.0, psm=11, min_conf=35) +
                     V.ocr_words(img, scale=2.0, psm=11, min_conf=35, binarize=True) +
                     # sparse mode sometimes skips a whole row (seen next to a focused field); page mode doesn't
                     V.ocr_words(img, scale=2.0, psm=3, min_conf=45))
    # Icons and switches read as stray symbols ("CD", "@"): short and taller than text.
    if words:
        mh = float(np.median([w.h for w in words]))
        words = [w for w in words if not (len(w.text) <= 2 and not w.text.isdigit() and w.h > 1.6 * mh)
                 and any(ch.isalnum() for ch in w.text)]
    # Light text on colored fills (primary buttons, toasts): read each filled box on its own.
    gray_all = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for b in boxes(img):
        if not (40 <= b[2] <= 420 and 22 <= b[3] <= 64):
            continue
        has_word = any(inside(b, w.cx, w.cy) for w in words)
        inner = gray_all[b[1] + 4:b[1] + b[3] - 4, b[0] + 4:b[0] + b[2] - 4]
        if _filled(img, b) or (not has_word and not is_switch(b) and inner.size and inner.std() > 18):
            t = read_label(img, (b[0] + 4, b[1] + 3, b[2] - 8, b[3] - 6))
            t = re.sub(r"[^\w@.,:'$&/ -]", "", t).strip()
            t = " ".join(tok for tok in t.split() if any(ch.isalnum() for ch in tok))
            if len(t) >= 2:
                words = [w for w in words if not inside(b, w.cx, w.cy)]
                cw = b[2] / max(1, len(t))
                x = b[0] + 4
                for tok in t.split():
                    words.append(V.Word(tok, int(x), b[1] + 4, int(cw * len(tok)), b[3] - 8, SYNTH))
                    x += cw * (len(tok) + 1)
    # drop overlapping duplicates from the several passes (keep the more confident)
    words.sort(key=lambda w: -w.conf)
    kept = []
    for w in words:
        if all(_iou(w, k) < 0.3 for k in kept):
            kept.append(w)
    # rows by vertical position, then split each row where the gap is wide
    kept.sort(key=lambda w: w.cy)
    rows: list[list] = []
    for w in kept:
        if rows and abs(rows[-1][-1].cy - w.cy) < max(5, 0.5 * min(rows[-1][-1].h, w.h)):
            rows[-1].append(w)
        else:
            rows.append([w])
    out: list[list] = []
    for r in rows:
        r.sort(key=lambda w: w.x)
        cur = [r[0]]
        for w in r[1:]:
            if w.x - (cur[-1].x + cur[-1].w) <= 0.9 * min(cur[-1].h, w.h) + 6:
                cur.append(w)
            else:
                out.append(cur)
                cur = [w]
        out.append(cur)
    res = []
    for ln in out:
        ln.sort(key=lambda w: w.x)
        x0, y0 = min(w.x for w in ln), min(w.y for w in ln)
        x1, y1 = max(w.x + w.w for w in ln), max(w.y + w.h for w in ln)
        res.append(Line(" ".join(w.text for w in ln), x0, y0, x1 - x0, y1 - y0, ln))
    return res


SYNTH = 99.5   # confidence given to words read box-by-box (their boxes are estimates)


def _filled(img, b) -> bool:
    """A box painted in a strong color (or dark fill) rather than outlined."""
    x, y, w, h = b
    crop = img[y + 3:y + h - 3, x + 3:x + w - 3]
    if crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return float(np.median(hsv[..., 1])) > 90 or float(np.median(hsv[..., 2])) < 70 and not V.is_dark(img)


def read_label(img, box) -> str:
    """One line of text on any fill: text is the minority ink, whatever its color."""
    import subprocess
    x, y, w, h = [int(v) for v in box]
    crop = cv2.cvtColor(V.to_bgr(img)[max(0, y):y + h, max(0, x):x + w], cv2.COLOR_BGR2GRAY)
    if crop.size == 0:
        return ""
    big = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if (bw == 0).mean() > 0.5:          # ink must be the minority: make text black on white
        bw = 255 - bw
    bw = cv2.copyMakeBorder(bw, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)
    ok, png = cv2.imencode(".png", bw)
    out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7"], input=png.tobytes(),
                         capture_output=True).stdout.decode("utf-8", "ignore")
    return out.strip()


def boxes(img, min_w=24, min_h=14) -> list[tuple[int, int, int, int]]:
    """Rectangles on screen (outlined or filled), deduplicated."""
    img = V.to_bgr(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 18, 60)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    H, W = gray.shape
    out = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w < min_w or h < min_h or w > 0.95 * W or h > 0.8 * H:
            continue
        # keep shapes that fill their bounding box like a (rounded) rectangle
        if cv2.contourArea(cv2.convexHull(c)) < 0.72 * w * h:
            continue
        out.append((x, y, w, h))
    out.sort(key=lambda b: b[2] * b[3])
    uniq = []
    for b in out:
        if not any(abs(b[0] - u[0]) <= 4 and abs(b[1] - u[1]) <= 4 and abs(b[2] - u[2]) <= 8 and abs(b[3] - u[3]) <= 8 for u in uniq):
            uniq.append(b)
    return uniq


def inside(b, x, y, pad=0):
    return b[0] - pad <= x <= b[0] + b[2] + pad and b[1] - pad <= y <= b[1] + b[3] + pad


def box_at(bxs, x, y, max_w=None):
    c = [b for b in bxs if inside(b, x, y) and (max_w is None or b[2] <= max_w)]
    return min(c, key=lambda b: b[2] * b[3]) if c else None


def is_field(b):
    return 110 <= b[2] <= 800 and 26 <= b[3] <= 150


def is_switch(b):
    return 30 <= b[2] <= 66 and 18 <= b[3] <= 40 and 1.4 <= b[2] / b[3] <= 2.6


def overlaps_text(b, lns, frac=0.25):
    x, y, w, h = b
    for ln in [w for l in lns for w in l.words if sum(ch.isalpha() for ch in w.text) >= 3]:
        ix = max(0, min(x + w, ln.x + ln.w) - max(x, ln.x))
        iy = max(0, min(y + h, ln.y + ln.h) - max(y, ln.y))
        if ix * iy > frac * w * h:
            return True
    return False


def sim(a: str, b: str) -> float:
    return V.similar(norm(a), norm(b))


def find_text(lns: list[Line], phrase: str, thresh: float = 0.8, region=None):
    """Every place `phrase` appears: (score, x, y, w, h), best first.

    Matches whole lines and runs of words inside a line, so a button label
    is found even when OCR merges it with neighbouring text.
    """
    n = max(1, len(phrase.split()))
    hits = []
    for ln in lns:
        ws = ln.words
        for k in (n - 1, n, n + 1):
            if k < 1:
                continue
            for i in range(0, max(1, len(ws) - k + 1)):
                span = ws[i:i + k]
                if not span:
                    continue
                s = sim(" ".join(w.text for w in span), phrase)
                if s >= thresh:
                    x0, y0 = span[0].x, min(w.y for w in span)
                    x1, y1 = span[-1].x + span[-1].w, max(w.y + w.h for w in span)
                    if region and not inside(region, (x0 + x1) / 2, (y0 + y1) / 2):
                        continue
                    hits.append((s, x0, y0, x1 - x0, y1 - y0))
    # Labels that wrap onto two lines ("RECOVERY" / "EMAIL"): join left-aligned stacked lines.
    if n >= 2:
        for a in lns:
            for b in lns:
                if b is a or abs(b.x - a.x) > 8 or not (0 <= b.y - (a.y + a.h) <= 1.2 * max(a.h, b.h) + 2):
                    continue
                sc = sim(a.text + " " + b.text, phrase)
                if sc >= thresh:
                    x0, y0 = min(a.x, b.x), a.y
                    x1, y1 = max(a.x + a.w, b.x + b.w), b.y + b.h
                    if region and not inside(region, (x0 + x1) / 2, (y0 + y1) / 2):
                        continue
                    hits.append((sc, x0, y0, x1 - x0, y1 - y0))
    hits.sort(key=lambda h: -h[0])
    return hits


def field_for(label_hit, bxs):
    """The field belonging to a label: on the same row to its right, or just below it."""
    s, x, y, w, h = label_hit
    cy = y + h / 2
    best, bd = None, 1e9
    fields = [b for b in bxs if is_field(b)]
    for b in bxs:
        if not is_field(b):
            continue
        # a box that wraps another field (a row, or a focus ring merged with a label) is not a field
        if any(o != b and o[0] >= b[0] - 1 and o[1] >= b[1] - 1 and o[0] + o[2] <= b[0] + b[2] + 1
               and o[1] + o[3] <= b[1] + b[3] + 1 and o[3] < b[3] - 8 for o in fields):
            continue
        bx, by, bw, bh = b
        if inside(b, x + w / 2, cy):        # the label is inside a box: not this one
            continue
        if bx >= x + w - 4 and by - 6 <= cy <= by + min(bh, 44) + 6:      # right, same row
            d = bx - (x + w)
        elif by >= y + h - 4 and by - (y + h) < 46 and bx - 30 <= x <= bx + bw:   # below
            d = (by - (y + h)) + abs(bx - x) * 0.2
        else:
            continue
        if d < bd:
            best, bd = b, d
    return best


def switch_for(label_hit, bxs, lns):
    s, x, y, w, h = label_hit
    cy = y + h / 2
    c = [b for b in bxs if is_switch(b) and abs((b[1] + b[3] / 2) - cy) < 26 and not overlaps_text(b, lns)]
    if not c:
        return None
    return min(c, key=lambda b: abs((b[0] + b[2] / 2) - (x + w / 2)))


def saturation(img, b) -> float:
    x, y, w, h = b
    crop = V.to_bgr(img)[y + 3:y + h - 3, x + 3:x + w - 3]
    if crop.size == 0:
        return 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return float(np.median(hsv[..., 1]))


def colored(img, b) -> float:
    """Share of the box painted in a vivid color (an 'on' switch is; an 'off' one is grey)."""
    x, y, w, h = b
    crop = V.to_bgr(img)[y + 2:y + h - 2, x + 2:x + w - 2]
    if crop.size == 0:
        return 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return float(((hsv[..., 1] > 90) & (hsv[..., 2] > 70)).mean())


def is_on(img, b) -> bool:
    return colored(img, b) > 0.3


def read_box(img, b) -> str:
    """Text inside a field. Multi-line boxes are read line by line."""
    x, y, w, h = b
    if h > 60:
        crop = V.normalize_for_ocr(V.to_bgr(img)[y + 4:y + h - 4, x + 4:x + w - 4])
        crop = cv2.normalize(crop, None, 0, 255, cv2.NORM_MINMAX)
        big = cv2.copyMakeBorder(cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC),
                                 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
        ok, png = cv2.imencode(".png", big)
        import subprocess
        out = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6"], input=png.tobytes(),
                             capture_output=True).stdout.decode("utf-8", "ignore")
        return " ".join(out.split())
    return V.ocr_region(img, (x + 3, y + 3, w - 6, h - 6))
