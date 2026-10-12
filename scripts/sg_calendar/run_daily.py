#!/usr/bin/env python3
"""
atelierR Singapore November calendar — daily run (Asia/Singapore)

毎朝の流れ (GitHub Actions だけで完結。Canva・Claude には毎日アクセスしない):
  post      Gmail の STORES メール → 予約番号単位の台帳
            → 予約済みの枠 (+ 手動で閉じた枠) を決める
            → 2枚の元画像 (全部空き / 全部予約済み、assets/sg_masters/) から枠ごとに切り貼りして
              1・2ページを作り、画素単位で検証 → JPEG (フィード 1080x1350 / ストーリーズ 1080x1920)
            → Instagram 公式 API: コンテナ作成 (非公開) → 05:00 SGT まで待機 → 公開
              フィード (2枚カルーセル)・ストーリーズ2本を個別に状態管理 (post_state.py) → コメントオフ
            → 前日までにこの仕組みが投稿したフィードを削除 (自分の記録にある投稿だけ)
  ledger    台帳だけ作って保存・確認 (投稿しない)
  watchdog  05:00 以降に3件すべて公開済みか確認し、そうでなければ失敗 (= 通知)

止める条件: 台帳の矛盾 (同じ枠に2件・元予約のない変更/キャンセル)、未確定の変更・キャンセル依頼、
            カレンダーにない日時の予約、画像検証の失敗。
            止めたときは exit 2 → ワークフローが Issue で通知する。

安全設定: DRY_RUN=true (既定) は Instagram・GitHub に一切書き込まない。
            IG_PROBE=true のときだけ、非公開のコンテナ作成 (公開はしない) まで Instagram に送る。
          DRY_RUN=false + AUTO_PUBLISH=false は、画像の保存とコンテナ作成までで公開しない (非公開リハーサル)。
          DRY_RUN=false + AUTO_PUBLISH=true で初めて公開する。
"""
import base64
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sg_calendar import auth, compose, images, ledger as ledger_mod  # noqa: E402
from sg_calendar.instagram import Instagram  # noqa: E402
from sg_calendar.post_state import ITEMS, Poster  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config" / "sg_calendar.json").read_text())
CAPTION_PATH = ROOT / "config" / "sg_caption.txt"
SGT = ZoneInfo(CONFIG["timezone"])
OUT = Path(os.environ.get("SG_OUT_DIR", ROOT / "out"))

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
AUTO_PUBLISH = os.environ.get("AUTO_PUBLISH", "false").lower() == "true"
MASTERS = Path(os.environ.get("SG_MASTERS_DIR", ROOT / "assets" / "sg_masters"))

GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
GITHUB_API = "https://api.github.com"
MEDIA_BRANCH = os.environ.get("MEDIA_BRANCH", "instagram-media")
MEDIA_TEST_BRANCH = "instagram-media-test"

EXIT_OK, EXIT_FAIL, EXIT_STOPPED = 0, 1, 2


def log(msg):
    print(msg, flush=True)


# ── Gmail ──────────────────────────────────────────────────────────────────

def gmail_token():
    return auth.gmail_access_token()


def _body_text(payload):
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        text = _body_text(part)
        if text:
            return text
    return ""


def _gmail_get(path, headers, params, tries=6):
    """GET with backoff on Gmail's rate limits (429, 403 *RateLimitExceeded) and 5xx."""
    for attempt in range(tries):
        r = requests.get(f"{GMAIL_API}/{path}", headers=headers, params=params, timeout=30)
        reason = ""
        if r.status_code == 403:
            try:
                reason = (r.json().get("error", {}).get("errors") or [{}])[0].get("reason", "")
            except ValueError:
                pass
        limited = r.status_code == 429 or r.status_code >= 500 or reason.endswith("RateLimitExceeded")
        if not limited or attempt == tries - 1:
            if not r.ok:
                raise RuntimeError(f"Gmail request failed: HTTP {r.status_code} {reason}".strip())
            return r.json()
        time.sleep(2 ** attempt)


def _list_ids(h, q):
    ids, page = [], None
    while True:
        d = _gmail_get("users/me/messages", h, {"q": q, "maxResults": 500, "pageToken": page})
        ids += [m["id"] for m in d.get("messages", [])]
        page = d.get("nextPageToken")
        if not page:
            return ids


