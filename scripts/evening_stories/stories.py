#!/usr/bin/env python3
"""
atelierR 夜のストーリーズ — 毎晩 19:00 SGT に、コスメの縦長写真を 3〜4 枚ランダムにストーリーズへ投稿する。
文字・リンク・スタンプなし。写真だけ。

写真のストック: column-post ブランチの stories/pool/*.jpg (1080x1920 に揃えて保存)
  追加: stories/import/<id>.json を push → import (evening-stories-import.yml) が画像を取り込む
        {"photos": [{"name": "IMG_7269", "url": "<Canva export URL>"}, ...]}
  外したい写真は stories/pool/ から消す。
投稿: main の evening-stories.yml が 18:30 / 18:48 SGT に起動 → 19:00 まで待って publish。
  stories/history.json に日付ごとの投稿を記録し、同じ日に二度投稿しない。
  直近に出した写真はなるべく避けて選ぶ (ストックが少なければ古い順に再登場)。
設定: stories/config.json  {"enabled": true, "count_min": 3, "count_max": 4, "avoid_days": 4,
                            "publish_time": "19:00", "gap_seconds": 20}
"""
import io
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sg_calendar"))
from instagram import Instagram  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "norikokagawa/Personal-Makeup-Session-")
BRANCH = os.environ.get("COLUMN_BRANCH", "column-post")
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "stories"
POOL = BASE / "pool"
HISTORY = BASE / "history.json"
SGT = timezone(timedelta(hours=8))
W, H = 1080, 1920


def git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def commit_push(paths, msg):
    git("config", "user.name", "evening-stories-bot")
    git("config", "user.email", "evening-stories-bot@users.noreply.github.com")
    git("add", *[str(p) for p in paths])
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    git("commit", "-m", msg)
    for _ in range(3):
        if subprocess.run(["git", "push", "origin", f"HEAD:{BRANCH}"], cwd=ROOT).returncode == 0:
            return
        git("pull", "--rebase", "origin", BRANCH)
    raise RuntimeError("git push failed")


def config():
    cfg = {"enabled": True, "count_min": 3, "count_max": 4, "avoid_days": 4,
           "publish_time": "19:00", "gap_seconds": 20}
    p = BASE / "config.json"
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    return cfg


def to_story(raw):
    """縦 9:16 (1080x1920) に中央トリミングして JPEG に。"""
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    return ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.5))


# ── import ─────────────────────────────────────────────────────────────────

def import_photos(req_path):
    req = json.loads(Path(req_path).read_text(encoding="utf-8"))
    POOL.mkdir(parents=True, exist_ok=True)
    added = []
    for ph in req["photos"]:
        dest = POOL / f"{ph['name']}.jpg"
        r = requests.get(ph["url"], timeout=120)
        r.raise_for_status()
        im = to_story(r.content)
        im.save(dest, "JPEG", quality=92)
        added.append(dest)
        print("imported:", dest.name)
    commit_push(added, f"stories: import {len(added)} photos [skip ci]")


# ── publish ────────────────────────────────────────────────────────────────

def raw_url(path):
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path.relative_to(ROOT).as_posix()}"


