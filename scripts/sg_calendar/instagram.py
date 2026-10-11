"""
Instagram 公式 API (Graph API / Facebook ログイン方式) — 既存 daily_post.py と同じ方式を再利用

  コンテナ作成 → 処理完了 (FINISHED) を待つ → 公開 (media_publish)

既存実装との違い:
- コンテナ ID を記録してから公開するので、途中で止まっても再実行で二重投稿しない
  (公開済みコンテナの status_code は PUBLISHED になり、再公開できない)
- ストーリーズ (media_type=STORIES)、公開後のコメントオフ (comment_enabled=false) に対応
- dry_run では書き込み系 (POST) を一切呼ばない。probe=True のときだけ非公開のコンテナ作成まで行う
- エラーにはトークンを含めない (Graph API のエラーコードのみ)
"""
import os
import time

import requests

GRAPH = f"https://graph.facebook.com/{os.environ.get('IG_GRAPH_VERSION', 'v23.0')}"
REQUIRED_PERMISSIONS = ("instagram_basic", "instagram_content_publish", "pages_show_list")
COMMENT_PERMISSION = "instagram_manage_comments"


class InstagramError(RuntimeError):
    """ambiguous=True: リクエストが届いたか不明 (通信エラー)。公開処理では「未公開」と決めつけない。"""

    def __init__(self, msg, ambiguous=False):
        super().__init__(msg)
        self.ambiguous = ambiguous


def _raise(r, what):
    try:
        err = r.json().get("error") or {}
    except ValueError:
        err = {}
    raise InstagramError(f"{what} failed (HTTP {r.status_code}, code={err.get('code')}, "
                         f"subcode={err.get('error_subcode')}, type={err.get('type')})")


class Instagram:
    def __init__(self, user_id, token, dry_run=True, probe=False):
        self.uid = user_id
        self.token = token
        self.dry_run = dry_run
        self.probe = probe          # DRY_RUN 中でも非公開コンテナ作成までは許可する (公開はしない)

    # ── read ──
    def _get(self, path, **params):
        try:
            r = requests.get(f"{GRAPH}/{path}", params={**params, "access_token": self.token}, timeout=60)
        except requests.RequestException as e:
            raise InstagramError(f"GET {path.split('?')[0]}: network error ({type(e).__name__})") from None
        if not r.ok:
            _raise(r, f"GET {path}")
        return r.json()

    def account(self):
        return self._get(self.uid, fields="username,name")

    def permissions(self):
        data = self._get("me/permissions").get("data", [])
        return sorted(p["permission"] for p in data if p.get("status") == "granted")

    def publishing_limit(self):
        d = (self._get(f"{self.uid}/content_publishing_limit", fields="quota_usage,config").get("data") or [{}])[0]
        return d.get("quota_usage"), (d.get("config") or {}).get("quota_total")

    def media_since(self, since_ts):
        """Feed media published since a unix timestamp."""
        out = self._get(f"{self.uid}/media", fields="id,timestamp,media_type,caption", limit=25, since=since_ts)
        return out.get("data", [])

    def stories(self):
        """Stories currently live (last 24h)."""
        return self._get(f"{self.uid}/stories", fields="id,timestamp,media_type").get("data", [])

    def container_status(self, container_id):
        return self._get(container_id, fields="status_code").get("status_code", "UNKNOWN")

    # ── write ──
    def _post(self, path, data, what, allow_in_probe=False):
        if self.dry_run and not (self.probe and allow_in_probe):
            return None
        try:
            r = requests.post(f"{GRAPH}/{path}", data={**data, "access_token": self.token}, timeout=120)
        except requests.RequestException as e:
            raise InstagramError(f"{what}: network error ({type(e).__name__})", ambiguous=True) from None
        if not r.ok:
            _raise(r, what)
        return r.json()

    def create_image(self, image_url, caption=None, carousel_item=False, story=False):
        data = {"image_url": image_url}
        if caption:
            data["caption"] = caption
        if carousel_item:
            data["is_carousel_item"] = "true"
        if story:
            data["media_type"] = "STORIES"
        res = self._post(f"{self.uid}/media", data, "create container", allow_in_probe=True)
        return res and res["id"]

    def create_carousel(self, children, caption):
        res = self._post(f"{self.uid}/media", {"media_type": "CAROUSEL", "children": ",".join(children),
                                               "caption": caption}, "create carousel", allow_in_probe=True)
        return res and res["id"]

    def wait_finished(self, container_id, timeout=300):
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.container_status(container_id)
            if status in ("FINISHED", "PUBLISHED"):
                return status
            if status in ("ERROR", "EXPIRED"):
                raise InstagramError(f"container {status}")
            time.sleep(5)
        raise InstagramError("container processing timed out")

    def publish(self, container_id):
        res = self._post(f"{self.uid}/media_publish", {"creation_id": container_id}, "publish")
        return res and res["id"]

    def disable_comments(self, media_id):
        res = self._post(media_id, {"comment_enabled": "false"}, "disable comments")
        return bool(res and res.get("success"))