def fetch_events():
    """STORES mails that matter for the period: bookings/changes/cancellations whose body names
    the period's month (e.g. 2026年11月), plus recent customer inquiries."""
    h = {"Authorization": f"Bearer {gmail_token()}"}
    start = datetime.strptime(CONFIG["period"][0], "%Y-%m-%d")
    month = f"{start.year}年{start.month}月"
    booking_q = (f'from:hello@stores.jp "{month}" {{"予約が入りました" "予約が変更されました" '
                 f'"予約がキャンセルされました"}} newer_than:400d')
    inquiry_q = 'from:hello@stores.jp "お問い合わせがあります" newer_than:120d'
    ids = list(dict.fromkeys(_list_ids(h, booking_q) + _list_ids(h, inquiry_q)))
    events = []
    for mid in ids:
        m = _gmail_get(f"users/me/messages/{mid}", h, {"format": "full"})
        time.sleep(0.2)                             # 1通ずつ間をあけて Gmail の上限を避ける
        hdrs = {x["name"]: x["value"] for x in m["payload"].get("headers", [])}
        received = datetime.fromtimestamp(int(m["internalDate"]) / 1000, ZoneInfo("UTC")).isoformat()
        ev = ledger_mod.parse_message(mid, received, hdrs.get("Subject", ""), _body_text(m["payload"]))
        if ev:
            events.append(ev)
    log(f"Gmail: {len(ids)} messages scanned, {len(events)} reservation events")
    return events


def current_ledger():
    lg = ledger_mod.build_ledger(fetch_events(), *CONFIG["period"])
    return ledger_mod.to_json(lg)


# ── GitHub media branch (public image URLs, state, run records) ────────────

def _gh():
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json"}


def _repo():
    return os.environ["GITHUB_REPOSITORY"]


def ensure_media_branch(branch=MEDIA_BRANCH):
    repo = _repo()
    if requests.get(f"{GITHUB_API}/repos/{repo}/branches/{branch}", headers=_gh(), timeout=30).ok:
        return
    main = requests.get(f"{GITHUB_API}/repos/{repo}/git/ref/heads/main", headers=_gh(), timeout=30).json()
    requests.post(f"{GITHUB_API}/repos/{repo}/git/refs", headers=_gh(), timeout=30, json={
        "ref": f"refs/heads/{branch}", "sha": main["object"]["sha"]}).raise_for_status()


