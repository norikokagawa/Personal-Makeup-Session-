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
from sg_calendar.instagram import InstagramError  # noqa: E402
from sg_calendar.post_state import Poster  # noqa: E402
from sg_calendar.run_daily import publish_time  # noqa: E402

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
        late = datetime(2026, 11, 1, 5, 12, tzinfo=SGT)
        self.assertEqual(publish_time(late), late)          # 過ぎていれば直ちに公開


class FakeIG:
    """Instagram stand-in: containers go FINISHED → PUBLISHED; can fail on demand."""

    def __init__(self):
        self.status, self.published, self.n = {}, [], 0
        self.fail_publish = None          # None | "hard" | "network" | "network_after_apply"

    def _new(self):
        self.n += 1
        cid = f"c{self.n}"
        self.status[cid] = "FINISHED"
        return cid

    def container_status(self, cid):
        return self.status[cid]

    def wait_finished(self, cid):
        return self.status[cid]

    def publish(self, cid):
        mode, self.fail_publish = self.fail_publish, None
        if mode == "hard":
            raise InstagramError("rejected")
        if mode == "network":
            raise InstagramError("timeout", ambiguous=True)
        if self.status[cid] == "PUBLISHED":
            raise AssertionError("container published twice")
        self.status[cid] = "PUBLISHED"
        self.published.append(cid)
        if mode == "network_after_apply":
            raise InstagramError("timeout after apply", ambiguous=True)
        return f"m{cid}"

    def disable_comments(self, mid):
        return True


def run_all(poster):
    errors = []
    for key in ("FEED", "STORY_1", "STORY_2"):
        try:
            poster.run_item(key, lambda ig: (ig._new(), None))
        except InstagramError as e:
            errors.append(key)
    return errors


class PostStateTest(unittest.TestCase):
    def setUp(self):
        self.ig, self.saved = FakeIG(), []

    def poster(self, rec, publish=True):
        return Poster(self.ig, rec, lambda r: self.saved.append(json.loads(json.dumps(r))),
                      publish=publish, prepare=True)

    def test_three_independent_posts_and_rerun_is_noop(self):
        rec = {}
        self.assertEqual(run_all(self.poster(rec)), [])
        self.assertEqual(len(self.ig.published), 3)
        self.assertEqual(run_all(self.poster(rec)), [])           # 予備トリガーで再実行
        self.assertEqual(len(self.ig.published), 3)

    def test_state_saved_before_publish_call(self):
        rec = {}
        run_all(self.poster(rec))
        states = [s["items"]["FEED"]["state"] for s in self.saved if "FEED" in s["items"]]
        self.assertEqual(states[:3], ["prepared", "publishing", "published"])

    def test_hard_failure_is_retried_without_duplicates(self):
        rec = {}
        self.ig.fail_publish = "hard"
        self.assertEqual(run_all(self.poster(rec)), ["FEED"])
        self.assertEqual(rec["items"]["FEED"]["state"], "failed")
        self.assertEqual(rec["items"]["STORY_1"]["state"], "published")   # 他は止めない
        self.assertEqual(run_all(self.poster(rec)), [])
        self.assertEqual(len(self.ig.published), 3)

    def test_unknown_result_that_was_applied_is_not_reposted(self):
        rec = {}
        self.ig.fail_publish = "network_after_apply"
        self.assertEqual(run_all(self.poster(rec)), ["FEED"])
        self.assertEqual(rec["items"]["FEED"]["state"], "publishing")
        run_all(self.poster(rec))
        self.assertEqual(rec["items"]["FEED"]["state"], "published")
        self.assertEqual(len(self.ig.published), 3)                       # 再投稿なし

    def test_unknown_result_not_applied_is_published_once(self):
        rec = {}
        self.ig.fail_publish = "network"
        run_all(self.poster(rec))
        run_all(self.poster(rec))
        self.assertEqual(rec["items"]["FEED"]["state"], "published")
        self.assertEqual(len(self.ig.published), 3)

    def test_expired_container_is_recreated(self):
        rec = {}
        run_all(self.poster(rec, publish=False))                          # 非公開リハーサル
        self.assertEqual(self.ig.published, [])
        self.ig.status[rec["items"]["FEED"]["container"]] = "EXPIRED"
        run_all(self.poster(rec))
        self.assertEqual(len(self.ig.published), 3)

    def test_gives_up_after_max_attempts(self):
        rec = {"items": {"FEED": {"state": "failed", "attempts": 3}}}
        self.assertEqual(run_all(self.poster(rec)), ["FEED"])
        self.assertEqual(len(self.ig.published), 2)


