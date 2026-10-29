"""Pixel-level perception used by EIDOS when it runs offline.

Live mode hands these jobs to Meta's models (SAM 3.1 for segmentation and
grounding, Muse Spark for reading the screen). Offline mode uses classic
computer vision so the whole pipeline still runs end to end, from pixels
only, without an API key:

  * OCR (Tesseract) to read words and their positions
  * grid inference: which column is "Revenue", where the data ends
  * template matching to find a control seen in the tutorial
  * simple pixel statistics for checking visual contracts
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from difflib import SequenceMatcher
from statistics import median

import cv2
import numpy as np


# --------------------------------------------------------------------------- OCR

@dataclass
class Word:
    text: str
    x: int
    y: int
    w: int
    h: int
    conf: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def to_bgr(img) -> np.ndarray:
    if isinstance(img, (bytes, bytearray)):
        arr = np.frombuffer(img, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if isinstance(img, str):
        return cv2.imread(img, cv2.IMREAD_COLOR)
    return img


def is_dark(img: np.ndarray) -> bool:
    return float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean()) < 110


def normalize_for_ocr(img: np.ndarray, binarize: bool = False) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if gray.mean() < 110:
        gray = 255 - gray
    if binarize:
        # Keep only dark ink: drops gridlines, selection borders, tinted fills.
        gray = np.where(gray < 120, 0, 255).astype(np.uint8)
    return gray


def ocr_words(img, scale: float = 2.0, psm: int = 11, min_conf: float = 40,
              binarize: bool = False) -> list[Word]:
    """Return words with boxes in the ORIGINAL image's coordinates."""
    img = to_bgr(img)
    gray = normalize_for_ocr(img)
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if binarize:
        big = np.where(big < 140, 0, 255).astype(np.uint8)
    ok, png = cv2.imencode(".png", big)
    out = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", str(psm), "tsv"],
        input=png.tobytes(), capture_output=True, check=False,
    ).stdout.decode("utf-8", "ignore")
    words = []
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 12 or not parts[11].strip():
            continue
        conf = float(parts[10])
        if conf < min_conf:
            continue
        x, y, w, h = (int(int(v) / scale) for v in parts[6:10])
        text = parts[11].strip().strip("[]|()'\"`")
        if text:
            words.append(Word(text, x, y, w, h, conf))
    return words


def dedupe(words: list[Word], radius: float = 14) -> list[Word]:
    """Merge words found by several OCR passes at the same place."""
    out: list[Word] = []
    for w in sorted(words, key=lambda w: -w.conf):
        if not any(abs(w.cx - o.cx) < radius and abs(w.cy - o.cy) < 8 for o in out):
            out.append(w)
    return out


def ocr_region(img, box, scale: float = 3.0, digits: bool = False) -> str:
    """Read a single line of text inside box=(x, y, w, h)."""
    img = to_bgr(img)
    x, y, w, h = [int(v) for v in box]
    x, y = max(0, x), max(0, y)
    crop = img[y:y + h, x:x + w]
    if crop.size == 0:
        return ""
    gray = normalize_for_ocr(crop)
    # Erase border and grid lines that run the full height of the box: OCR
    # reads them as '1' or '|'.
    # Only lines touching the box edges count as borders; strokes of
    # characters in the middle of the box are left alone.
    ink = gray < 150
    edge = 4
    for x in list(range(min(edge, gray.shape[1]))) + list(range(max(0, gray.shape[1] - edge), gray.shape[1])):
        if ink[:, x].mean() > 0.9:
            gray[:, x] = 255
    for y in list(range(min(edge, gray.shape[0]))) + list(range(max(0, gray.shape[0] - edge), gray.shape[0])):
        if ink[y, :].mean() > 0.9:
            gray[y, :] = 255
    # Stretch contrast: dim labels on dark themes are otherwise invisible to OCR.
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if digits:
        _, big = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    big = cv2.copyMakeBorder(big, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255)
    ok, png = cv2.imencode(".png", big)
    out = subprocess.run(
        ["tesseract", "stdin", "stdout", "--psm", "7"]
        + (["-c", "tessedit_char_whitelist=0123456789"] if digits else []),
        input=png.tobytes(), capture_output=True, check=False,
    ).stdout.decode("utf-8", "ignore")
    return out.strip()


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def parse_number(s: str) -> float | None:
    s = s.replace(",", "").replace("O", "0").replace("o", "0").strip()
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None