def read_branch_file(path):
    r = requests.get(f"{GITHUB_API}/repos/{_repo()}/contents/{path}", headers=_gh(),
                     params={"ref": MEDIA_BRANCH}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return base64.b64decode(r.json()["content"])


def put_branch_file(path, content, message, branch=MEDIA_BRANCH):
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{path}"
    cur = requests.get(url, headers=_gh(), params={"ref": branch}, timeout=30)
    body = {"message": message, "branch": branch, "content": base64.b64encode(content).decode()}
    if cur.ok:
        body["sha"] = cur.json()["sha"]
    requests.put(url, headers=_gh(), json=body, timeout=60).raise_for_status()
    return f"https://raw.githubusercontent.com/{_repo()}/{branch}/{path}"


# ── Scheduling helpers ─────────────────────────────────────────────────────

def publish_time(now):
    """Today's 05:00 SGT; if that has already passed, publish right away (nearest feasible time)."""
    hh, mm = map(int, CONFIG["post_time"].split(":"))
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return target if now < target else now


def make_waiter(target, max_wait_min=50):
    """Sleep until `target` (SGT) before publishing; never sleeps longer than max_wait_min."""
    def wait():
        delay = (target - datetime.now(SGT)).total_seconds()
        if delay > max_wait_min * 60:
            raise RuntimeError(f"started too early ({delay / 60:.0f} min before publish time)")
        if delay > 0:
            log(f"waiting {delay / 60:.1f} min until {target:%H:%M} SGT")
            time.sleep(delay)
    return wait


# ── Images ─────────────────────────────────────────────────────────────────

def booked_slots(data):
    """(booked {(date, time)}, blockers) from the ledger: active bookings + manually closed slots."""
    layout = compose.load_layout()
    on_calendar = {(sl["date"], sl["time"]) for pg in layout["pages"] for sl in pg["slots"]}
    blockers = list(data["anomalies"])
    blockers += [f"unconfirmed change/cancel request in mail {m}" for m in data["pending_requests"]
                 if m not in CONFIG["acknowledged_inquiries"]]
    lo, hi = data["period"]
    booked = set()
    for r in data["reservations"].values():
        if r["state"] != "cancelled" and lo <= r["slot"][0] <= hi:
            booked.add(tuple(r["slot"]))
    for d, t in sorted(booked - on_calendar):
        blockers.append(f"booking at {d} {t} has no slot on the calendar")
    manual = {tuple(m) for m in CONFIG["manual_closed"]}
    for d, t in sorted(manual - on_calendar):
        blockers.append(f"manual_closed {d} {t} is not a slot on the calendar (check config)")
    return (booked | manual) & on_calendar, blockers


def build_images(day, report, booked):
    """Pages 1-2 from the master images → verify → JPEG feed + 1080x1920 JPEG stories."""
    pages = compose.build_pages(MASTERS, booked, OUT / "pages")
    pngs = []
    for page, src in zip(CONFIG["pages"], pages):
        p = OUT / f"sg_feed_p{page}_{day}.png"
        src.replace(p)
        pngs.append(p)
    for p in pngs:
        images.verify_feed(p)
    images.assert_pages_differ(*pngs)
    files, checks = {}, {}
    for page, png in zip(CONFIG["pages"], pngs):
        story_png = OUT / f"sg_story_p{page}_{day}.png"
        images.make_story(png, story_png)
        feed_jpg, story_jpg = OUT / f"feed_p{page}.jpg", OUT / f"story_p{page}.jpg"
        checks[f"feed_p{page}"] = f"1080x1350 JPEG q95 4:4:4, PSNR {images.to_jpeg(png, feed_jpg)} dB"
        checks[f"story_p{page}"] = f"1080x1920 JPEG, full page unscaled, PSNR {images.to_jpeg(story_png, story_jpg)} dB"
        files[f"feed_p{page}"], files[f"story_p{page}"] = feed_jpg, story_jpg
    report["images"] = {"source": "master images (Canva export, pro, lossless) composed per slot",
                        "booked_slots": len(booked), "checks": checks}
    return files


# ── Instagram ──────────────────────────────────────────────────────────────

def instagram_client(probe=False):
    # 新ワークフローはシステムユーザーの META_ACCESS_TOKEN のみを使う (旧 IG_ACCESS_TOKEN は使わない)
    return Instagram(os.environ.get("IG_USER_ID", "").strip(), os.environ.get("META_ACCESS_TOKEN", "").strip(),
                     dry_run=DRY_RUN, probe=probe)


def load_record(day):
    if DRY_RUN:
        p = OUT / f"record_{day}.json"
        return json.loads(p.read_text()) if p.exists() else {}
    raw = read_branch_file(f"records/{day}.json")
    return json.loads(raw) if raw else {}


def record_saver(day):
    def save(rec):
        body = json.dumps(rec, ensure_ascii=False, indent=2)
        (OUT / f"record_{day}.json").write_text(body)
        if not DRY_RUN:
            put_branch_file(f"records/{day}.json", body.encode(), f"SG post state {day}")
    return save


def find_feed_today(ig, day, caption):
    """Our carousel already on Instagram today (protects against a lost record)."""
    start = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=SGT).timestamp())
    for m in ig.media_since(start):
        if m.get("media_type") == "CAROUSEL_ALBUM" and (m.get("caption") or "").strip() == caption:
            return m["id"]
    return None