class ProbeSafetyTest(unittest.TestCase):
    """IG_PROBE (DRY_RUN) may create private containers but must never publish or change posts."""

    def test_probe_never_publishes(self):
        from unittest import mock
        from sg_calendar import instagram as ig_mod
        calls = []

        class Resp:
            ok = True

            def __init__(self, body):
                self._b = body

            def json(self):
                return self._b

        def fake_post(url, data=None, timeout=None):
            calls.append(url.rsplit("/", 1)[-1])
            return Resp({"id": f"c{len(calls)}", "success": True})

        ig = ig_mod.Instagram("123", "tok", dry_run=True, probe=True)
        with mock.patch.object(ig_mod.requests, "post", side_effect=fake_post):
            self.assertTrue(ig.create_image("https://x/a.jpg", story=True))
            self.assertTrue(ig.create_carousel(["c1", "c2"], "cap"))
            self.assertIsNone(ig.publish("c1"))
            self.assertFalse(ig.disable_comments("m1"))
        self.assertEqual(calls, ["media", "media"])            # media_publish / コメント変更は送られない

        rec = {}
        poster = Poster(ig, rec, lambda r: None, publish=False, prepare=True)
        with mock.patch.object(ig_mod.requests, "post", side_effect=fake_post), \
                mock.patch.object(ig, "wait_finished", return_value="FINISHED"):
            poster.run_item("STORY_1", lambda i: (i.create_image("https://x/s.jpg", story=True), None))
        self.assertEqual(rec["items"]["STORY_1"]["state"], "prepared")
        self.assertNotIn("media_publish", calls)


class JpegTest(unittest.TestCase):
    def test_high_quality_jpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            png, jpg = Path(tmp, "a.png"), Path(tmp, "a.jpg")
            im = Image.new("RGB", images.FEED_SIZE, images.DESIGN_BG)
            ImageDraw.Draw(im).text((300, 600), "11:00 12:00 1:00", fill=(255, 87, 87))
            im.save(png)
            self.assertGreaterEqual(images.to_jpeg(png, jpg), images.MIN_PSNR)
            with Image.open(jpg) as j:
                self.assertEqual((j.format, j.size), ("JPEG", images.FEED_SIZE))

    def test_identical_pages_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp, "a.png")
            Image.new("RGB", images.FEED_SIZE, images.DESIGN_BG).save(a)
            with self.assertRaises(ValueError):
                images.assert_pages_differ(a, a)


if __name__ == "__main__":
    unittest.main()


# ── composing pages from the master images ─────────────────────────────────

from sg_calendar import compose, run_daily as RD  # noqa: E402

THUMBS = FIX / "masters_thumb"      # Canva previews (480x600) of the two master copies


