"""
Canva カレンダー (1・2ページ目) の読み取り・更新計画・検証

Canva の公開 REST API (Connect API) には要素単位の編集がないため、横線の更新は
Canva MCP の編集トランザクション (read-design → edit-design format_text → commit) で行う。
このモジュールはその前後のドキュメントを機械的に扱う:

  snapshot   : read-design の design_content (または同じ形の簡易スナップショット) → セル一覧
  grid       : 日付行・時刻セルの文字から {date: {time: cell}} を組み立てる (ロケーターを固定しない)
  plan       : 台帳 + 現在の横線 → format_text 操作と停止理由
  verify     : 更新前後を比較し、計画したセルの線と色以外が1つも変わっていないことを確認
"""
import re

BOOKED = {"strikethrough": "strikethrough", "color": "#ff5757"}
OPEN = {"strikethrough": "none", "color": "#545454"}
YEAR, MONTH = 2026, 11
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


# ── snapshot ───────────────────────────────────────────────────────────────

def _fmt(cell):
    regions = cell.get("textRegions") or []
    if not regions:
        return {"text": "", "strike": None, "color": None, "weight": None, "size": None, "font": None}
    f = regions[0]["formatting"]
    return {"text": "".join(r["characters"] for r in regions).strip(),
            "strike": f.get("strikethrough"), "color": (f.get("color") or "").lower(),
            "weight": f.get("fontWeight"), "size": f.get("fontSize"), "font": f.get("fontRef"),
            "regions": len(regions)}


def _compact_cell(s):
    """'ID|text|1|#ff5757|light' → cell dict (簡易スナップショット形式)"""
    cid, text, strike, color, weight = (s.split("|") + [""] * 5)[:5]
    if not text:
        return {"id": cid, "text": "", "strike": None, "color": None, "weight": None}
    return {"id": cid, "text": text, "strike": "strikethrough" if strike == "1" else "none",
            "color": color.lower(), "weight": weight}


def snapshot(doc):
    """
    Normalise either the full read-design `design_content` or a compact snapshot
    into {"pages": [{"page_id", "others": [...], "table": {...}, "rows": [[cell]]}]}.
    """
    pages = []
    for p in doc["pages"]:
        if "rows" in p and "elements" not in p:          # compact form
            rows = [[_compact_cell(c) for c in r] for r in p["rows"]]
            pages.append({"page_id": p["page_id"], "table_id": p["table_id"],
                          "others": p.get("others", []), "rows": rows})
            continue
        table, others = None, []
        for el in p["elements"]:
            if el["type"] == "table":
                if table is not None:
                    raise ValueError(f"page {p['id']}: more than one table")
                table = el
            else:
                text = "".join(r["characters"] for r in el.get("textRegions", []))
                others.append({k: el.get(k) for k in ("id", "type", "top", "left", "width",
                                                      "height", "rotation", "opacity")} | {"text": text})
        if table is None:
            raise ValueError(f"page {p['id']}: no table")
        rows = [[{"id": c["id"], **_fmt(c)} for c in r["cells"]] for r in table["rows"]]
        pages.append({"page_id": p["id"], "table_id": table["id"],
                      "table_box": {k: table.get(k) for k in ("top", "left", "width", "height")},
                      "others": others, "rows": rows})
    return {"pages": pages}


def locator(page, cell):
    return f"{page['page_id']}-{page['table_id']}-{cell['id']}"


# ── grid ───────────────────────────────────────────────────────────────────

def to_24h(text):
    m = _TIME_RE.match(text)
    if not m:
        return None
    h = int(m.group(1))
    if h < 10:              # デザイン上は午後を 1:00〜5:00 と表記
        h += 12
    return f"{h:02d}:{m.group(2)}"


def cell_state(cell):
    if cell["strike"] == "strikethrough" and cell["color"] == BOOKED["color"]:
        return "booked"
    if cell["strike"] == "none" and cell["color"] == OPEN["color"]:
        return "open"
    return "unknown"


def grid(snap):
    """{date: {time: {"page", "locator", "state", "cell"}}}; raises on anything ambiguous."""
    out = {}
    for pi, page in enumerate(snap["pages"], start=1):
        rows = page["rows"]
        if len(rows) < 3:
            raise ValueError(f"page {pi}: table too small")
        dates = []
        for c in rows[1]:
            if not c["text"].isdigit():
                raise ValueError(f"page {pi}: date cell '{c['text']}' is not a day number")
            dates.append(f"{YEAR}-{MONTH:02d}-{int(c['text']):02d}")
        for r in rows[2:]:
            if len(r) != len(dates):
                raise ValueError(f"page {pi}: row width {len(r)} != {len(dates)} dates")
            for d, c in zip(dates, r):
                if not c["text"]:
                    continue
                t = to_24h(c["text"])
                if t is None:
                    raise ValueError(f"page {pi}: cannot read time '{c['text']}'")
                day = out.setdefault(d, {})
                if t in day:
                    raise ValueError(f"{d} {t} appears twice in the design")
                day[t] = {"page": pi, "locator": locator(page, c), "state": cell_state(c), "cell": c}
    return out


