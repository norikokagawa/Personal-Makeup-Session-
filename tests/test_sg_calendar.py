import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from PIL import Image, ImageDraw  # noqa: E402
from sg_calendar import canva_doc as C, images, ledger as L  # noqa: E402
from sg_calendar.run_daily import already_posted, planned_posts, publish_time  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
BEFORE = C.snapshot(json.loads((FIX / "canva_copy_before.json").read_text()))
AFTER = C.snapshot(json.loads((FIX / "canva_copy_after.json").read_text()))
SGT = ZoneInfo("Asia/Singapore")
PERIOD = ("2026-11-06", "2026-11-30")


def mail(no, day, time, received, subject="[STORES 予約] 予約が入りました", service=L.SERVICE):
    body = (f"◆予約番号:\n  {no}\n\n◆予約内容:\n  {service}\n\n"
            f"◆予約日時:\n  2026年11月{day}日 (日) {time} ~ 11:50\n")
    return L.parse_message(f"m{no}{received}", received, subject, body)


def change(no, new_day, new_time, old_day, old_time, received):
    body = (f"[ 変更後 ]\n◆予約番号:\n  {no}\n◆予約内容:\n  {L.SERVICE}\n"
            f"◆予約日時:\n  2026年11月{new_day}日 (水) {new_time} ~\n\n[ 変更前 ]\n"
            f"◆予約日時:\n  2026年11月{old_day}日 (日) {old_time} ~\n")
    return L.parse_message(f"c{no}{received}", received, "[STORES 予約] X 様の予約が変更されました", body)


def matching_mails(snap):
    """Booking mails for exactly the struck cells of the snapshot."""
    slots = [(d, t) for d, ts in C.booked_slots(C.grid(snap)).items() for t in ts]
    return [mail(str(1000 + i), int(d[-2:]), t, "2026-10-01T00:00:00Z") for i, (d, t) in enumerate(slots)]


def ledger_matching(snap):
    return L.build_ledger(matching_mails(snap), *PERIOD)


class LedgerTest(unittest.TestCase):
    def test_parses_real_booking_format(self):
        ev = mail("136683000", 15, "11:00", "2026-10-11T14:46:15Z")
        self.assertEqual((ev.kind, ev.reservation_no, ev.slot),
                         (L.KIND_BOOKED, "136683000", ("2026-11-15", "11:00")))

    def test_duplicate_notification_counts_once(self):
        lg = L.build_ledger([mail("1", 6, "11:00", "2026-10-01T00:00:00Z"),
                             mail("1", 6, "11:00", "2026-10-01T00:05:00Z")], *PERIOD)
        self.assertEqual(lg.booked_slots(), {"2026-11-06": ["11:00"]})
        self.assertEqual(lg.anomalies, [])

    def test_inquiry_is_pending_not_applied(self):
        lg = L.build_ledger([mail("1", 15, "11:00", "2026-10-11T14:46:15Z"),
                             L.parse_message("q", "2026-10-11T14:52:18Z", "X さんからお問い合わせがあります",
                                             "Could I change my appointment to 11 Nov?")], *PERIOD)
        self.assertEqual(lg.booked_slots(), {"2026-11-15": ["11:00"]})
        self.assertEqual(L.pending_request_ids(lg), ["q"])

    def test_change_releases_old_slot_and_cancel(self):
        lg = L.build_ledger([mail("1", 6, "11:00", "2026-10-01T00:00:00Z"),
                             mail("2", 15, "12:00", "2026-10-01T00:00:00Z"),
                             change("2", 11, "13:00", 15, "12:00", "2026-10-02T00:00:00Z"),
                             mail("1", 6, "11:00", "2026-10-03T00:00:00Z",
                                  subject="[STORES 予約] 予約がキャンセルされました")], *PERIOD)
        self.assertEqual(lg.booked_slots(), {"2026-11-11": ["13:00"]})
        self.assertEqual(lg.reservations["2"]["released"], [("2026-11-15", "12:00")])
        self.assertEqual(lg.reservations["1"]["state"], "cancelled")

    def test_unknown_states_are_anomalies(self):
        lg = L.build_ledger([mail("9", 6, "11:00", "2026-10-01T00:00:00Z",
                                  subject="[STORES 予約] 予約がキャンセルされました"),
                             mail("3", 7, "12:00", "2026-10-01T00:00:00Z"),
                             mail("4", 7, "12:00", "2026-10-01T00:00:00Z")], *PERIOD)
        self.assertEqual(len(lg.anomalies), 2)

    def test_json_round_trip(self):
        lg = L.build_ledger([mail("1", 6, "11:00", "2026-10-01T00:00:00Z")], *PERIOD)
        data = L.to_json(lg)
        again = L.to_json(L.from_json(json.loads(json.dumps(data))))
        self.assertEqual(L.fingerprint(data), L.fingerprint(again))


