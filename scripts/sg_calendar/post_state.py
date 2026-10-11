"""
投稿状態の管理 (二重投稿防止)

フィード (FEED)・ストーリーズ1 (STORY_1)・ストーリーズ2 (STORY_2) を個別に管理する。
状態は instagram-media ブランチの records/<日付>.json に、遷移のたびに先に保存する。

  pending ──コンテナ作成──▶ prepared ──公開リクエスト直前に保存──▶ publishing ──▶ published
     ▲                         │                                    │
     └──── failed ◀────────────┴──── 確定的なエラー ──────────────────┘

再実行時の判断 (Instagram 側のコンテナ状態を正とする):
  published                      → 何もしない (コメントオフ未完了なら再試行のみ)
  publishing + コンテナ PUBLISHED → 公開済みとして記録を直す (再投稿しない)
  publishing + コンテナ FINISHED  → 未公開と確定。同じコンテナで公開し直す (再投稿にならない)
  prepared/publishing + EXPIRED/ERROR → 新しいコンテナを作り直す
  failed                         → MAX_ATTEMPTS 回まで再試行、超えたら停止・通知
通信エラーなど「届いたか不明」の公開失敗は publishing のまま残し、次回の実行で上の規則で確定させる。
"""
from datetime import datetime, timezone

from sg_calendar.instagram import InstagramError

MAX_ATTEMPTS = 3
ITEMS = ("FEED", "STORY_1", "STORY_2")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Poster:
    """
    ig      : Instagram client (or a fake in tests)
    record  : dict loaded from records/<day>.json ({} when none)
    save    : callable(record) that persists the record durably (GitHub branch in production)
    publish : True only when DRY_RUN=false and AUTO_PUBLISH=true
    prepare : True when containers may be created (DRY_RUN=false, or IG_PROBE=true)
    """

    def __init__(self, ig, record, save, publish, prepare, wait_until=lambda: None):
        self.ig, self.rec, self._save = ig, record, save
        self.publish_allowed, self.prepare_allowed = publish, prepare
        self.wait_until = wait_until
        self.rec.setdefault("items", {})

    def _set(self, key, **fields):
        item = self.rec["items"].setdefault(key, {"state": "pending", "attempts": 0})
        item.update(fields, updated_at=_now())
        self._save(self.rec)
        return item

    def item(self, key):
        return self.rec["items"].get(key, {"state": "pending", "attempts": 0})

    # ── reconcile what a previous run left behind ──
    def reconcile(self, key):
        it = self.item(key)
        if it["state"] in ("prepared", "publishing") and it.get("container"):
            status = self.ig.container_status(it["container"])
            if status == "PUBLISHED":
                return self._set(key, state="published", media_id=it.get("media_id"),
                                 note="confirmed from container status after interrupted run")
            if status in ("EXPIRED", "ERROR"):
                return self._set(key, state="pending", container=None, children=None,
                                 note=f"container {status}; will be recreated")
            if it["state"] == "publishing" and status == "FINISHED":
                return self._set(key, state="prepared", note="publish not applied; safe to retry")
        return it

    # ── one item ──
    def run_item(self, key, prepare_fn):
        """prepare_fn(ig) → (container_id, children) for this item."""
        it = self.reconcile(key)
        if it["state"] == "published":
            return it
        if it["state"] == "failed" and it.get("attempts", 0) >= MAX_ATTEMPTS:
            raise InstagramError(f"{key}: failed {MAX_ATTEMPTS} times; manual check needed")
        if it["state"] == "publishing":
            raise InstagramError(f"{key}: publish result unknown (container status not final); "
                                 "will be re-checked on the next run")

        if it["state"] in ("pending", "failed"):
            if not self.prepare_allowed:
                return self._set(key, state="pending", note="dry run: nothing created")
            try:
                container, children = prepare_fn(self.ig)
                self.ig.wait_finished(container)
            except InstagramError as e:
                self._set(key, state="failed", attempts=it.get("attempts", 0) + 1, error=str(e))
                raise
            it = self._set(key, state="prepared", container=container, children=children, error=None)

        if not self.publish_allowed:
            return it
        self.wait_until()
        self._set(key, state="publishing", attempts=it.get("attempts", 0) + 1)
        try:
            media_id = self.ig.publish(it["container"])
        except InstagramError as e:
            if e.ambiguous:
                self._set(key, error=str(e), note="publish result unknown; next run checks the container")
            else:
                self._set(key, state="failed", error=str(e))
            raise
        return self._set(key, state="published", media_id=media_id, published_at=_now(), error=None)

    def comments_off(self, key):
        it = self.item(key)
        if it["state"] != "published" or it.get("comments") == "off" or not it.get("media_id"):
            return it.get("comments")
        try:
            ok = self.ig.disable_comments(it["media_id"])
            self._set(key, comments="off" if ok else "failed")
        except InstagramError as e:
            self._set(key, comments=f"failed: {e}")
        return self.item(key).get("comments")

    def summary(self):
        return {k: {f: v for f, v in self.item(k).items() if f in ("state", "attempts", "media_id",
                                                                   "comments", "error", "note")}
                for k in ITEMS}
