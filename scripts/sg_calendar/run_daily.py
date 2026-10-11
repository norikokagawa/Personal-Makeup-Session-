#!/usr/bin/env python3
"""
atelierR Singapore November calendar — daily Instagram run (Asia/Singapore)

1. Gmail: STORES 予約メールから予約番号単位の台帳を作る (2026-11-06〜30)
2. 台帳と Canva 1ページ目の承認済み状態 (config/sg_nov_page1.json) を照合
   - 差分・不明点があれば投稿を止め、レポートを出して終了 (exit 2)
     → Canva の横線更新はプレビュー承認後に行い、承認済み状態を更新する
3. Canva 正式エクスポート (PNG / pro / 1080x1350) → ストーリーズ 1080x1920 を生成・検証
4. Metricool: 同日の既存投稿を確認し、フィードとストーリーズを別々に予約

安全設定: DRY_RUN=true (既定) は書き込みを一切しない。
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
from sg_calendar import images, ledger as ledger_mod  # noqa: E402
from sg_calendar.metricool import Metricool, TYPE_FEED, TYPE_STORY  # noqa: E402

SGT = ZoneInfo("Asia/Singapore")
ROOT = Path(__file__).resolve().parents[2]
GRID_PATH = ROOT / "config" / "sg_nov_page1.json"
CAPTION_PATH = ROOT / "config" / "sg_caption.txt"
OUT = Path(os.environ.get("SG_OUT_DIR", ROOT / "out"))

PERIOD = ("2026-11-06", "2026-11-30")
POST_TIME = "05:00"

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
AUTO_PUBLISH = os.environ.get("AUTO_PUBLISH", "false").lower() == "true"

CANVA_API = "https://api.canva.com/rest/v1"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
GITHUB_API = "https://api.github.com"
MEDIA_BRANCH = os.environ.get("MEDIA_BRANCH", "instagram-media")

EXIT_OK, EXIT_FAIL, EXIT_NEEDS_APPROVAL = 0, 1, 2


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
    tok = gmail_token()
    h = {"Authorization": f"Bearer {tok}"}
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
        m = requests.get(f"{GMAIL_API}/users/me/messages/{mid}", headers=h,
                         params={"format": "full"}, timeout=30).json()
        hdrs = {x["name"]: x["value"] for x in m["payload"].get("headers", [])}
        received = datetime.fromtimestamp(int(m["internalDate"]) / 1000, ZoneInfo("UTC")).isoformat()
        ev = ledger_mod.parse_message(mid, received, hdrs.get("Subject", ""), _body_text(m["payload"]))
        if ev:
            events.append(ev)
    log(f"Gmail: {len(ids)} messages scanned, {len(events)} reservation events")
    return events


def relevant_inquiries(inquiries):
    keys = ("nov", "11月", "november", "singapore", "cancel", "change", "reschedule")
    return [i for i in inquiries if any(k in i.text.lower() for k in keys)]


# ── Canva (Connect API, read/export only) ──────────────────────────────────

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


def export_page1(design_id, dest):
    h = {"Authorization": f"Bearer {canva_token()}"}
    r = requests.post(f"{CANVA_API}/exports", headers=h, timeout=60, json={
        "design_id": design_id,
        "format": {"type": "png", "pages": [1], "width": 1080, "height": 1350,
                   "export_quality": "pro", "lossless": True},
    })
    r.raise_for_status()
    job = r.json()["job"]["id"]
    for _ in range(40):
        time.sleep(3)
        s = requests.get(f"{CANVA_API}/exports/{job}", headers=h, timeout=30).json()["job"]
        if s["status"] == "success":
            url = s["urls"][0]
            img = requests.get(url, timeout=60)
            img.raise_for_status()
            dest.write_bytes(img.content)
            return url
        if s["status"] == "failed":
            raise RuntimeError(f"Canva export failed: {s}")
    raise TimeoutError("Canva export timed out")


# ── Public media + run records (GitHub branch) ─────────────────────────────

def _gh():
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json"}


def _ensure_media_branch(repo):
    r = requests.get(f"{GITHUB_API}/repos/{repo}/branches/{MEDIA_BRANCH}", headers=_gh(), timeout=30)
    if r.ok:
        return
    main = requests.get(f"{GITHUB_API}/repos/{repo}/git/ref/heads/main", headers=_gh(), timeout=30).json()
    requests.post(f"{GITHUB_API}/repos/{repo}/git/refs", headers=_gh(), timeout=30, json={
        "ref": f"refs/heads/{MEDIA_BRANCH}", "sha": main["object"]["sha"]}).raise_for_status()


def put_file(repo, path, content_bytes, message):
    """Write a file to the media branch; returns its public raw URL."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    cur = requests.get(url, headers=_gh(), params={"ref": MEDIA_BRANCH}, timeout=30)
    body = {"message": message, "branch": MEDIA_BRANCH,
            "content": base64.b64encode(content_bytes).decode()}
    if cur.ok:
        body["sha"] = cur.json()["sha"]
    requests.put(url, headers=_gh(), json=body, timeout=60).raise_for_status()
    return f"https://raw.githubusercontent.com/{repo}/{MEDIA_BRANCH}/{path}"


def read_record(repo, day):
    r = requests.get(f"{GITHUB_API}/repos/{repo}/contents/records/{day}.json",
                     headers=_gh(), params={"ref": MEDIA_BRANCH}, timeout=30)
    if not r.ok:
        return {}
    return json.loads(base64.b64decode(r.json()["content"]))


# ── Scheduling ─────────────────────────────────────────────────────────────

