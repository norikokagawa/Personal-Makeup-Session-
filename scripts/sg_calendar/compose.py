"""
Build the day's calendar pages from two fixed master images, without calling Canva.

  open master   : every slot gray, no strikethrough   (Canva copy DAHX1S2EPR0)
  booked master : every slot red + strikethrough      (Canva copy DAHX1QJavPQ)

The masters differ only inside the time-slot text. Each slot's box is found from
that difference, matched to config/sg_layout.json (which cell is which date/time),
and the booked master's pixels are copied into the open master for booked slots.
Anything that does not line up exactly raises, so a wrong image is never produced.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / "config" / "sg_layout.json"


class ComposeError(Exception):
    pass


def load_layout(path=LAYOUT):
    return json.loads(Path(path).read_text())


def _arr(im):
    return np.asarray(im.convert("RGB"), dtype=np.int16)


def _runs(mask_1d, max_gap):
    """[start, end) runs of True, joining gaps shorter than max_gap."""
    idx = np.flatnonzero(mask_1d)
    if not idx.size:
        return []
    runs, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > max_gap:
            runs.append((start, prev + 1))
            start = i
        prev = i
    runs.append((start, prev + 1))
    return runs


def slot_boxes(open_im, booked_im, page_layout):
    """{(date, time): (x0, y0, x1, y1)} for one page; raises unless it matches the layout exactly."""
    if open_im.size != booked_im.size:
        raise ComposeError(f"master sizes differ: {open_im.size} vs {booked_im.size}")
    w, h = open_im.size
    diff = np.any(_arr(open_im) != _arr(booked_im), axis=2)
    gap_x, gap_y = max(2, w // 50), max(2, h // 60)
    cols = _runs(diff.any(axis=0), gap_x)
    if len(cols) != page_layout["columns"]:
        raise ComposeError(f"page {page_layout['page']}: found {len(cols)} slot columns, "
                           f"layout has {page_layout['columns']}")
    rows = _runs(diff.any(axis=1), gap_y)
    if len(rows) != page_layout["time_rows"]:
        raise ComposeError(f"page {page_layout['page']}: found {len(rows)} slot rows, "
                           f"layout has {page_layout['time_rows']}")

    found = {}
    for ri, (y0, y1) in enumerate(rows):
        for ci, (x0, x1) in enumerate(cols):
            cell = diff[y0:y1, x0:x1]
            if not cell.any():
                continue
            ys, xs = np.nonzero(cell)
            found[(ri, ci)] = (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1)
    expected = {(s["row"], s["col"]): (s["date"], s["time"]) for s in page_layout["slots"]}
    if set(found) != set(expected):
        raise ComposeError(f"page {page_layout['page']}: slot cells differ from layout "
                           f"(extra {sorted(set(found) - set(expected))}, "
                           f"missing {sorted(set(expected) - set(found))})")

    # a little padding for anti-aliased edges, never reaching a neighbouring slot
    pad = max(1, w // 360)
    boxes = {}
    for (ri, ci), (x0, y0, x1, y1) in found.items():
        boxes[expected[(ri, ci)]] = (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))
    keys = list(boxes)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            A, B = boxes[a], boxes[b]
            if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
                raise ComposeError(f"slot boxes overlap: {a} {b}")

    outside = diff.copy()
    for x0, y0, x1, y1 in boxes.values():
        outside[y0:y1, x0:x1] = False
    if outside.any():
        ys, xs = np.nonzero(outside)
        raise ComposeError(f"page {page_layout['page']}: masters differ outside the slots "
                           f"near x={xs.min()} y={ys.min()} — re-export the masters")
    return boxes


def compose(open_im, booked_im, boxes, booked):
    """Open master with the booked master's pixels in each slot of `booked` ({(date, time)})."""
    unknown = set(booked) - set(boxes)
    if unknown:
        raise ComposeError(f"booked slots not on this page: {sorted(unknown)}")
    out = open_im.convert("RGB").copy()
    src = booked_im.convert("RGB")
    for key in booked:
        box = boxes[key]
        out.paste(src.crop(box), box[:2])
    return out


def verify(img, open_im, booked_im, boxes, booked):
    """Every slot equals exactly the intended master; everything else equals the open master."""
    a, o, b = _arr(img), _arr(open_im), _arr(booked_im)
    rest = np.ones(a.shape[:2], dtype=bool)
    for key, (x0, y0, x1, y1) in boxes.items():
        want = b if key in booked else o
        if not np.array_equal(a[y0:y1, x0:x1], want[y0:y1, x0:x1]):
            raise ComposeError(f"slot {key} does not match the {'booked' if key in booked else 'open'} style")
        rest[y0:y1, x0:x1] = False
    if not np.array_equal(a[rest], o[rest]):
        raise ComposeError("image differs from the master outside the time slots")


def build_pages(masters_dir, booked, out_dir, layout=None):
    """Write page_1.png / page_2.png for the set of booked (date, time); returns their paths."""
    layout = layout or load_layout()
    masters_dir, out_dir = Path(masters_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    on_pages = set()
    paths = []
    for pl in layout["pages"]:
        n = pl["page"]
        with Image.open(masters_dir / f"open_p{n}.png") as o, Image.open(masters_dir / f"booked_p{n}.png") as b:
            o.load(), b.load()
            boxes = slot_boxes(o, b, pl)
            mine = {k for k in booked if k in boxes}
            on_pages |= mine
            img = compose(o, b, boxes, mine)
            verify(img, o, b, boxes, mine)
        p = out_dir / f"page_{n}.png"
        img.save(p)
        paths.append(p)
    missing = set(booked) - on_pages
    if missing:
        raise ComposeError(f"booked slots that are not on the calendar: {sorted(missing)}")
    return paths