def post_to_instagram(report, day, files, now):
    caption = CAPTION_PATH.read_text().strip()
    probe = DRY_RUN and os.environ.get("IG_PROBE", "").lower() == "true"
    ig = instagram_client(probe)
    publish = (not DRY_RUN) and AUTO_PUBLISH
    when = publish_time(now)
    report["publish_at"] = when.isoformat()
    report["late"] = now > when.replace(hour=5, minute=5)

    if not DRY_RUN:
        ensure_media_branch()
        urls = {k: put_branch_file(f"media/{day}/{f.name}", f.read_bytes(), f"SG {f.stem} {day}")
                for k, f in files.items()}
    elif probe:
        # 非公開コンテナの作成テスト用。画像はテスト用ブランチに置く (本番の記録・画像とは分ける)
        ensure_media_branch(MEDIA_TEST_BRANCH)
        urls = {k: put_branch_file(f"probe/{day}/{f.name}", f.read_bytes(), f"SG probe {f.stem} {day}",
                                   branch=MEDIA_TEST_BRANCH) for k, f in files.items()}
    else:
        urls = {k: f"(dry-run) {f.name}" for k, f in files.items()}

    poster = Poster(ig, load_record(day), record_saver(day), publish=publish,
                    prepare=(not DRY_RUN) or probe, wait_until=make_waiter(when))

    # 記録が失われていても、本日のフィードが既に公開済みなら再投稿しない
    if poster.item("FEED")["state"] == "pending" and (not DRY_RUN or probe):
        existing = find_feed_today(ig, day, caption)
        if existing:
            poster._set("FEED", state="published", media_id=existing, note="found on Instagram")

    def feed(ig_):
        children = [ig_.create_image(urls[f"feed_p{p}"], carousel_item=True) for p in CONFIG["pages"]]
        for c in children:
            ig_.wait_finished(c)
        return ig_.create_carousel(children, caption), children

    def story(page):
        return lambda ig_: (ig_.create_image(urls[f"story_p{page}"], story=True), None)

    errors = []
    for key, fn in [("FEED", feed)] + [(f"STORY_{p}", story(p)) for p in CONFIG["pages"]]:
        try:
            poster.run_item(key, fn)
        except Exception as e:                       # 1件の失敗で他の投稿を止めない
            errors.append(f"{key}: {e}")
    if publish and poster.item("FEED")["state"] == "published":
        if not poster.item("FEED").get("media_id"):
            mid = find_feed_today(ig, day, caption)
            if mid:
                poster._set("FEED", media_id=mid)
        poster.comments_off("FEED")
    if poster.item("FEED")["state"] == "published" or DRY_RUN:
        done, problems = delete_previous_feeds(ig, day, caption)
        report["previous_feed"] = {"done": done, "problems": problems}
    report["instagram"] = poster.summary()
    report["instagram_errors"] = errors
    return errors


def delete_previous_feeds(ig, day, caption):
    """After today's feed is live: delete the feed posts this system published on earlier days.

    Only media IDs from our own records are touched, and only if Instagram still reports them as
    our carousel with our caption. Returns (done, problems)."""
    done, problems = [], []
    if not CONFIG.get("delete_previous_feed"):
        return done, problems
    today = datetime.strptime(day, "%Y-%m-%d")
    for back in range(1, 8):
        d = (today - timedelta(days=back)).strftime("%Y-%m-%d")
        rec = load_record(d)
        feed = rec.get("items", {}).get("FEED", {})
        mid = feed.get("media_id")
        if feed.get("state") != "published" or not mid or feed.get("deleted_at"):
            continue
        if DRY_RUN:
            done.append(f"{d}: would delete")
            continue
        save = record_saver(d)
        try:
            info = ig.media_info(mid)
            if info.get("media_type") != "CAROUSEL_ALBUM" or (info.get("caption") or "").strip() != caption:
                problems.append(f"{d}: not deleted — the post no longer looks like ours (type/caption changed)")
                continue
            if not ig.delete_media(mid):
                raise RuntimeError("Instagram did not confirm the deletion")
            feed.update(deleted_at=datetime.now(SGT).isoformat(timespec="seconds"), delete_error=None)
            done.append(f"{d}: deleted")
        except Exception as e:
            feed["delete_error"] = str(e)
            problems.append(f"{d}: delete failed — {e}")
        save(rec)
    return done, problems


# ── Steps ──────────────────────────────────────────────────────────────────

