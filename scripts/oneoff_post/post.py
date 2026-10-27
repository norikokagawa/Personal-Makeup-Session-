#!/usr/bin/env python3
"""
atelierR 単発投稿 — 募集告知など「今日のコラム」以外のフィード投稿を1本、指定した日時に投稿する。

Noriko が画像と文面を承認 → Claude が column-post ブランチに次を push:
  oneoff/requests/<id>.json
  {"id": "2026-10-27-sg-december",
   "publish_at": "now" または "2026-11-01T09:00+08:00",
   "caption": "...",
   "comments_off": true,
   "image_url": "<Canva export URL>"   # 省略可。oneoff/media/<id>/feed.jpg を一緒に push してもよい
   "dry_run": false}

prepare (push 直後, oneoff-post.yml):
  画像を JPEG にして oneoff/media/<id>/feed.jpg に保存。publish_at が過ぎていれば (now なら) そのまま投稿する。
publish (15分ごと, main の oneoff-publish.yml):
  publish_at を過ぎた未投稿のリクエストを投稿する。
結果は oneoff/results/<id>.json に保存し、同じ id は二度投稿しない。
"""
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sg_calendar"))
from instagram import Instagram, InstagramError  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "norikokagawa/Personal-Makeup-Session-")
BRANCH = os.environ.get("COLUMN_BRANCH", "column-post")
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "oneoff"
SGT = timezone(timedelta(hours=8))


def git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def commit_push(paths, msg):
    git("config", "user.name", "oneoff-post-bot")
    git("config", "user.email", "oneoff-post-bot@users.noreply.github.com")
    git("add", *[str(p) for p in paths])
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    git("commit", "-m", msg)
    for _ in range(3):
        if subprocess.run(["git", "push", "origin", f"HEAD:{BRANCH}"], cwd=ROOT).returncode == 0:
            return
        git("pull", "--rebase", "origin", BRANCH)
    raise RuntimeError("git push failed")


def is_dry(req):
    return str(req.get("dry_run", "false")).lower() == "true"


def due(req):
    at = str(req.get("publish_at", "now")).strip()
    if at.lower() == "now":
        return True
    t = datetime.fromisoformat(at)
    if t.tzinfo is None:
        t = t.replace(tzinfo=SGT)          # タイムゾーンなしはシンガポール時間とみなす
    return datetime.now(timezone.utc) >= t


def paths(rid):
    return BASE / "media" / rid / "feed.jpg", BASE / "results" / f"{rid}.json"


def raw_url(path):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path.relative_to(ROOT).as_posix()}"


def wait_public(url, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if requests.head(url, timeout=30).ok:
            return
        time.sleep(5)
    raise RuntimeError(f"image not reachable: {url}")


def ensure_image(req):
    feed_jpg, _ = paths(req["id"])
    if feed_jpg.exists():
        return feed_jpg
    if not req.get("image_url"):
        raise RuntimeError(f"{req['id']}: no image (image_url or {feed_jpg.relative_to(ROOT)})")
    r = requests.get(req["image_url"], timeout=120)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    feed_jpg.parent.mkdir(parents=True, exist_ok=True)
    im.save(feed_jpg, "JPEG", quality=95)
    print("image size:", im.size)
    if not is_dry(req):
        commit_push([feed_jpg], f"oneoff {req['id']}: image ready")
    return feed_jpg


def post(req):
    rid = req["id"]
    feed_jpg, result_path = paths(rid)
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    if result.get("feed_media_id"):
        print(f"{rid}: already posted — skip")
        return 0
    if is_dry(req):
        print(f"{rid}: dry_run — not posting")
        return 0
    url = raw_url(feed_jpg)
    wait_public(url)

    ig = Instagram(os.environ["IG_USER_ID"], os.environ["META_ACCESS_TOKEN"], dry_run=False)
    cid = ig.create_image(url, caption=req["caption"])
    ig.wait_finished(cid)
    result["feed_media_id"] = ig.publish(cid)
    result["published_at"] = datetime.now(SGT).isoformat(timespec="seconds")
    print("feed published:", result["feed_media_id"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2))
    commit_push([result_path], f"oneoff {rid}: published")

    problems = []
    if req.get("comments_off", True):
        try:
            result["comments_off"] = ig.disable_comments(result["feed_media_id"])
        except InstagramError as e:
            result["comments_off"] = False
            problems.append(f"comments off failed: {e}")
    result["problems"] = problems
    result_path.write_text(json.dumps(result, indent=2))
    commit_push([result_path], f"oneoff {rid}: done")
    print(json.dumps(result, indent=2))
    return 1 if problems else 0


def load(path):
    req = json.loads(Path(path).read_text(encoding="utf-8"))
    req.setdefault("id", Path(path).stem)
    return req


def prepare(req_path):
    req = load(req_path)
    ensure_image(req)
    if due(req):
        return post(req)
    print(f"{req['id']}: scheduled for {req['publish_at']}")
    return 0


def publish_due():
    rc = 0
    for p in sorted((BASE / "requests").glob("*.json")):
        req = load(p)
        _, result_path = paths(req["id"])
        if result_path.exists() and json.loads(result_path.read_text()).get("feed_media_id"):
            continue
        if is_dry(req) or not due(req):
            continue
        try:
            ensure_image(req)
            rc |= post(req)
        except Exception as e:  # 1本の失敗で他を止めない
            print(f"{req['id']}: FAILED {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    mode = sys.argv[1]
    sys.exit(publish_due() if mode == "publish" else prepare(sys.argv[2]))