def wait_public(url, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if requests.head(url, timeout=30).ok:
            return
        time.sleep(5)
    raise RuntimeError(f"image not reachable: {url}")


def pick(names, history, cfg, today):
    n = random.randint(cfg["count_min"], cfg["count_max"])
    last_used = {}
    for day, rec in history.items():
        for name in rec.get("photos", []):
            last_used[name] = max(last_used.get(name, ""), day)
    cutoff = (today - timedelta(days=cfg["avoid_days"])).isoformat()
    fresh = [x for x in names if last_used.get(x, "") < cutoff]
    random.shuffle(fresh)
    chosen = fresh[:n]
    if len(chosen) < n:  # ストックが少ないときは、出してから日が経っている順に足す
        rest = sorted((x for x in names if x not in chosen), key=lambda x: (last_used.get(x, ""), random.random()))
        chosen += rest[: n - len(chosen)]
    return chosen


def publish(force=False):
    cfg = config()
    if not cfg["enabled"]:
        print("disabled in stories/config.json — skip")
        return 0
    now = datetime.now(SGT)
    today = now.date()
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    rec = history.get(today.isoformat(), {})
    if rec.get("done"):
        print("already posted today — skip")
        return 0

    names = sorted(p.stem for p in POOL.glob("*.jpg"))
    if not names:
        print("no photos in stories/pool — skip")
        return 0

    hh, mm = map(int, cfg["publish_time"].split(":"))
    at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if not force:
        if now < at - timedelta(minutes=45):
            print(f"too early ({now:%H:%M}) — skip")
            return 0
        if now > at + timedelta(hours=2):
            print(f"too late ({now:%H:%M}) — skip today")
            return 0

    if not rec.get("photos"):
        rec = {"photos": pick(names, history, cfg, today), "media_ids": []}
        history[today.isoformat()] = rec
    print("photos:", rec["photos"])

    if not force:
        wait = (at - datetime.now(SGT)).total_seconds()
        if wait > 0:
            print(f"waiting {int(wait)}s until {cfg['publish_time']} SGT")
            time.sleep(wait)

    ig = Instagram(os.environ["IG_USER_ID"], os.environ["META_ACCESS_TOKEN"], dry_run=False)
    for i, name in enumerate(rec["photos"]):
        if i < len(rec["media_ids"]):
            continue  # 前回の実行で投稿済み
        url = raw_url(POOL / f"{name}.jpg")
        wait_public(url)
        cid = ig.create_image(url, story=True)
        ig.wait_finished(cid)
        rec["media_ids"].append(ig.publish(cid))
        print(f"story {i + 1}/{len(rec['photos'])}: {name} → {rec['media_ids'][-1]}")
        HISTORY.write_text(json.dumps(history, indent=2, sort_keys=True))
        commit_push([HISTORY], f"stories {today}: {i + 1}/{len(rec['photos'])} [skip ci]")
        if i < len(rec["photos"]) - 1:
            time.sleep(cfg["gap_seconds"])

    rec["done"] = True
    rec["published_at"] = datetime.now(SGT).isoformat(timespec="seconds")
    # 履歴は直近60日分だけ残す
    keep = (today - timedelta(days=60)).isoformat()
    history = {d: r for d, r in history.items() if d >= keep}
    HISTORY.write_text(json.dumps(history, indent=2, sort_keys=True))
    commit_push([HISTORY], f"stories {today}: done [skip ci]")
    return 0


def queue():
    """今日の分を選び、oneoff/requests/ に type: story のリクエストとして書き出す (push すると即投稿)。
    GitHub の定時実行が大きく遅れることがあるため、Claude の定時タスクが 19:00 SGT にこれを実行して push する。"""
    cfg = config()
    if not cfg["enabled"]:
        print("disabled — skip")
        return []
    today = datetime.now(SGT).date()
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    if history.get(today.isoformat(), {}).get("done"):
        print("already posted today — skip")
        return []
    names = sorted(p.stem for p in POOL.glob("*.jpg"))
    photos = pick(names, history, cfg, today)
    history[today.isoformat()] = {"photos": photos, "via": "oneoff", "done": True}
    HISTORY.write_text(json.dumps(history, indent=2, sort_keys=True))
    out = []
    for i, name in enumerate(photos, 1):
        rid = f"{today}-evening-{i}"
        f = ROOT / "oneoff" / "requests" / f"{rid}.json"
        f.write_text(json.dumps({"id": rid, "publish_at": "now", "type": "story", "caption": "",
                                 "image_url": raw_url(POOL / f"{name}.jpg"), "dry_run": False}, indent=2))
        out.append(f)
    print("queued:", photos)
    return out


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "queue":
        queue()
    elif mode == "import":
        import_photos(sys.argv[2])
    else:
        sys.exit(publish(force="--now" in sys.argv))
