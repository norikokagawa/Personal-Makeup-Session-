"""
STORES 予約メール → 予約番号単位の台帳

メール1通ずつではなく予約番号ごとに最終状態を決める。
推測はしない: 解釈できないメールや矛盾があれば ``anomalies`` に積み、
呼び出し側はそれを見て更新を停止する。
"""
import hashlib
import json
import re
from dataclasses import dataclass, field

SERVICE = "Personal Makeup Session — Singapore"

KIND_BOOKED = "booked"
KIND_CHANGED = "changed"
KIND_CANCELLED = "cancelled"
KIND_INQUIRY = "inquiry"

_NO_RE = re.compile(r"◆予約番号:\s*(\d+)")
_SERVICE_RE = re.compile(r"◆予約内容:\s*(.+)")
_SLOT_RE = re.compile(
    r"◆予約日時:\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*\([^)]*\)\s*(\d{1,2}):(\d{2})"
)


@dataclass
class Event:
    message_id: str
    received_at: str          # ISO 8601 UTC, used for ordering
    kind: str
    reservation_no: str = None
    service: str = None
    slot: tuple = None        # ("2026-11-15", "11:00")
    previous_slot: tuple = None
    text: str = ""


@dataclass
class Ledger:
    reservations: dict = field(default_factory=dict)  # no -> {"state", "slot", "history"}
    inquiries: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)
    period: tuple = None
    pending_ids: list = None   # from_json() 用。None なら inquiries から判定

    def booked_slots(self, dates=None):
        """{date: sorted [time,...]} of confirmed (not cancelled) reservations."""
        out = {}
        for r in self.reservations.values():
            if r["state"] == KIND_CANCELLED or not r["slot"]:
                continue
            d, t = r["slot"]
            if dates is not None and d not in dates:
                continue
            out.setdefault(d, []).append(t)
        return {d: sorted(ts) for d, ts in out.items()}


def classify(subject):
    if "予約が入りました" in subject:
        return KIND_BOOKED
    if "予約が変更されました" in subject:
        return KIND_CHANGED
    if "予約がキャンセルされました" in subject:
        return KIND_CANCELLED
    if "お問い合わせがあります" in subject:
        return KIND_INQUIRY
    return None


def _slots(body):
    return [
        (f"{y}-{int(m):02d}-{int(d):02d}", f"{int(hh):02d}:{mm}")
        for y, m, d, hh, mm in _SLOT_RE.findall(body)
    ]


def parse_message(message_id, received_at, subject, body):
    """Returns an Event, or None for mail that is not about reservations."""
    kind = classify(subject)
    if kind is None:
        return None
    if kind == KIND_INQUIRY:
        return Event(message_id, received_at, kind, text=body.strip())

    no = _NO_RE.search(body)
    service = _SERVICE_RE.search(body)
    slots = _slots(body)
    ev = Event(
        message_id, received_at, kind,
        reservation_no=no.group(1) if no else None,
        service=service.group(1).strip() if service else None,
    )
    if kind == KIND_CHANGED:
        # 本文は "[ 変更後 ]" が先、"[ 変更前 ]" があればその後に続く
        after, _, before = body.partition("変更前")
        after_slots, before_slots = _slots(after), _slots(before)
        ev.slot = after_slots[0] if after_slots else None
        ev.previous_slot = before_slots[0] if before_slots else None
    else:
        ev.slot = slots[0] if slots else None
    return ev


