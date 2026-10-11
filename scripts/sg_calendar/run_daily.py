#!/usr/bin/env python3
"""
atelierR Singapore November calendar — daily run (Asia/Singapore)

毎朝の流れ (本番):
  04:00  GitHub Actions  `run_daily.py ledger`
         Gmail の STORES メール → 予約番号単位の台帳 → state/ledger.json (instagram-media ブランチ)
  04:15  Claude 定期実行  docs/SG_CANVA_ROUTINE.md
         台帳と Canva 1・2ページ目を照合 → 横線だけ更新 → 検証 → 保存 → state/canva_state.json
  04:40  GitHub Actions  `run_daily.py post`
         Gmail を再確認し、Canva 状態と完全一致することを確認 → 1・2ページを高画質書き出し
         → フィード (2枚カルーセル) + ストーリーズ2本を Metricool に 05:00 SGT で登録

止める条件: 台帳の矛盾 (同じ枠に2件・元予約のない変更/キャンセル)、未確定の変更・キャンセル依頼、
            デザインにない日時の予約、Canva 状態が当日分でない/台帳とずれている、画像検証の失敗。
            止めたときは exit 2 → ワークフローが Issue で通知する。

安全設定: DRY_RUN=true (既定) は Metricool・GitHub に一切書き込まず、Canva はテスト用コピーを使う。
          DRY_RUN では止める条件に当たっても後続の工程を最後まで試し、"WOULD_STOP" と記録する。
          AUTO_PUBLISH=false (既定) は Metricool に下書きとしてだけ作る。
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
from sg_calendar import canva_doc, images, ledger as ledger_mod  # noqa: E402
from sg_calendar.metricool import Metricool, TYPE_FEED, TYPE_STORY  # noqa: E402

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

EXIT_OK, EXIT_FAIL, EXIT_STOPPED = 0, 1, 2


def log(msg):
    print(msg, flush=True)


# ── Gmail ──────────────────────────────────────────────────────────────────

def gmail_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"].strip(),
        "client_id": os.environ["GMAIL_CLIENT_ID"].strip(),
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"].strip(),
    }, timeout=30)
    if not r.ok:
        raise PermissionError(f"Gmail token refresh failed ({r.status_code}): re-authorise Gmail")
    return r.json()["access_token"]


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
    r = requests.post(f"{CANVA_API}/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["CANVA_REFRESH_TOKEN"].strip(),
        "client_id": os.environ["CANVA_CLIENT_ID"].strip(),
        "client_secret": os.environ["CANVA_CLIENT_SECRET"].strip(),
    }, timeout=30)
    if not r.ok:
        raise PermissionError(f"Canva token refresh failed ({r.status_code}): re-authorise Canva")
    data = r.json()
    if "refresh_token" in data:
        # 既存の daily_post.py と同じローテーション処理を再利用
        from daily_post import _save_canva_refresh_token
        _save_canva_refresh_token(data["refresh_token"])
    return data["access_token"]


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


def ensure_media_branch():
    repo = _repo()
    if requests.get(f"{GITHUB_API}/repos/{repo}/branches/{MEDIA_BRANCH}", headers=_gh(), timeout=30).ok:
        return
    main = requests.get(f"{GITHUB_API}/repos/{repo}/git/ref/heads/main", headers=_gh(), timeout=30).json()
    requests.post(f"{GITHUB_API}/repos/{repo}/git/refs", headers=_gh(), timeout=30, json={
        "ref": f"refs/heads/{MEDIA_BRANCH}", "sha": main["object"]["sha"]}).raise_for_status()


def read_branch_file(path):
    r = requests.get(f"{GITHUB_API}/repos/{_repo()}/contents/{path}", headers=_gh(),
                     params={"ref": MEDIA_BRANCH}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return base64.b64decode(r.json()["content"])


def put_branch_file(path, content, message):
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{path}"
    cur = requests.get(url, headers=_gh(), params={"ref": MEDIA_BRANCH}, timeout=30)
    body = {"message": message, "branch": MEDIA_BRANCH, "content": base64.b64encode(content).decode()}
    if cur.ok:
        body["sha"] = cur.json()["sha"]
    requests.put(url, headers=_gh(), json=body, timeout=60).raise_for_status()
    return f"https://raw.githubusercontent.com/{_repo()}/{MEDIA_BRANCH}/{path}"


# ── Scheduling helpers ─────────────────────────────────────────────────────

def publish_time(now):
    """Today 05:00 SGT, or the nearest feasible time (+10 min, rounded) if it has passed."""
    hh, mm = map(int, CONFIG["post_time"].split(":"))
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now <= target - timedelta(minutes=5):
        return target
    t = now + timedelta(minutes=10)
    return t.replace(minute=(t.minute // 5) * 5, second=0, microsecond=0)


def planned_posts():
    """(record key, Metricool type, page numbers in the media, caption?)"""
    return [("FEED", TYPE_FEED, CONFIG["pages"], True)] + \
           [(f"STORY_{p}", TYPE_STORY, [p], False) for p in CONFIG["pages"]]


def already_posted(key, post_type, existing, record):
    """Same-day duplicate check: our record first, then Metricool's calendar for the day."""
    if record.get(key, {}).get("metricool_id"):
        return True
    same = [p for p in existing if Metricool.post_type(p) == post_type]
    if post_type == TYPE_FEED:
        return bool(same)
    return len(same) >= int(key.split("_")[1])     # STORY_1 → 1本目, STORY_2 → 2本目


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