# ------------------------------------------------------------------ grid model

@dataclass
class Grid:
    """A spreadsheet-like table as perceived on screen."""
    headers: list[Word]          # header words, left to right
    header_y: float
    data_rows_y: list[float]     # y centers of rows that contain data
    row_h: float
    col_pitch: float
    row_labels: dict[int, str]   # data-row index -> row number shown in gutter

    def col_x(self, header: str | None = None, index: int | None = None) -> float:
        if header is not None:
            return self.find_header(header).cx
        return self.headers[index].cx

    def find_header(self, name: str) -> Word:
        best = max(self.headers, key=lambda w: similar(w.text, name))
        if similar(best.text, name) < 0.6:
            raise LookupError(f"column '{name}' not found on screen")
        return best

    def col_index(self, name: str) -> int:
        """Column position counted on screen from the first table column."""
        first = self.headers[0].cx
        return int(round((self.find_header(name).cx - first) / self.col_pitch))

    @property
    def first_empty_row_y(self) -> float:
        return self.data_rows_y[-1] + self.row_h

    def header_names(self) -> list[str]:
        return [w.text for w in self.headers]


def infer_grid(img, expected_headers: list[str]) -> Grid:
    """Find the header row and data extent using OCR only.

    expected_headers are the column names seen in the tutorial; the screen
    may show them in a different order, position, size, or color scheme.
    """
    img = to_bgr(img)
    # Two OCR passes at different scales: a selection border or tight
    # spacing can hide a word from one pass but rarely from both.
    words = dedupe(ocr_words(img, scale=2.0) + ocr_words(img, scale=3.0)
                   + ocr_words(img, scale=3.0, binarize=True))
    # Header row = the visual line holding the most expected header names.
    cands = [w for w in words if any(similar(w.text, h) >= 0.75 for h in expected_headers)]
    if not cands:
        raise LookupError("no header row found")
    hdr = max(([c for c in cands if abs(c.cy - w.cy) <= 8] for w in cands), key=len)
    # The header line also holds names we have never seen (a new dataset):
    # take every word on that line.
    line_y = median(w.cy for w in hdr)
    known = sorted(dedupe(hdr), key=lambda w: w.cx)
    line = sorted(dedupe([w for w in words if abs(w.cy - line_y) <= 8
                          and re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]+", w.text)] + known), key=lambda w: w.cx)
    # Column pitch from neighbouring words on the header line (the known
    # names may not be adjacent columns).
    gaps = [b.cx - a.cx for a, b in zip(line, line[1:]) if b.cx - a.cx > 30]
    step = median(gaps) if gaps else 140
    # Grow outward from the known names while columns stay evenly spaced,
    # so a sidebar or title on the same line is not mistaken for a column.
    lo = min(range(len(line)), key=lambda i: abs(line[i].cx - known[0].cx))
    hi = min(range(len(line)), key=lambda i: abs(line[i].cx - known[-1].cx))
    while lo > 0 and line[lo].cx - line[lo - 1].cx <= step * 1.4:
        lo -= 1
    while hi < len(line) - 1 and line[hi + 1].cx - line[hi].cx <= step * 1.4:
        hi += 1
    # A real column has data underneath it; a sidebar item on the same line
    # does not (or has only a few stacked menu items).
    def has_data(h):
        below = [w for w in words if w.cy > h.cy + 8 and abs(w.cx - h.cx) < step * 0.45
                 and re.fullmatch(r"[A-Za-z0-9.,$-]{2,}|\d", w.text)]
        return len(below) >= 4
    cols = [w for w in line[lo:hi + 1] if has_data(w) or any(w is k for k in known)]
    hdr = []
    for w in cols:
        if hdr and (w.cx - hdr[-1].cx < step * 0.5):
            # two readings of one header cell: keep the more confident one
            if w.conf > hdr[-1].conf:
                hdr[-1] = w
            continue
        hdr.append(w)
    header_y = median(w.cy for w in hdr)
    pitch = median(b.cx - a.cx for a, b in zip(hdr, hdr[1:])) if len(hdr) > 1 else 110

    # Data rows: words below the header that sit under the first or last header column.
    anchors = [hdr[0], hdr[-1]]
    ys = []
    for w in words:
        if w.cy <= header_y + 4 or not re.fullmatch(r"[A-Za-z0-9.,$-]{2,}|\d", w.text):
            continue
        if w.x + w.w < hdr[0].x - 6:      # row-number gutter, not data
            continue
        if any(abs(w.cx - a.cx) < pitch * 0.45 for a in anchors):
            ys.append(w.cy)
    ys.sort()
    rows: list[float] = []
    for y in ys:
        if not rows or y - rows[-1] > 6:
            rows.append(y)
        else:
            rows[-1] = (rows[-1] + y) / 2
    # Keep the contiguous block directly under the header.
    if rows:
        gaps = [b - a for a, b in zip(rows, rows[1:])]
        row_h = median(gaps) if gaps else 25
        block = [rows[0]]
        for y in rows[1:]:
            if y - block[-1] < row_h * 1.6:
                block.append(y)
            else:
                break
        rows = block
    else:
        row_h = 25

    # Row numbers: read the gutter left of the first column, one row at a time.
    gutter_right = hdr[0].x - pitch * 0.12
    labels = {}
    for i, y in enumerate(rows):
        box = (max(0, gutter_right - 50), y - row_h * 0.42, 46, row_h * 0.84)
        t = ocr_region(img, box, digits=True)
        if t.isdigit():
            labels[i] = t
    # Row numbers go up by one per row: take the offset most rows agree on,
    # which also corrects single misread digits.
    if labels:
        from collections import Counter
        base = Counter(int(v) - i for i, v in labels.items()).most_common(1)[0][0]
        labels = {i: str(base + i) for i in range(len(rows))}
    return Grid(hdr, header_y, rows, row_h, pitch, labels)


def column_bounds(img, grid: Grid) -> list[tuple[float, float]]:
    """Left/right edge of each header column, from the drawn gridlines.

    Sums vertical-edge strength over the table body; gridlines show up as
    peaks. Falls back to the header pitch if the lines are too faint.
    """
    img = to_bgr(img)
    gray = normalize_for_ocr(img).astype(np.float32)
    top = int(grid.header_y - grid.row_h * 0.5)
    bot = int(grid.data_rows_y[-1] + grid.row_h * 0.5) if grid.data_rows_y else top + 200
    band = gray[max(0, top):bot]
    # a gridline is a 1-2px column darker than both neighbours on most rows
    left = np.roll(band, 2, axis=1)
    right = np.roll(band, -2, axis=1)
    darker = ((band < left - 6) & (band < right - 6)).mean(axis=0)
    xs = [x for x in range(2, len(darker) - 2) if darker[x] > 0.55 and darker[x] >= darker[x - 1] and darker[x] >= darker[x + 1]]
    lines: list[int] = []
    for x in xs:
        if not lines or x - lines[-1] > 4:
            lines.append(x)
    hs = grid.headers
    # Width: spacing of header text (left-aligned and centred layouts alike).
    mw = median(b.x - a.x for a, b in zip(hs, hs[1:])) if len(hs) > 1 else grid.col_pitch
    # Offset of the text inside its column, measured on columns whose left
    # gridline is clearly visible.
    offs = []
    for h in hs:
        near = [x for x in lines if 0 <= h.x - x <= mw * 0.6]
        if near:
            offs.append(h.x - near[-1])
    off = median(offs) if offs else 5.0
    out = []
    for h in hs:
        l_hat = h.x - off
        snap = [x for x in lines if abs(x - l_hat) <= 8]
        l = float(min(snap, key=lambda x: abs(x - l_hat))) if snap else l_hat
        r_hat = l + mw
        snap = [x for x in lines if abs(x - r_hat) <= 8]
        r = float(min(snap, key=lambda x: abs(x - r_hat))) if snap else r_hat
        out.append((float(l), float(r)))
    return out


def column_letter(index: int) -> str:
    s = ""
    index += 1
    while index:
        index, r = divmod(index - 1, 26)
        s = chr(65 + r) + s
    return s


def cell_box(grid: Grid, x: float, y: float) -> tuple[int, int, int, int]:
    """Box around a cell centered on the column's x and the row's y."""
    w = grid.col_pitch * 0.95
    h = grid.row_h * 0.9
    # Left-aligned apps put text near the left edge, centered apps around cx;
    # a box spanning most of the pitch covers both.
    return int(x - w / 2), int(y - h / 2), int(w), int(h)


# ------------------------------------------------------------ template finding

def find_template(screen, template, min_gray: float = 0.85, min_edge: float = 0.6):
    """Find a control seen in the tutorial on the current screen.

    Tries an intensity match first (same look), then an edge match across a
    few scales (survives color-scheme changes and resizing). Returns
    (x, y, score, method) or None.
    """
    screen = to_bgr(screen)
    template = to_bgr(template)
    sg, tg = normalize_for_ocr(screen), normalize_for_ocr(template)
    best = None
    for scale in (1.0, 0.9, 1.1, 0.8, 1.25, 1.4):
        t = cv2.resize(tg, None, fx=scale, fy=scale) if scale != 1.0 else tg
        if t.shape[0] >= sg.shape[0] or t.shape[1] >= sg.shape[1]:
            continue
        _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(sg, t, cv2.TM_CCOEFF_NORMED))
        if best is None or score > best[2]:
            best = (loc[0] + t.shape[1] / 2, loc[1] + t.shape[0] / 2, float(score), "intensity")
    if best and best[2] >= min_gray:
        return best
    se, te0 = cv2.Canny(sg, 50, 150), cv2.Canny(tg, 50, 150)
    best = None
    for scale in (1.0, 0.9, 1.1, 0.8, 1.25, 1.4):
        t = cv2.resize(te0, None, fx=scale, fy=scale) if scale != 1.0 else te0
        if t.shape[0] >= se.shape[0] or t.shape[1] >= se.shape[1]:
            continue
        _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(se, t, cv2.TM_CCOEFF_NORMED))
        if best is None or score > best[2]:
            best = (loc[0] + t.shape[1] / 2, loc[1] + t.shape[0] / 2, float(score), "edges")
    if best and best[2] >= min_edge:
        return best
    return None


