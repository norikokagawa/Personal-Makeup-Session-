"""
Metricool スケジューラ API

フィード投稿とストーリーズを別々の予約として作成する。
DRY_RUN では書き込み系 API を一切呼ばず、送るはずのペイロードだけを返す。

NOTE: エンドポイントとフィールド名は Metricool API (Advanced プラン) の
/v2/scheduler/posts に合わせている。本番移行前のテストで実レスポンスを
確認し、違いがあればここだけ直す。
"""
import requests

API = "https://app.metricool.com/api"
NETWORK = "instagram"
TYPE_FEED = "POST"
TYPE_STORY = "STORY"


class Metricool:
    def __init__(self, user_token, user_id, blog_id, timezone, dry_run=True):
        self.dry_run = dry_run
        self.tz = timezone
        self.params = {"userId": user_id, "blogId": blog_id}
        self.headers = {"X-Mc-Auth": user_token, "Content-Type": "application/json"}

    def _get(self, path, **params):
        r = requests.get(f"{API}{path}", headers=self.headers,
                         params={**self.params, **params}, timeout=60)
        if r.status_code in (401, 403):
            raise PermissionError(f"Metricool auth failed ({r.status_code}): token expired or revoked")
        r.raise_for_status()
        return r.json()

    def list_instagram_posts(self, day):
        """All Instagram posts (scheduled or published) on a local date 'YYYY-MM-DD'."""
        data = self._get("/v2/scheduler/posts",
                         start=f"{day}T00:00:00", end=f"{day}T23:59:59", timezone=self.tz)
        posts = data.get("data", data) if isinstance(data, dict) else data
        return [p for p in posts or []
                if any(pr.get("network") == NETWORK for pr in p.get("providers", []))]

    @staticmethod
    def post_type(post):
        return (post.get("instagramData") or {}).get("type", TYPE_FEED)

    @staticmethod
    def post_status(post):
        """'PUBLISHED' only once Instagram has the post; scheduled ones are 'PENDING'."""
        for pr in post.get("providers", []):
            if pr.get("network") == NETWORK:
                return pr.get("status") or "UNKNOWN"
        return "UNKNOWN"

    def normalize_image(self, url):
        if self.dry_run:
            return url
        data = self._get("/actions/normalize/image/url", url=url)
        return data if isinstance(data, str) else data.get("url", url)

    def build_payload(self, when_local, post_type, media_url, text, auto_publish):
        return {
            "publicationDate": {"dateTime": when_local, "timezone": self.tz},
            "text": text,
            "providers": [{"network": NETWORK}],
            "media": [media_url],
            "instagramData": {"type": post_type},
            "autoPublish": bool(auto_publish),
            # AUTO_PUBLISH=false の間は下書きとして作り、勝手に公開されないようにする
            "draft": not auto_publish,
            "shortener": False,
        }

    def create(self, payload):
        if self.dry_run:
            return {"dry_run": True, "payload": payload}
        r = requests.post(f"{API}/v2/scheduler/posts", headers=self.headers,
                          params=self.params, json=payload, timeout=60)
        if r.status_code in (401, 403):
            raise PermissionError(f"Metricool auth failed ({r.status_code})")
        r.raise_for_status()
        return r.json()
