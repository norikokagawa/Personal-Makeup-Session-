import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from PIL import Image  # noqa: E402
from sg_calendar import images, ledger as L  # noqa: E402
from sg_calendar.run_daily import already_posted, publish_time  # noqa: E402

GRID = json.loads((ROOT / "config" / "sg_nov_page1.json").read_text())
SGT = ZoneInfo("Asia/Singapore")


def booking(no, date_jp, time, received, subject="[STORES 予約] 予約が入りました",
            service=L.SERVICE):
    body = (f"◆予約番号:\n  {no}\n\n◆予約内容:\n  {service}\n\n"
            f"◆予約日時:\n  {date_jp} (日) {time} ~ 11:50\n")
    return L.parse_message(f"m{no}{received}", received, subject, body)


class LedgerTest(unittest.TestCase):
    def test_parses_real_booking_format(self):
        ev = booking("136683000", "2026年11月15日", "11:00", "2026-10-11T14:46:15Z")
        self.assertEqual(ev.kind, L.KIND_BOOKED)
        self.assertEqual(ev.reservation_no, "136683000")
        self.assertEqual(ev.slot, ("2026-11-15", "11:00"))

    def test_duplicate_notification_counts_once(self):
        evs = [booking("1", "2026年11月6日", "11:00", "2026-10-01T00:00:00Z"),
               booking("1", "2026年11月6日", "11:00", "2026-10-01T00:05:00Z")]
        lg = L.build_ledger(evs, "2026-11-06", "2026-11-30")
        self.assertEqual(lg.booked_slots(), {"2026-11-06": ["11:00"]})
        self.assertEqual(lg.anomalies, [])

    def test_inquiry_does_not_change_reservation(self):
        evs = [booking("1", "2026年11月15日", "11:00", "2026-10-11T14:46:15Z"),
               L.parse_message("q", "2026-10-11T14:52:18Z", "X さんからお問い合わせがあります",
                               "Could I change my appointment to 11 Nov?")]
        lg = L.build_ledger(evs, "2026-11-06", "2026-11-30")
        self.assertEqual(lg.booked_slots(), {"2026-11-15": ["11:00"]})
        self.assertEqual(len(lg.inquiries), 1)

    def test_change_and_cancel_by_reservation_number(self):
        change_body = ("[ 変更後 ]\n◆予約番号:\n  2\n◆予約内容:\n  " + L.SERVICE +
                       "\n◆予約日時:\n  2026年11月11日 (水) 13:00 ~ 13:50\n")
        evs = [booking("1", "2026年11月6日", "11:00", "2026-10-01T00:00:00Z"),
               booking("2", "2026年11月7日", "12:00", "2026-10-01T00:00:00Z"),
               L.parse_message("c2", "2026-10-02T00:00:00Z", "[STORES 予約] Y 様の予約が変更されました",
                               change_body),
               booking("1", "2026年11月6日", "11:00", "2026-10-03T00:00:00Z",
                       subject="[STORES 予約] 予約がキャンセルされました")]
        lg = L.build_ledger(evs, "2026-11-06", "2026-11-30")
        self.assertEqual(lg.booked_slots(), {"2026-11-11": ["13:00"]})

    def test_unknown_states_are_anomalies(self):
        evs = [booking("9", "2026年11月6日", "11:00", "2026-10-01T00:00:00Z",
                       subject="[STORES 予約] 予約がキャンセルされました"),
               booking("3", "2026年11月7日", "12:00", "2026-10-01T00:00:00Z"),
               booking("4", "2026年11月7日", "12:00", "2026-10-01T00:00:00Z")]
        lg = L.build_ledger(evs, "2026-11-06", "2026-11-30")
        self.assertEqual(len(lg.anomalies), 2)

    def test_other_services_and_periods_ignored(self):
        evs = [booking("5", "2026年11月6日", "11:00", "2026-10-01T00:00:00Z", service="【東京】オフ会"),
               booking("6", "2026年10月10日", "11:00", "2026-10-01T00:00:00Z")]
        lg = L.build_ledger(evs, "2026-11-06", "2026-11-30")
        self.assertEqual(lg.booked_slots(), {})


class DiffTest(unittest.TestCase):
    def _ledger(self, slots):
        evs = [booking(str(i), f"2026年11月{int(d[-2:])}日", t, "2026-10-01T00:00:00Z")
               for i, (d, t) in enumerate(slots)]
        return L.build_ledger(evs, "2026-11-06", "2026-11-30")

    def test_matching_ledger_has_no_diff(self):
        slots = [(d, t) for d, ts in GRID["approved_booked"].items() for t in ts]
        self.assertEqual(L.diff_against_design(self._ledger(slots), GRID), ([], [], []))

    def test_new_booking_needs_strike(self):
        slots = [(d, t) for d, ts in GRID["approved_booked"].items() for t in ts]
        slots.append(("2026-11-15", "11:00"))
        strike, unstrike, unknown = L.diff_against_design(self._ledger(slots), GRID)
        self.assertEqual(strike, [("2026-11-15", "11:00")])
        self.assertEqual((unstrike, unknown), ([], []))

    def test_booking_at_time_without_cell_is_unknown(self):
        slots = [(d, t) for d, ts in GRID["approved_booked"].items() for t in ts]
        slots.append(("2026-11-07", "14:00"))   # 土曜は 14:00 枠なし
        self.assertEqual(L.diff_against_design(self._ledger(slots), GRID)[2],
                         [("2026-11-07", "14:00")])

    def test_grid_slot_counts(self):
        for d, cells in GRID["cells"].items():
            weekend = datetime.strptime(d, "%Y-%m-%d").weekday() >= 5
            self.assertEqual(len(cells), 6 if weekend else 4, d)


class ImageTest(unittest.TestCase):
    def test_story_keeps_full_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed, story = Path(tmp, "f.png"), Path(tmp, "s.png")
            im = Image.new("RGB", images.FEED_SIZE, images.DESIGN_BG)
            im.putpixel((0, 0), (255, 0, 0))
            im.putpixel((1079, 1349), (0, 0, 255))
            im.save(feed)
            images.verify_feed(feed)
            images.make_story(feed, story)
            with Image.open(story) as s:
                self.assertEqual(s.size, (1080, 1920))
                self.assertEqual(s.getpixel((0, 285)), (255, 0, 0))
                self.assertEqual(s.getpixel((1079, 285 + 1349)), (0, 0, 255))

    def test_thumbnail_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, "t.png")
            Image.new("RGB", (400, 500), (1, 2, 3)).save(p)
            with self.assertRaises(ValueError):
                images.verify_feed(p)


class ScheduleTest(unittest.TestCase):
    def test_before_five_uses_five(self):
        t = publish_time(datetime(2026, 11, 1, 4, 30, tzinfo=SGT))
        self.assertEqual((t.hour, t.minute), (5, 0))

    def test_late_run_uses_nearest_time(self):
        t = publish_time(datetime(2026, 11, 1, 5, 12, tzinfo=SGT))
        self.assertEqual((t.hour, t.minute), (5, 20))

    def test_same_day_duplicate_detection(self):
        existing = [{"providers": [{"network": "instagram"}], "instagramData": {"type": "STORY"}}]
        self.assertTrue(already_posted(existing, {}, "STORY"))
        self.assertFalse(already_posted(existing, {}, "POST"))
        self.assertTrue(already_posted([], {"POST": {"metricool_id": 1}}, "POST"))


if __name__ == "__main__":
    unittest.main()