def publish_time(now):
    """Today 05:00 SGT, or the nearest feasible time (+10 min, rounded) if it has passed."""
    target = now.replace(hour=5, minute=0, second=0, microsecond=0)
    if now <= target - timedelta(minutes=5):
        return target
    t = now + timedelta(minutes=10)
    return t.replace(minute=(t.minute // 5) * 5, second=0, microsecond=0)


def already_posted(existing, record, post_type):
    """Same-day duplicate check: our own record first, then Metricool's calendar."""
    if record.get(post_type, {}).get("metricool_id"):
        return True
    return any(Metricool.post_type(p) == post_type for p in existing)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(SGT)
    day = now.strftime("%Y-%m-%d")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"run_at": now.isoformat(), "dry_run": DRY_RUN, "auto_publish": AUTO_PUBLISH,
              "day": day, "status": None}
    log(f"=== SG calendar run {now:%Y-%m-%d %H:%M} SGT | DRY_RUN={DRY_RUN} AUTO_PUBLISH={AUTO_PUBLISH} ===")

    def finish(status, code):
        report["status"] = status
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        log(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    # 1. Gmail ledger
    grid = json.loads(GRID_PATH.read_text())
    lg = ledger_mod.build_ledger(fetch_events(), *PERIOD)
    report["ledger"] = {no: {"state": r["state"], "slot": list(r["slot"])}
                        for no, r in sorted(lg.reservations.items(), key=lambda kv: kv[1]["slot"])}
    # レポートは Issue に載るので本文 (氏名・連絡先を含む) は入れない。Gmail で message_id を開いて確認する
    report["inquiries"] = [{"received_at": i.received_at, "message_id": i.message_id}
                           for i in relevant_inquiries(lg.inquiries)]
    report["anomalies"] = lg.anomalies
    covered = set(grid["covered_dates"])
    report["bookings_outside_page1"] = sorted(
        f"{r['slot'][0]} {r['slot'][1]}" for r in lg.reservations.values()
        if r["state"] != "cancelled" and r["slot"][0] not in covered)

    # 2. Ledger vs approved Canva state
    strike, unstrike, unknown = ledger_mod.diff_against_design(lg, grid)
    report["canva_diff"] = {"strike": strike, "unstrike": unstrike, "no_cell_for_booking": unknown}
    if lg.anomalies or unknown:
        return finish("STOPPED_UNCLEAR_BOOKINGS", EXIT_NEEDS_APPROVAL)
    if strike or unstrike:
        # 予約が変わったのに Canva 未承認 → 古いカレンダーは投稿しない
        return finish("STOPPED_CANVA_UPDATE_NEEDS_APPROVAL", EXIT_NEEDS_APPROVAL)

    # 3. Images
    feed = OUT / f"sg_feed_{day}.png"
    story = OUT / f"sg_story_{day}.png"
    if os.environ.get("FEED_IMAGE"):           # ローカルテスト用: 既に書き出した正式エクスポート
        feed.write_bytes(Path(os.environ["FEED_IMAGE"]).read_bytes())
    else:
        export_page1(grid["design_id"], feed)
    images.verify_feed(feed)
    images.make_story(feed, story)
    report["images"] = {"feed": str(feed), "story": str(story)}

    # 4. Metricool
    caption = CAPTION_PATH.read_text().strip()
    when = publish_time(now)
    report["publish_at"] = when.isoformat()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    mc = Metricool(os.environ.get("METRICOOL_USER_TOKEN", ""), os.environ.get("METRICOOL_USER_ID", ""),
                   os.environ.get("METRICOOL_BLOG_ID", ""), "Asia/Singapore", dry_run=DRY_RUN)

    if DRY_RUN:
        existing, record = [], {}
        feed_url, story_url = f"(dry-run) {feed.name}", f"(dry-run) {story.name}"
        if os.environ.get("METRICOOL_USER_TOKEN"):
            existing = mc.list_instagram_posts(when.strftime("%Y-%m-%d"))   # 読み取りのみ
    else:
        _ensure_media_branch(repo)
        record = read_record(repo, day)
        existing = mc.list_instagram_posts(when.strftime("%Y-%m-%d"))
        feed_url = put_file(repo, f"media/{day}/feed.png", feed.read_bytes(), f"SG feed image {day}")
        story_url = put_file(repo, f"media/{day}/story.png", story.read_bytes(), f"SG story image {day}")

    report["existing_same_day"] = [{"type": Metricool.post_type(p), "status": Metricool.post_status(p),
                                    "id": p.get("id")} for p in existing]
    results = {}
    for post_type, media, text in ((TYPE_FEED, feed_url, caption), (TYPE_STORY, story_url, "")):
        if already_posted(existing, record, post_type):
            results[post_type] = {"skipped": "already scheduled/published today"}
            continue
        payload = mc.build_payload(when.strftime("%Y-%m-%dT%H:%M:00"), post_type,
                                   mc.normalize_image(media), text, AUTO_PUBLISH)
        res = mc.create(payload)
        results[post_type] = {"scheduled": not DRY_RUN, "published": False,
                              "draft": payload["draft"], "metricool_id": res.get("id"),
                              "response": res if DRY_RUN else None}
    report["metricool"] = results
    # Instagram 公開完了は予約時点では未確定。翌日の実行で status を確認して記録する
    report["comments_off"] = "manual: Metricool API has no comment-disable option"

    if not DRY_RUN:
        put_file(repo, f"records/{day}.json",
                 json.dumps({**record, **results}, ensure_ascii=False, indent=2).encode(),
                 f"SG run record {day}")
    return finish("DRY_RUN_OK" if DRY_RUN else "SCHEDULED", EXIT_OK)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PermissionError as e:
        log(f"AUTH ERROR: {e}")
        sys.exit(EXIT_FAIL)