class CanvaTest(unittest.TestCase):
    def test_grid_reads_both_pages(self):
        g = C.grid(BEFORE)
        self.assertEqual(sorted(g), ["2026-11-06", "2026-11-07", "2026-11-08", "2026-11-10", "2026-11-11",
                                     "2026-11-12", "2026-11-14", "2026-11-15", "2026-11-18", "2026-11-19",
                                     "2026-11-21", "2026-11-22", "2026-11-24", "2026-11-28", "2026-11-29"])
        for d, cells in g.items():
            weekend = datetime.strptime(d, "%Y-%m-%d").weekday() >= 5
            self.assertEqual(len(cells), 6 if weekend else 4, d)
        self.assertEqual(g["2026-11-29"]["11:00"]["page"], 2)

    def test_matching_ledger_needs_no_ops(self):
        p = C.plan(ledger_matching(BEFORE), C.grid(BEFORE))
        self.assertEqual((p["ops"], p["blockers"]), ({}, []))

    def test_new_booking_strikes_only_that_cell(self):
        lg = L.build_ledger(matching_mails(BEFORE) + [mail("9999", 15, "11:00", "2026-10-02T00:00:00Z")],
                            *PERIOD)
        p = C.plan(lg, C.grid(BEFORE))
        self.assertEqual(p["strike"], [("2026-11-15", "11:00")])
        self.assertEqual(p["ops"], {1: [{"type": "format_text",
                                         "locator_id": "PBHB5tM9wW3v89p4-LBhp08b4JQVkJzbS-CBMVJcDXbYyRw1wG",
                                         "formatting": C.BOOKED}]})

    def test_struck_without_booking_is_kept_as_manual(self):
        lg = L.build_ledger([], *PERIOD)
        p = C.plan(lg, C.grid(BEFORE))
        self.assertEqual(p["unstrike"], [])
        self.assertIn(("2026-11-08", "17:00"), p["keep_manual"])

    def test_cancelled_booking_is_reopened_unless_manual(self):
        evs = [mail("5555", 29, "11:00", "2026-10-01T00:00:00Z"),
               mail("5555", 29, "11:00", "2026-10-02T00:00:00Z", subject="[STORES 予約] 予約がキャンセルされました")]
        p = C.plan(L.build_ledger(evs, *PERIOD), C.grid(BEFORE))
        self.assertIn(("2026-11-29", "11:00"), p["unstrike"])
        p = C.plan(L.build_ledger(evs, *PERIOD), C.grid(BEFORE), manual_closed=[["2026-11-29", "11:00"]])
        self.assertNotIn(("2026-11-29", "11:00"), p["unstrike"])

    def test_blockers(self):
        evs = [mail("7001", 16, "11:00", "2026-10-01T00:00:00Z"),         # 16日はデザインにない
               mail("7002", 7, "14:00", "2026-10-01T00:00:00Z")]          # 土曜 14:00 枠なし
        self.assertEqual(len(C.plan(L.build_ledger(evs, *PERIOD), C.grid(BEFORE))["blockers"]), 2)

    def test_verify_accepts_planned_and_rejects_anything_else(self):
        ops = {1: [{"type": "format_text", "locator_id": "PBHB5tM9wW3v89p4-LBhp08b4JQVkJzbS-CBMVJcDXbYyRw1wG",
                    "formatting": C.BOOKED}],
               2: [{"type": "format_text", "locator_id": "PBj2PhcBGdkDymdm-LBqlMKLtxn2d6cDB-CBqpCklZm1Xpr1r9",
                    "formatting": C.OPEN}]}
        self.assertEqual(C.verify(BEFORE, AFTER, ops), [])
        self.assertEqual(len(C.verify(BEFORE, AFTER, {})), 2)
        tampered = json.loads(json.dumps(AFTER))
        tampered["pages"][1]["rows"][2][0]["weight"] = "normal"
        self.assertTrue(any("font" in p for p in C.verify(BEFORE, tampered, ops)))


class ImageTest(unittest.TestCase):
    def _feed(self, tmp, edge_mark=False):
        p = Path(tmp, "f.png")
        im = Image.new("RGB", images.FEED_SIZE, images.DESIGN_BG)
        ImageDraw.Draw(im).rectangle((100, 400, 980, 1100), outline=(84, 84, 84))
        if edge_mark:
            ImageDraw.Draw(im).rectangle((0, 600, 30, 700), fill=(84, 84, 84))
        im.save(p)
        return p

    def test_story_keeps_full_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed, story = self._feed(tmp), Path(tmp, "s.png")
            images.verify_feed(feed)
            images.make_story(feed, story)
            with Image.open(story) as s:
                self.assertEqual(s.size, (1080, 1920))

    def test_thumbnail_and_cut_text_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            thumb = Path(tmp, "t.png")
            Image.new("RGB", (400, 500), images.DESIGN_BG).save(thumb)
            with self.assertRaises(ValueError):
                images.verify_feed(thumb)
            with self.assertRaises(ValueError):
                images.verify_feed(self._feed(tmp, edge_mark=True))


class ScheduleTest(unittest.TestCase):
    def test_publish_time(self):
        self.assertEqual(publish_time(datetime(2026, 11, 1, 4, 40, tzinfo=SGT)).strftime("%H:%M"), "05:00")
        self.assertEqual(publish_time(datetime(2026, 11, 1, 5, 12, tzinfo=SGT)).strftime("%H:%M"), "05:20")

    def test_three_independent_posts(self):
        self.assertEqual([(k, t, p) for k, t, p, _ in planned_posts()],
                         [("FEED", "POST", [1, 2]), ("STORY_1", "STORY", [1]), ("STORY_2", "STORY", [2])])

    def test_same_day_duplicates(self):
        story = {"providers": [{"network": "instagram"}], "instagramData": {"type": "STORY"}}
        self.assertTrue(already_posted("STORY_1", "STORY", [story], {}))
        self.assertFalse(already_posted("STORY_2", "STORY", [story], {}))
        self.assertFalse(already_posted("FEED", "POST", [story], {}))
        self.assertTrue(already_posted("FEED", "POST", [], {"FEED": {"metricool_id": 7}}))


if __name__ == "__main__":
    unittest.main()