# ── plan ───────────────────────────────────────────────────────────────────

def plan(ledger, g, manual_closed=(), acknowledged_inquiries=()):
    """
    Returns {"strike": [...], "unstrike": [...], "keep_manual": [...], "blockers": [...],
             "ops": {page: [format_text op, ...]}}

    - 確定予約 (台帳で有効) の枠 → 赤+取り消し線
    - 台帳でキャンセル/日程変更により空いた枠 → 灰色 (manual_closed に入っていなければ)
    - 予約記録のない取り消し線 → 手動閉鎖とみなし、そのまま
    """
    from sg_calendar.ledger import pending_request_ids
    blockers = list(ledger.anomalies)
    for mid in pending_request_ids(ledger):
        if mid not in acknowledged_inquiries:
            blockers.append(f"unconfirmed change/cancel request in mail {mid}")

    lo, hi = ledger.period
    active = {}
    for no, r in ledger.reservations.items():
        if r["state"] != "cancelled" and lo <= r["slot"][0] <= hi:
            active.setdefault(tuple(r["slot"]), []).append(no)
    released = set()
    for r in ledger.reservations.values():
        for s in r.get("released", []):
            released.add(tuple(s))
        if r["state"] == "cancelled":
            released.add(tuple(r["slot"]))

    for (d, t) in sorted(active):
        if t not in g.get(d, {}):
            blockers.append(f"booking at {d} {t} has no cell on pages 1-2")
    for d, times in g.items():
        for t, c in times.items():
            if c["state"] == "unknown":
                blockers.append(f"{d} {t}: cell style is neither booked nor open")

    strike, unstrike, keep = [], [], []
    manual = {tuple(m) for m in manual_closed}
    for d in sorted(g):
        for t in sorted(g[d]):
            c, key = g[d][t], (d, t)
            if key in active and c["state"] == "open":
                strike.append((d, t, c))
            elif key not in active and c["state"] == "booked":
                if key in released and key not in manual:
                    unstrike.append((d, t, c))
                else:
                    keep.append((d, t))

    ops = {}
    for d, t, c in strike:
        ops.setdefault(c["page"], []).append(
            {"type": "format_text", "locator_id": c["locator"], "formatting": dict(BOOKED)})
    for d, t, c in unstrike:
        ops.setdefault(c["page"], []).append(
            {"type": "format_text", "locator_id": c["locator"], "formatting": dict(OPEN)})
    return {"strike": [(d, t) for d, t, _ in strike], "unstrike": [(d, t) for d, t, _ in unstrike],
            "keep_manual": keep, "blockers": blockers, "ops": ops}


# ── verify ─────────────────────────────────────────────────────────────────

def verify(before, after, ops):
    """
    Return a list of problems (empty = safe to commit).
    Allowed differences: only strike/color of the cells named in ops, to exactly the target style.
    """
    problems = []
    target = {op["locator_id"]: op["formatting"] for p in ops.values() for op in p}
    if len(before["pages"]) != len(after["pages"]):
        return ["page count changed"]
    for pb, pa in zip(before["pages"], after["pages"]):
        if pb["page_id"] != pa["page_id"] or pb["table_id"] != pa["table_id"]:
            problems.append(f"page/table id changed on {pb['page_id']}")
            continue
        if pb.get("others") != pa.get("others"):
            problems.append(f"{pb['page_id']}: non-table elements changed")
        if pb.get("table_box") != pa.get("table_box"):
            problems.append(f"{pb['page_id']}: table position/size changed")
        if [len(r) for r in pb["rows"]] != [len(r) for r in pa["rows"]]:
            problems.append(f"{pb['page_id']}: table shape changed")
            continue
        for rb, ra in zip(pb["rows"], pa["rows"]):
            for cb, ca in zip(rb, ra):
                loc = locator(pb, cb)
                want = target.pop(loc, None)
                fixed = {k: v for k, v in cb.items() if k not in ("strike", "color")}
                if fixed != {k: v for k, v in ca.items() if k not in ("strike", "color")}:
                    problems.append(f"{loc}: text/font/size/weight changed")
                if want is None:
                    if (cb["strike"], cb["color"]) != (ca["strike"], ca["color"]):
                        problems.append(f"{loc}: unplanned style change")
                elif (ca["strike"], ca["color"]) != (want["strikethrough"], want["color"]):
                    problems.append(f"{loc}: expected {want}, got {ca['strike']} {ca['color']}")
    for loc in target:
        problems.append(f"{loc}: planned cell not found")
    return problems


def booked_slots(g):
    return {d: sorted(t for t, c in times.items() if c["state"] == "booked") for d, times in g.items()}