class ComposeTest(unittest.TestCase):
    def setUp(self):
        self.layout = compose.load_layout()

    def masters(self, n):
        return Image.open(THUMBS / f"open_p{n}.png"), Image.open(THUMBS / f"booked_p{n}.png")

    def test_every_layout_slot_is_found(self):
        for pl in self.layout["pages"]:
            boxes = compose.slot_boxes(*self.masters(pl["page"]), pl)
            self.assertEqual(set(boxes), {(s["date"], s["time"]) for s in pl["slots"]})

    def test_only_booked_slots_change(self):
        booked = {("2026-11-06", "11:00"), ("2026-11-29", "15:00")}
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = compose.build_pages(THUMBS, booked, d, self.layout)
            o1, b1 = self.masters(1)
            boxes = compose.slot_boxes(o1, b1, self.layout["pages"][0])
            img = Image.open(p1)
            compose.verify(img, o1, b1, boxes, {("2026-11-06", "11:00")})
            with self.assertRaises(compose.ComposeError):        # 違う枠の組み合わせでは一致しない
                compose.verify(img, o1, b1, boxes, set())

    def test_slot_not_on_calendar_is_rejected(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(compose.ComposeError):
            compose.build_pages(THUMBS, {("2026-11-09", "11:00")}, d, self.layout)

    def test_layout_mismatch_is_rejected(self):
        pl = json.loads(json.dumps(self.layout["pages"][0]))
        pl["slots"].pop()
        with self.assertRaises(compose.ComposeError):
            compose.slot_boxes(*self.masters(1), pl)

    def test_masters_differing_elsewhere_are_rejected(self):
        o, b = self.masters(1)
        b = b.copy()
        b.putpixel((10, 10), (0, 0, 0))
        with self.assertRaises(compose.ComposeError):
            compose.slot_boxes(o, b, self.layout["pages"][0])


class BookedSlotsTest(unittest.TestCase):
    def data(self, mails):
        return L.to_json(L.build_ledger(mails, *PERIOD))

    def test_active_bookings_and_manual_closed(self):
        d = self.data([mail("1001", 6, "11:00", "2026-10-01T00:00:00Z")])
        old = RD.CONFIG["manual_closed"]
        RD.CONFIG["manual_closed"] = [["2026-11-07", "12:00"]]
        try:
            booked, blockers = RD.booked_slots(d)
        finally:
            RD.CONFIG["manual_closed"] = old
        self.assertEqual(booked, {("2026-11-06", "11:00"), ("2026-11-07", "12:00")})
        self.assertEqual(blockers, [])

    def test_double_booking_and_unknown_slot_stop(self):
        d = self.data([mail("1001", 29, "15:00", "2026-10-01T00:00:00Z"),
                       mail("1002", 29, "15:00", "2026-10-02T00:00:00Z"),
                       mail("1003", 9, "11:00", "2026-10-02T00:00:00Z")])
        _, blockers = RD.booked_slots(d)
        self.assertTrue(any("2026-11-09 11:00" in b for b in blockers))
        self.assertGreaterEqual(len(blockers), 2)


class DeletePreviousFeedTest(unittest.TestCase):
    CAPTION = "cap"

    def setUp(self):
        self.records = {
            "2026-11-09": {"items": {"FEED": {"state": "published", "media_id": "m9"}}},
            "2026-11-08": {"items": {"FEED": {"state": "published", "media_id": "m8", "deleted_at": "x"}}},
            "2026-11-07": {"items": {"FEED": {"state": "published", "media_id": "m7"}}},
        }
        self.saved = {}
        self.patch = {"DRY_RUN": False,
                      "load_record": lambda d: json.loads(json.dumps(self.records.get(d, {}))),
                      "record_saver": lambda d: (lambda rec: self.saved.__setitem__(d, rec))}
        self.orig = {k: getattr(RD, k) for k in self.patch}
        for k, v in self.patch.items():
            setattr(RD, k, v)

    def tearDown(self):
        for k, v in self.orig.items():
            setattr(RD, k, v)

    def ig(self, info):
        class IG:
            deleted = []

            def media_info(self, mid):
                return info[mid]

            def delete_media(self, mid):
                IG.deleted.append(mid)
                return True
        return IG()

    def test_deletes_only_our_undeleted_posts(self):
        ig = self.ig({"m9": {"media_type": "CAROUSEL_ALBUM", "caption": "cap"},
                      "m7": {"media_type": "CAROUSEL_ALBUM", "caption": "edited by hand"}})
        done, problems = RD.delete_previous_feeds(ig, "2026-11-10", self.CAPTION)
        self.assertEqual(ig.deleted, ["m9"])                       # m8 は削除済み、m7 は中身が変わっている
        self.assertEqual(done, ["2026-11-09: deleted"])
        self.assertEqual(len(problems), 1)
        self.assertIn("deleted_at", self.saved["2026-11-09"]["items"]["FEED"])

    def test_dry_run_deletes_nothing(self):
        RD.DRY_RUN = True
        ig = self.ig({})
        done, _ = RD.delete_previous_feeds(ig, "2026-11-10", self.CAPTION)
        self.assertEqual(ig.deleted, [])
        self.assertEqual(done, ["2026-11-09: would delete", "2026-11-07: would delete"])
