#!/usr/bin/env python3
"""
One-page December design (page 5): draws the two master images that the daily run composes from.

  open_p5.png   : every time slot available (dark grey)
  booked_p5.png : every time slot booked (deep red + strikethrough)

The two images are identical except inside the time-slot text, exactly like the Canva masters
of pages 1-4, so compose.py finds each slot from their difference. Page 5 shows the slots of
pages 3 and 4 (December, minus REMOVED_DATES) as two equal blocks of dates; its layout entry is written from them.
Run this only when the design or the December dates/times change:

  python3 scripts/sg_calendar/month_master.py            # writes assets/sg_masters/*_p5.png + layout

Fonts: Cormorant Garamond (assets/fonts, OFL) and Inter (system font, `fonts-inter`; set
INTER_FONT_DIR if it is elsewhere). The daily run does not need the fonts, only the PNGs.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
LAYOUT = ROOT / "config" / "sg_layout.json"
MASTERS = ROOT / "assets" / "sg_masters"
CORMORANT = ROOT / "assets" / "fonts" / "CormorantGaramond-wght.ttf"
INTER_DIR = Path(os.environ.get("INTER_FONT_DIR", "/usr/share/fonts/opentype/inter"))

PAGE, SOURCE_PAGES = 5, (3, 4)
REMOVED_DATES = {"2026-12-10", "2026-12-17"}   # taken off the calendar (no sessions)
EXTRA_SLOTS = [{"date": "2026-12-01", "time": "15:00", "row": 4}]   # booked outside the original times
SIZE = (1080, 1350)
BG = (244, 243, 239)
INK, SOFT, RULE = (92, 88, 84), (140, 134, 127), (222, 218, 211)
RED = (150, 58, 52)            # booked slots and Sundays
DATE, TIME = (88, 84, 80), (60, 57, 54)
LEFT, RIGHT, TOP, BLOCK_GAP, STEP, ROWS_PER_BLOCK = 115, 965, 380, 70, 58, 5


def cormorant(size, weight):
    f = ImageFont.truetype(str(CORMORANT), size)
    f.set_variation_by_axes([weight])
    return f


def inter(size, style):
    return ImageFont.truetype(str(INTER_DIR / f"Inter-{style}.otf"), size)


def display_time(t):
    h, m = map(int, t.split(":"))
    return f"{h - 12 if h > 12 else h}:{m:02d}"


def spaced(d, cx, y, text, font, fill, track, features=None):
    """Letter-spaced text centred on cx; returns its width."""
    widths = [d.textlength(c, font=font, features=features) for c in text]
    total = sum(widths) + track * (len(text) - 1)
    x = cx - total / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=font, fill=fill, features=features)
        x += w + track
    return total


def blocks(layout):
    """[(dates, slots)] for the two blocks: the December dates of pages 3-4 minus REMOVED_DATES,
    split evenly (first half on top). Each slot keeps its time row from pages 3-4."""
    slots = [s for pg in layout["pages"] if pg["page"] in SOURCE_PAGES for s in pg["slots"]
             if s["date"] not in REMOVED_DATES]
    for extra in EXTRA_SLOTS:
        if any(s["date"] == extra["date"] and s["row"] == extra["row"] for s in slots):
            raise ValueError(f"extra slot {extra} collides with an existing time on that date")
        slots.append(extra)
    dates = sorted({s["date"] for s in slots})
    if len(dates) % 2:
        raise ValueError(f"{len(dates)} dates cannot be split into two equal blocks")
    half = len(dates) // 2
    out = []
    for part in (dates[:half], dates[half:]):
        mine = [s for s in slots if s["date"] in part]
        if max(s["row"] for s in mine) >= ROWS_PER_BLOCK:
            raise ValueError(f"more than {ROWS_PER_BLOCK} times on one date")
        out.append((part, mine))
    return out


def page_layout(layout):
    """Layout entry for page 5: block 1 rows 0-4, block 2 rows 5-9, one column per date."""
    slots = []
    for bi, (dates, mine) in enumerate(blocks(layout)):
        slots += [{"date": s["date"], "time": s["time"], "row": s["row"] + bi * ROWS_PER_BLOCK,
                   "col": dates.index(s["date"])} for s in mine]
    rows_used = max(s["row"] for s in slots) + 1
    return {"page": PAGE, "columns": len(blocks(layout)[0][0]), "time_rows": rows_used,
            "slots": sorted(slots, key=lambda s: (s["row"], s["col"]))}


def draw(layout, booked_style):
    img = Image.new("RGB", SIZE, BG)
    d = ImageDraw.Draw(img)
    months = sorted({s["date"][:7] for _, mine in blocks(layout) for s in mine})
    if len(months) != 1:
        raise ValueError(f"page {PAGE} must show one month, got {months}")
    title = dt.date.fromisoformat(months[0] + "-01").strftime("%B  %Y").upper()
    spaced(d, 540, 132, "SINGAPORE", cormorant(60, 400), INK, 24)
    d.line([(495, 222), (585, 222)], fill=RULE, width=1)
    spaced(d, 540, 244, title, cormorant(24, 500), SOFT, 8, ["lnum"])
    bl = blocks(layout)
    cw = (RIGHT - LEFT) / len(bl[0][0])
    for bi, (dates, mine) in enumerate(bl):
        y0 = TOP + bi * (102 + ROWS_PER_BLOCK * STEP + BLOCK_GAP)
        for ci, ds in enumerate(dates):
            cx, day = LEFT + cw * (ci + 0.5), dt.date.fromisoformat(ds)
            sunday = day.weekday() == 6
            spaced(d, cx, y0, day.strftime("%a").upper(), inter(12, "Regular"), RED if sunday else SOFT, 3.5)
            spaced(d, cx, y0 + 27, str(day.day), cormorant(30, 400), RED if sunday else DATE, 1, ["lnum"])
        d.line([(LEFT + 20, y0 + 80), (RIGHT - 20, y0 + 80)], fill=RULE, width=1)
        for s in mine:
            cx = LEFT + cw * (dates.index(s["date"]) + 0.5)
            ty = y0 + 102 + s["row"] * STEP
            col = RED if booked_style else TIME
            w = spaced(d, cx, ty, display_time(s["time"]), inter(19, "ExtraLight"), col, 2.4)
            if booked_style:
                d.line([(cx - w / 2 - 4, ty + 12), (cx + w / 2 + 4, ty + 12)], fill=col, width=1)
    return img


def main():
    layout = json.loads(LAYOUT.read_text())
    draw(layout, False).save(MASTERS / f"open_p{PAGE}.png")
    draw(layout, True).save(MASTERS / f"booked_p{PAGE}.png")
    entry = page_layout(layout)
    layout["pages"] = [pg for pg in layout["pages"] if pg["page"] != PAGE] + [entry]
    LAYOUT.write_text(json.dumps(layout, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote open/booked_p{PAGE}.png and layout page {PAGE} ({len(entry['slots'])} slots)")


if __name__ == "__main__":
    sys.exit(main())
