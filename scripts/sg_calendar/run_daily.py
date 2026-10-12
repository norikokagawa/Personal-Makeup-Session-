#!/usr/bin/env python3
"""
atelierR Singapore November calendar — daily run (Asia/Singapore)

毎朝の流れ (本番。起動経路は docs/SG_SCHEDULING.md):
  ledger    Gmail の STORES メール → 予約番号単位の台帳 → state/ledger.json (instagram-media ブランチ)
  (Canva)   Claude 定期実行 docs/SG_CANVA_ROUTINE.md: 台帳と Canva 1・2ページ目を照合 → 横線だけ更新
            → 検証 → 保存 → state/canva_state.json
  post      Gmail を再確認し、最後に検証した Canva 状態と一致することを確認
            → 1・2ページを高画質書き出し・検証 → JPEG (フィード 1080x1350 / ストーリーズ 1080x1920)
            → Instagram 公式 API: コンテナ作成 (非公開) → 05:00 SGT まで待機 → 公開
              フィード (2枚カルーセル)・ストーリーズ2本を個別に状態管理 (post_state.py) → コメントオフ
  watchdog  05:00 以降に3件すべて公開済みか確認し、そうでなければ失敗 (= 通知)

止める条件: 台帳の矛盾 (同じ枠に2件・元予約のない変更/キャンセル)、未確定の変更・キャンセル依頼、
            デザインにない日時の予約、最後の Canva 更新以降に予約が変わった、画像検証の失敗。
            止めたときは exit 2 → ワークフローが Issue で通知する。

安全設定: DRY_RUN=true (既定) は Instagram・GitHub に一切書き込まず、Canva はテスト用コピーを使う。
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
from sg_calendar import auth, canva_doc, images, ledger as ledger_mod  # noqa: E402
from sg_calendar.instagram import Instagram  # noqa: E402
from sg_calendar.post_state import ITEMS, Poster  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config" / "sg_calendar.json").read_text())
CAPTION_PATH = ROOT / "config" / "sg_caption.txt"
SGT = ZoneInfo(CONFIG["timezone"])
OUT = Path(os.environ.get("SG_OUT_DIR", ROOT / "out"))

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
AUTO_PUBLISH = os.environ.get("AUTO_PUBLISH", "false").lower() == "true"
DESIGN_ID = CONFIG["test_design_id"] if DRY_RUN else CONFIG["design_id"]

CANVA_API = "https://api.canva.com/rest/v1"
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


def fetch_events():
    h = {"Authorization": f"Bearer {gmail_token()}"}
    q = ('from:hello@stores.jp ({"予約が入りました" "予約が変更されました" '
         '"予約がキャンセルされました" "お問い合わせがあります"}) newer_than:400d')
    ids, page = [], None
    while True:
        r = requests.get(f"{GMAIL_API}/users/me/messages", headers=h, timeout=30,
                         params={"q": q, "maxResults": 500, "pageToken": page})
        r.raise_for_status()
        d = r.json()
        ids += [m["id"] for m in d.get("messages", [])]
        page = d.get("nextPageToken")
        if not page:
            break
    events = []
    for mid in ids:
        r = requests.get(f"{GMAIL_API}/users/me/messages/{mid}", headers=h,
                         params={"format": "full"}, timeout=30)
        r.raise_for_status()
        m = r.json()
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


# ── Canva (Connect API: export only) ───────────────────────────────────────

def canva_token():
    # 1回限りの refresh token を消費し、新しい token を Secrets に保存 (失敗したら停止)
    return auth.canva_access_token()


def export_pages(design_id, pages, dest_dir, day):
    h = {"Authorization": f"Bearer {canva_token()}"}
    r = requests.post(f"{CANVA_API}/exports", headers=h, timeout=60, json={
        "design_id": design_id,
        "format": {"type": "png", "pages": pages, "width": 1080, "height": 1350,
                   "export_quality": "pro", "lossless": True},
    })
    r.raise_for_status()
    job = r.json()["job"]["id"]
    for _ in range(40):
        time.sleep(3)
        s = requests.get(f"{CANVA_API}/exports/{job}", headers=h, timeout=30).json()["job"]
        if s["status"] == "success":
            if len(s["urls"]) != len(pages):
                raise RuntimeError(f"Canva returned {len(s['urls'])} files for {len(pages)} pages")
            paths = []
            for page, url in zip(pages, s["urls"]):
                img = requests.get(url, timeout=60)
                img.raise_for_status()
                p = dest_dir / f"sg_feed_p{page}_{day}.png"
                p.write_bytes(img.content)
                paths.append(p)
            return paths
        if s["status"] == "failed":
            raise RuntimeError(f"Canva export failed: {s}")
    raise TimeoutError("Canva export timed out")


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

def download_test_exports(day):
    """DRY_RUN only: official Canva export URLs produced by the Canva connector (file not logged)."""
    urls = json.loads(Path(ROOT / os.environ["TEST_EXPORT_URLS_FILE"]).read_text())["urls"]
    paths = []
    for page, url in zip(CONFIG["pages"], urls):
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        p = OUT / f"sg_feed_p{page}_{day}.png"
        p.write_bytes(r.content)
        paths.append(p)
    return paths


def build_images(day, report):
    """Export pages 1-2 (official, high quality) → verify → JPEG feed + 1080x1920 JPEG stories."""
    test_file = os.environ.get("TEST_EXPORT_URLS_FILE")
    if DRY_RUN and test_file and (ROOT / test_file).exists():
        pngs = download_test_exports(day)
        source = "Canva connector export (pro, 1080x1350) of the TEST copy"
    else:
        pngs = export_pages(DESIGN_ID, CONFIG["pages"], OUT, day)
        source = "Canva Connect export (pro, 1080x1350)"
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
    report["images"] = {"source": source, "checks": checks}
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
    report["instagram"] = poster.summary()
    report["instagram_errors"] = errors
    return errors


def check_against_canva(data, state):
    """Problems that mean the calendar on Canva may not match the current bookings.

    The Canva step need not have run today: if bookings have not changed since the last
    verified Canva state, the calendar is still correct and is posted as usual."""
    if state is None:
        return ["no Canva state recorded (Canva step never completed)"]
    problems = []
    if state["design_id"] != DESIGN_ID:
        problems.append(f"Canva state is for {state['design_id']}, expected {DESIGN_ID}")
    if state["ledger_fingerprint"] != ledger_mod.fingerprint(data):
        problems.append("bookings changed since the last verified Canva update")
    p = canva_doc.plan(ledger_mod.from_json(data), canva_doc.grid(state["snapshot"]),
                       CONFIG["manual_closed"], CONFIG["acknowledged_inquiries"])
    problems += p["blockers"]
    if p["strike"] or p["unstrike"]:
        problems.append(f"Canva differs from bookings: strike {p['strike']} unstrike {p['unstrike']}")
    return problems


# ── Steps ──────────────────────────────────────────────────────────────────

def step_ledger(report):
    data = current_ledger()
    report["ledger"] = data
    OUT.joinpath("ledger.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    if not DRY_RUN:
        ensure_media_branch()
        put_branch_file("state/ledger.json", json.dumps(data, ensure_ascii=False, indent=2).encode(),
                        f"SG ledger {report['day']}")
    blockers = data["anomalies"] + [f"unconfirmed change/cancel request in mail {m}"
                                    for m in data["pending_requests"]
                                    if m not in CONFIG["acknowledged_inquiries"]]
    report["blockers"] = blockers
    return ("STOPPED" if not DRY_RUN else "WOULD_STOP") if blockers else "LEDGER_OK"


def load_canva_state():
    if os.environ.get("CANVA_STATE_FILE"):              # テスト用: リポジトリ内のファイル
        return json.loads(Path(ROOT / os.environ["CANVA_STATE_FILE"]).read_text())
    raw = read_branch_file("state/canva_state.json")
    return json.loads(raw) if raw else None


def step_post(report, now):
    day = report["day"]
    record = load_record(day)
    if all(record.get("items", {}).get(k, {}).get("state") == "published" for k in ITEMS):
        report["instagram"] = {k: record["items"][k] for k in ITEMS}
        return "ALREADY_POSTED"                     # 予備のトリガーで再実行されても何もしない
    try:
        data = current_ledger()
        problems = check_against_canva(data, load_canva_state())
    except PermissionError as e:
        if not DRY_RUN:
            raise
        problems = [f"AUTH ERROR: {e}"]             # DRY_RUN: 記録したうえで後続の工程も試す
    report["checks"] = problems
    if problems and not DRY_RUN:
        return "STOPPED"

    files = build_images(day, report)
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
    report["auth"] = auth.check(include_canva=os.environ.get("CHECK_CANVA", "").lower() == "true")
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
              "dry_run": DRY_RUN, "auto_publish": AUTO_PUBLISH, "design_id": DESIGN_ID}
    log(f"=== SG calendar {mode} {now:%Y-%m-%d %H:%M} SGT | DRY_RUN={DRY_RUN} "
        f"AUTO_PUBLISH={AUTO_PUBLISH} design={DESIGN_ID} ===")
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
    if status in ("AUTH_FAILED", "FAILED", "NOT_PUBLISHED"):
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