def step_ledger(report):
    data = current_ledger()
    report["ledger"] = data
    OUT.joinpath("ledger.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    if not DRY_RUN:
        ensure_media_branch()
        put_branch_file("state/ledger.json", json.dumps(data, ensure_ascii=False, indent=2).encode(),
                        f"SG ledger {report['day']}")
    booked, blockers = booked_slots(data)
    report["booked_slots"] = len(booked)
    report["blockers"] = blockers
    return ("STOPPED" if not DRY_RUN else "WOULD_STOP") if blockers else "LEDGER_OK"


def step_post(report, now):
    day = report["day"]
    record = load_record(day)
    if all(record.get("items", {}).get(k, {}).get("state") == "published" for k in ITEMS):
        report["instagram"] = {k: record["items"][k] for k in ITEMS}
        return "ALREADY_POSTED"                     # 予備のトリガーで再実行されても何もしない
    try:
        data = current_ledger()
        booked, problems = booked_slots(data)
        report["bookings"] = ledger_summary(data)
    except PermissionError as e:
        if not DRY_RUN:
            raise
        booked, problems = set(), [f"AUTH ERROR: {e}"]   # DRY_RUN: 記録したうえで後続の工程も試す
    report["checks"] = problems
    if problems and not DRY_RUN:
        return "STOPPED"

    files = build_images(day, report, booked)
    try:
        errors = post_to_instagram(report, day, files, now)
    except PermissionError:
        raise
    except Exception as e:
        if not DRY_RUN:
            raise
        errors = [f"instagram: {e}"]
        report["instagram_errors"] = errors
    if problems:
        return "WOULD_STOP"
    if errors:
        return "WOULD_FAIL" if DRY_RUN else "FAILED"
    if report.get("previous_feed", {}).get("problems"):
        return "PUBLISHED_OLD_POST_NOT_DELETED"     # 投稿は成功。前日分は手動で削除してもらう (通知)
    return "DRY_RUN_OK" if DRY_RUN else ("PUBLISHED" if AUTO_PUBLISH else "PREPARED_NOT_PUBLISHED")


def step_watchdog(report):
    """After 05:00: confirm all three posts are published today; otherwise fail → notification."""
    day = report["day"]
    items = load_record(day).get("items", {})
    states = {k: items.get(k, {}).get("state", "missing") for k in ITEMS}
    report["watchdog"] = states
    return "ALL_PUBLISHED" if all(v == "published" for v in states.values()) else "NOT_PUBLISHED"


def mask(obj):
    """Hide all but the last 3 digits of reservation numbers (the repo, its logs and issues are public)."""
    return json.loads(ledger_mod.mask_numbers(json.dumps(obj, ensure_ascii=False, default=str)))


def ledger_summary(data):
    """Read-only overview for the report: booked times per date, no reservation numbers or names."""
    by_date, cancelled = {}, 0
    for r in data["reservations"].values():
        if r["state"] == "cancelled":
            cancelled += 1
            continue
        if data["period"][0] <= r["slot"][0] <= data["period"][1]:
            by_date.setdefault(r["slot"][0], []).append(r["slot"][1])
    return {"period": data["period"],
            "active_bookings": sum(len(v) for v in by_date.values()),
            "cancelled": cancelled,
            "booked_by_date": {d: sorted(v) for d, v in sorted(by_date.items())},
            "anomalies": data["anomalies"],
            "unconfirmed_change_requests": data["pending_requests"]}


def step_auth_check(report):
    report["auth"] = auth.check()
    # Gmail が通ったら、11/6〜30 の予約を読み取り専用で取得して要約する (書き込みは一切しない)
    if report["auth"].get("Gmail") == "OK" and os.environ.get("AUTH_CHECK_LEDGER", "").lower() == "true":
        try:
            data = current_ledger()
            OUT.joinpath("ledger.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
            report["gmail_ledger"] = ledger_summary(data)
        except Exception as e:                      # 要約の失敗は認証結果とは分けて記録
            report["gmail_ledger"] = f"FAIL: {type(e).__name__}: {e}"
    return "AUTH_OK" if all(not str(v).startswith("FAIL") for v in report["auth"].values()) else "AUTH_FAILED"


def main(mode):
    now = datetime.now(SGT)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"mode": mode, "run_at": now.isoformat(), "day": now.strftime("%Y-%m-%d"),
              "dry_run": DRY_RUN, "auto_publish": AUTO_PUBLISH}
    log(f"=== SG calendar {mode} {now:%Y-%m-%d %H:%M} SGT | DRY_RUN={DRY_RUN} "
        f"AUTO_PUBLISH={AUTO_PUBLISH} ===")
    try:
        if mode == "auth-check":
            status = step_auth_check(report)
        elif mode == "watchdog":
            status = step_watchdog(report)
        else:
            status = step_ledger(report) if mode == "ledger" else step_post(report, now)
    except PermissionError as e:
        report["status"] = "AUTH_ERROR"
        report["error"] = str(e)
        (OUT / "report.json").write_text(json.dumps(mask(report), ensure_ascii=False, indent=2))
        raise
    report["status"] = status
    public = mask(report)
    (OUT / "report.json").write_text(json.dumps(public, ensure_ascii=False, indent=2))
    log(json.dumps(public, ensure_ascii=False, indent=2))
    if status in ("AUTH_FAILED", "FAILED", "NOT_PUBLISHED", "PUBLISHED_OLD_POST_NOT_DELETED"):
        return EXIT_FAIL
    return EXIT_STOPPED if status == "STOPPED" else EXIT_OK


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "post"
    if mode not in ("ledger", "post", "auth-check", "watchdog"):
        sys.exit(f"usage: run_daily.py ledger|post|auth-check|watchdog (got {mode})")
    try:
        sys.exit(main(mode))
    except PermissionError as e:
        log(f"AUTH ERROR: {e}")
        sys.exit(EXIT_FAIL)