# ------------------------------------------------------------ contract helpers

def ink_ratio(img, box) -> float:
    """Share of 'text' pixels in a region. Bold text raises it."""
    img = to_bgr(img)
    x, y, w, h = [max(0, int(v)) for v in box]
    gray = normalize_for_ocr(img[y:y + h, x:x + w])
    if gray.size == 0:
        return 0.0
    return float((gray < 110).mean())


def changed_box(before, after, thresh: int = 28):
    """Bounding box of the region that changed between two frames."""
    a = cv2.cvtColor(to_bgr(before), cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(to_bgr(after), cv2.COLOR_BGR2GRAY)
    d = cv2.absdiff(a, b)
    _, m = cv2.threshold(d, thresh, 255, cv2.THRESH_BINARY)
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    pts = cv2.findNonZero(m)
    if pts is None:
        return None
    x, y, w, h = cv2.boundingRect(pts)
    return int(x), int(y), int(w), int(h)


def band_change(before, after, x0, x1, y, h, table_top, table_bottom, thresh: int = 28):
    """How a change is distributed over a table.

    Returns (cover, outside): the share of the row band's width that changed,
    and the share of the rest of the table that changed. A selected row
    gives high cover and near-zero outside; a dialog or backdrop over the
    screen changes the rest of the table too.
    """
    a = cv2.cvtColor(to_bgr(before), cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(to_bgr(after), cv2.COLOR_BGR2GRAY)
    m = cv2.absdiff(a, b) > thresh
    x0, x1 = int(max(0, x0)), int(min(m.shape[1], x1))
    y0, y1 = int(max(0, y - h / 2)), int(min(m.shape[0], y + h / 2))
    band = m[y0:y1, x0:x1]
    cover = float(band.any(axis=0).mean()) if band.size else 0.0
    t0, t1 = int(max(0, table_top)), int(min(m.shape[0], table_bottom))
    rest = np.concatenate([m[t0:y0, x0:x1].ravel(), m[y1:t1, x0:x1].ravel()])
    outside = float(rest.mean()) if rest.size else 0.0
    return cover, outside
