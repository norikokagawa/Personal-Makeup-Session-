#!/usr/bin/env python3
"""
atelierR「今日のコラム」投稿 — フィード1枚＋ストーリーズ1枚を Instagram に直接投稿する。

前日: Noriko が記事を承認 → Claude が column/requests/<投稿日>.json を push
      → prepare: 画像を JPEG 化して column/media/<投稿日>/ に保存 (投稿しない)
当日 05:00 SGT: main の column-publish.yml が publish を実行 → フィード・コメントオフ・ストーリーズ

  {"date": "2026-10-17", "title": "...", "feed_url": "<Canva export URL>",
   "story_url": "<Canva export URL>", "caption": "...", "dry_run": false}

1. Canva の書き出し画像をダウンロードし JPEG に変換 (Graph API は JPEG のみ)
2. column/media/<日付>/ に保存して公開 URL (raw.githubusercontent.com) を作る
3. フィード投稿 → コメントオフ → ストーリーズ投稿
4. 結果を column/results/<日付>.json に保存 (同じ日付は二度投稿しない)
"""
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sg_calendar"))
from instagram import Instagram, InstagramError  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "norikokagawa/Personal-Makeup-Session-")
BRANCH = os.environ.get("COLUMN_BRANCH", "column-post")
ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def commit_push(paths, msg):
    git("config", "user.name", "column-post-bot")
    git("config", "user.email", "column-post-bot@users.noreply.github.com")
    git("add", *[str(p) for p in paths])
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if r.returncode == 0:
        return
    git("commit", "-m", msg)
    for _ in range(3):
        if subprocess.run(["git", "push", "origin", f"HEAD:{BRANCH}"], cwd=ROOT).returncode == 0:
            return
        git("pull", "--rebase", "origin", BRANCH)
    raise RuntimeError("git push failed")


def to_jpeg(url, dest):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=95)
    return im.size


def raw_url(path):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path.relative_to(ROOT).as_posix()}"


def wait_public(url, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.head(url, timeout=30)
        if r.ok:
            return
        time.sleep(5)
    raise RuntimeError(f"image not reachable: {url}")


def prepare(req_path):
    """push 直後: Canva の書き出し画像を JPEG にして保存する (URL は数時間で切れるため前日に確保)。投稿はしない。"""
    req = json.loads(Path(req_path).read_text(encoding="utf-8"))
    day = req["date"]
    media_dir = ROOT / "column" / "media" / day
    feed_jpg, story_jpg = media_dir / "feed.jpg", media_dir / "story.jpg"
    print("feed size:", to_jpeg(req["feed_url"], feed_jpg))
    print("story size:", to_jpeg(req["story_url"], story_jpg))
    if str(req.get("dry_run", "false")).lower() == "true":
        print("DRY_RUN: images converted, not saved")
        return 0
    commit_push([feed_jpg, story_jpg], f"column {day}: images ready")
    return 0


def wait_until_5am():
    """GitHub の定時実行は早めに起動するので、05:00 SGT まで待つ (最大50分)。"""
    from datetime import datetime, timedelta, timezone
    sgt = timezone(timedelta(hours=8))
    now = datetime.now(sgt)
    target = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if now.hour < 4 and (target - now).total_seconds() <= 3000:
        wait = (target - now).total_seconds()
        print(f"waiting {int(wait)}s until 05:00 SGT")
        time.sleep(wait)
    return datetime.now(sgt).strftime("%Y-%m-%d")


def publish_today():
    """05:00 SGT: 今日の日付のリクエストがあり、画像が準備済みで、未投稿なら投稿する。"""
    day = wait_until_5am()
    req_path = ROOT / "column" / "requests" / f"{day}.json"
    if not req_path.exists():
        print(f"{day}: no request — nothing to post")
        return 0
    req = json.loads(req_path.read_text(encoding="utf-8"))
    if str(req.get("dry_run", "false")).lower() == "true":
        print(f"{day}: dry_run request — skip")
        return 0
    return post(day, req)


def post(day, req):
    result_path = ROOT / "column" / "results" / f"{day}.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    if result.get("feed_media_id") and result.get("story_media_id"):
        print(f"{day}: already posted — skip")
        return 0
    media_dir = ROOT / "column" / "media" / day
    feed_jpg, story_jpg = media_dir / "feed.jpg", media_dir / "story.jpg"
    if not (feed_jpg.exists() and story_jpg.exists()):
        raise RuntimeError(f"{day}: images not prepared")
    feed_u, story_u = raw_url(feed_jpg), raw_url(story_jpg)
    wait_public(feed_u)
    wait_public(story_u)

    ig = Instagram(os.environ["IG_USER_ID"], os.environ["META_ACCESS_TOKEN"], dry_run=False)
    problems = []

    if not result.get("feed_media_id"):
        cid = ig.create_image(feed_u, caption=req["caption"])
        ig.wait_finished(cid)
        result["feed_media_id"] = ig.publish(cid)
        print("feed published:", result["feed_media_id"])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2))
        commit_push([result_path], f"column {day}: feed published")
    try:
        result["comments_off"] = ig.disable_comments(result["feed_media_id"])
    except InstagramError as e:
        result["comments_off"] = False
        problems.append(f"comments off failed: {e}")

    if not result.get("story_media_id"):
        try:
            cid = ig.create_image(story_u, story=True)
            ig.wait_finished(cid)
            result["story_media_id"] = ig.publish(cid)
            print("story published:", result["story_media_id"])
        except InstagramError as e:
            problems.append(f"story failed: {e}")

    result["problems"] = problems
    result_path.write_text(json.dumps(result, indent=2))
    commit_push([result_path], f"column {day}: done")
    print(json.dumps(result, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    mode = sys.argv[1]
    sys.exit(publish_today() if mode == "publish" else prepare(sys.argv[2]))