def check_against_canva(data, state, day):
    """Problems that mean the calendar on Canva may not match today's bookings."""
    if state is None:
        return ["no Canva state recorded (Canva step did not run)"]
    problems = []
    if state["design_id"] != DESIGN_ID:
        problems.append(f"Canva state is for {state['design_id']}, expected {DESIGN_ID}")
    if state["date"] != day:
        problems.append(f"Canva state is from {state['date']}, not today")
    if state["ledger_fingerprint"] != ledger_mod.fingerprint(data):
        problems.append("bookings changed after the Canva step ran")
    p = canva_doc.plan(ledger_mod.from_json(data), canva_doc.grid(state["snapshot"]),
                       CONFIG["manual_closed"], CONFIG["acknowledged_inquiries"])
    problems += p["blockers"]
    if p["strike"] or p["unstrike"]:
        problems.append(f"Canva differs from bookings: strike {p['strike']} unstrike {p['unstrike']}")
    return problems


def step_post(report, now):
    day = report["day"]
    data = current_ledger()
    problems = check_against_canva(data, load_canva_state(), day)
    report["checks"] = problems
    if problems and not DRY_RUN:
        return "STOPPED"

    # Images: 1・2ページの正式エクスポート → 検証 → ストーリーズ生成
    feeds = export_pages(DESIGN_ID, CONFIG["pages"], OUT, day)
    stories = []
    for page, f in zip(CONFIG["pages"], feeds):
        images.verify_feed(f)
        s = OUT / f"sg_story_p{page}_{day}.png"
        images.make_story(f, s)
        stories.append(s)
    report["images"] = {"feed": [str(p) for p in feeds], "story": [str(p) for p in stories],
                        "checks": "1080x1350 PNG, edges clear, stories contain full pages unscaled"}

    # Metricool
    when = publish_time(now)
    report["publish_at"] = when.isoformat()
    mc = Metricool(os.environ.get("METRICOOL_USER_TOKEN", ""), os.environ.get("METRICOOL_USER_ID", ""),
                   os.environ.get("METRICOOL_BLOG_ID", ""), CONFIG["timezone"], dry_run=DRY_RUN)
    have_token = bool(os.environ.get("METRICOOL_USER_TOKEN"))
    existing = mc.list_instagram_posts(when.strftime("%Y-%m-%d")) if have_token else []
    report["existing_same_day"] = [{"type": Metricool.post_type(p), "status": Metricool.post_status(p),
                                    "id": p.get("id")} for p in existing]
    if DRY_RUN:
        record = {}
        urls = {f"feed{p}": f"(dry-run) {f.name}" for p, f in zip(CONFIG["pages"], feeds)}
        urls |= {f"story{p}": f"(dry-run) {s.name}" for p, s in zip(CONFIG["pages"], stories)}
    else:
        ensure_media_branch()
        raw = read_branch_file(f"records/{day}.json")
        record = json.loads(raw) if raw else {}
        urls = {}
        for p, f, s in zip(CONFIG["pages"], feeds, stories):
            urls[f"feed{p}"] = put_branch_file(f"media/{day}/feed_p{p}.png", f.read_bytes(), f"SG feed p{p} {day}")
            urls[f"story{p}"] = put_branch_file(f"media/{day}/story_p{p}.png", s.read_bytes(), f"SG story p{p} {day}")

    caption = CAPTION_PATH.read_text().strip()
    results = {}
    for key, post_type, pages, with_caption in planned_posts():
        if already_posted(key, post_type, existing, record):
            results[key] = {"skipped": "already scheduled/published today"}
            continue
        kind = "feed" if post_type == TYPE_FEED else "story"
        media = [mc.normalize_image(urls[f"{kind}{p}"]) for p in pages]
        payload = mc.build_payload(when.strftime("%Y-%m-%dT%H:%M:00"), post_type, media,
                                   caption if with_caption else "", AUTO_PUBLISH)
        res = mc.create(payload)
        results[key] = {"scheduled": not DRY_RUN, "published": False, "draft": payload["draft"],
                        "metricool_id": res.get("id"), "payload": payload if DRY_RUN else None}
    report["metricool"] = results
    report["comments_off"] = "manual: Metricool API has no comment-disable option"
    if not DRY_RUN:
        put_branch_file(f"records/{day}.json",
                        json.dumps({**record, **results}, ensure_ascii=False, indent=2).encode(),
                        f"SG run record {day}")
    if problems:
        return "WOULD_STOP"
    return "DRY_RUN_OK" if DRY_RUN else "SCHEDULED"


def main(mode):
    now = datetime.now(SGT)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"mode": mode, "run_at": now.isoformat(), "day": now.strftime("%Y-%m-%d"),
              "dry_run": DRY_RUN, "auto_publish": AUTO_PUBLISH, "design_id": DESIGN_ID}
    log(f"=== SG calendar {mode} {now:%Y-%m-%d %H:%M} SGT | DRY_RUN={DRY_RUN} "
        f"AUTO_PUBLISH={AUTO_PUBLISH} design={DESIGN_ID} ===")
    status = step_ledger(report) if mode == "ledger" else step_post(report, now)
    report["status"] = status
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    log(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return EXIT_STOPPED if status == "STOPPED" else EXIT_OK


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "post"
    if mode not in ("ledger", "post"):
        sys.exit(f"usage: run_daily.py ledger|post (got {mode})")
    try:
        sys.exit(main(mode))
    except PermissionError as e:
        log(f"AUTH ERROR: {e}")
        sys.exit(EXIT_FAIL)