def build_ledger(events, period_start, period_end):
    """Apply events in received order. Period bounds are 'YYYY-MM-DD' inclusive."""
    ledger = Ledger()
    ledger.period = (period_start, period_end)

    def in_period(slot):
        return slot is not None and period_start <= slot[0] <= period_end

    for ev in sorted(events, key=lambda e: e.received_at):
        if ev.kind == KIND_INQUIRY:
            # 変更・キャンセルの「希望」だけでは台帳を変えない。確認対象として残す
            ledger.inquiries.append(ev)
            continue
        if ev.service and ev.service != SERVICE:
            continue
        if not ev.reservation_no or (ev.kind != KIND_CANCELLED and not ev.slot):
            ledger.anomalies.append(
                f"{ev.message_id}: {ev.kind} mail without reservation number or date")
            continue

        cur = ledger.reservations.get(ev.reservation_no)
        if ev.kind == KIND_BOOKED:
            if cur and cur["state"] != KIND_CANCELLED:
                if cur["slot"] != ev.slot:
                    ledger.anomalies.append(
                        f"{ev.reservation_no}: booked twice with different dates "
                        f"{cur['slot']} / {ev.slot}")
                    continue
                # 同じ通知の重複。台帳は変えない
            ledger.reservations[ev.reservation_no] = {
                "state": KIND_BOOKED, "slot": ev.slot,
                "history": (cur["history"] if cur else []) + [ev.message_id]}
        elif ev.kind == KIND_CHANGED:
            if cur is None and not in_period(ev.slot) and not in_period(ev.previous_slot):
                continue
            if cur is None:
                # 元の予約メールが見つからない変更。変更後の日時は本文で確定しているが、
                # 変更前の枠が分からないと横線を外せないので停止対象にする
                ledger.anomalies.append(
                    f"{ev.reservation_no}: change notice without original booking mail")
            elif ev.previous_slot and cur["slot"] != ev.previous_slot:
                ledger.anomalies.append(
                    f"{ev.reservation_no}: change says previous slot {ev.previous_slot} "
                    f"but ledger has {cur['slot']}")
            released = list(cur.get("released", [])) if cur else []
            if cur and cur["slot"] != ev.slot:
                released.append(cur["slot"])      # 変更前の枠は空く
            ledger.reservations[ev.reservation_no] = {
                "state": KIND_BOOKED, "slot": ev.slot, "released": released,
                "history": (cur["history"] if cur else []) + [ev.message_id]}
        elif ev.kind == KIND_CANCELLED:
            if cur is None:
                if in_period(ev.slot):
                    ledger.anomalies.append(
                        f"{ev.reservation_no}: cancellation for unknown reservation")
                continue
            cur["state"] = KIND_CANCELLED
            cur["history"].append(ev.message_id)

    # 対象期間外の予約は落とす (期間内の枠を空けた変更は残す)
    ledger.reservations = {
        no: r for no, r in ledger.reservations.items()
        if in_period(r["slot"]) or any(in_period(s) for s in r.get("released", []))}

    # 同じ枠に2件以上の有効予約
    seen = {}
    for no, r in ledger.reservations.items():
        if r["state"] == KIND_CANCELLED:
            continue
        if r["slot"] in seen:
            ledger.anomalies.append(
                f"slot {r['slot']} has two active reservations: {seen[r['slot']]}, {no}")
        seen[r["slot"]] = no
    return ledger


_REQUEST_WORDS = ("cancel", "change", "reschedule", "move", "postpone", "キャンセル", "変更")
_PERIOD_WORDS = ("nov", "11月", "11/")


def pending_request_ids(ledger):
    if ledger.pending_ids is not None:
        return list(ledger.pending_ids)
    return [i.message_id for i in pending_requests(ledger)]


def pending_requests(ledger):
    """Inquiries that look like an unconfirmed change/cancel request for the November period."""
    out = []
    for i in ledger.inquiries:
        t = i.text.lower()
        if any(w in t for w in _REQUEST_WORDS) and any(w in t for w in _PERIOD_WORDS):
            out.append(i)
    return out


_NUM_RE = re.compile(r"(?<![\d-])\d{6,}(\d{3})(?![\d-])")


def mask_numbers(text):
    """'136653243' → '***243' (リポジトリは公開なので予約番号をそのまま残さない)."""
    return _NUM_RE.sub(r"***\1", text)


def _key(no):
    if re.fullmatch(r"r[0-9a-f]{12}", no):      # from_json() 由来: すでにハッシュ済み
        return no
    return "r" + hashlib.sha256(no.encode()).hexdigest()[:12]


def to_json(ledger):
    """Serialisable ledger: 枠と状態のみ。予約番号はハッシュ化、氏名・連絡先は含めない。"""
    return {
        "period": list(ledger.period),
        "reservations": {_key(no): {"state": r["state"], "slot": list(r["slot"]),
                                    "released": [list(x) for x in r.get("released", [])]}
                         for no, r in sorted(ledger.reservations.items())},
        "anomalies": [mask_numbers(a) for a in ledger.anomalies],
        "pending_requests": [i.message_id for i in pending_requests(ledger)],
    }


def from_json(data):
    lg = Ledger(period=tuple(data["period"]), anomalies=list(data["anomalies"]))
    lg.reservations = {no: {"state": r["state"], "slot": tuple(r["slot"]),
                            "released": [tuple(x) for x in r.get("released", [])], "history": []}
                       for no, r in data["reservations"].items()}
    lg.pending_ids = list(data["pending_requests"])
    return lg


def fingerprint(data):
    """Stable hash of a to_json() ledger, used to detect new mail between steps."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
