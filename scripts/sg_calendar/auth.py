"""
認証まわり (秘密情報は一切ログに出さない)

- Canva の refresh token は1回限り。更新のたびに新しい token が返るので、
  GitHub Secrets への保存に失敗したら必ず止めて通知する
  (既存 daily_post.py は保存失敗を「non-fatal」として続行するため、次回から無効な token が残る)。
- check(): 各サービスの認証が通るかだけを確認し、成功/失敗とエラーコードのみ返す。
"""
import base64
import os

import requests

GITHUB_API = "https://api.github.com"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class AuthError(PermissionError):
    pass


def _err(r):
    """Error code only (e.g. 'invalid_grant'); never the response body."""
    try:
        return r.json().get("error", str(r.status_code))
    except ValueError:
        return str(r.status_code)


def _gh_pat_headers():
    pat = os.environ.get("GH_PAT", "").strip()
    if not pat:
        raise AuthError("GH_PAT is not set (needed to save the rotated Canva refresh token)")
    return {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def _repo():
    return os.environ.get("GITHUB_REPOSITORY", "norikokagawa/Personal-Makeup-Session-")


def check_gh_pat():
    """GH_PAT can read the repo's Actions secrets public key (= has Secrets write access)."""
    r = requests.get(f"{GITHUB_API}/repos/{_repo()}/actions/secrets/public-key",
                     headers=_gh_pat_headers(), timeout=30)
    if not r.ok:
        raise AuthError(f"GH_PAT cannot manage Actions secrets ({r.status_code}); "
                        "regenerate it with 'Secrets: read and write' on this repository")
    return r.json()


def save_secret(name, value):
    from nacl import encoding, public
    key = check_gh_pat()
    box = public.SealedBox(public.PublicKey(key["key"].encode(), encoding.Base64Encoder()))
    enc = base64.b64encode(box.encrypt(value.encode())).decode()
    r = requests.put(f"{GITHUB_API}/repos/{_repo()}/actions/secrets/{name}", headers=_gh_pat_headers(),
                     json={"encrypted_value": enc, "key_id": key["key_id"]}, timeout=30)
    if not r.ok:
        raise AuthError(f"saving {name} failed ({r.status_code})")


def gmail_access_token():
    r = requests.post(GOOGLE_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"].strip(),
        "client_id": os.environ["GMAIL_CLIENT_ID"].strip(),
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"].strip(),
    }, timeout=30)
    if not r.ok:
        raise AuthError(f"Gmail token refresh failed ({r.status_code} {_err(r)}): "
                        "re-issue GMAIL_REFRESH_TOKEN (docs/SG_AUTH_SETUP.md)")
    return r.json()["access_token"]


def canva_access_token():
    """Refresh Canva and persist the rotated refresh token; stop if it cannot be saved."""
    check_gh_pat()                      # 先に保存できることを確かめてから token を消費する
    r = requests.post(CANVA_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["CANVA_REFRESH_TOKEN"].strip(),
        "client_id": os.environ["CANVA_CLIENT_ID"].strip(),
        "client_secret": os.environ["CANVA_CLIENT_SECRET"].strip(),
    }, timeout=30)
    if not r.ok:
        raise AuthError(f"Canva token refresh failed ({r.status_code} {_err(r)}): "
                        "re-issue CANVA_REFRESH_TOKEN (docs/SG_AUTH_SETUP.md)")
    data = r.json()
    if data.get("refresh_token"):
        try:
            save_secret("CANVA_REFRESH_TOKEN", data["refresh_token"])
        except AuthError as e:
            raise AuthError(f"Canva rotated its refresh token but it could not be saved ({e}); "
                            "CANVA_REFRESH_TOKEN must be re-issued") from None
    return data["access_token"]


def check(include_canva):
    """{service: "OK" | "FAIL: reason" | "SKIPPED: reason"} — no secret values."""
    out = {}

    def run(name, fn):
        try:
            fn()
            out[name] = "OK"
        except AuthError as e:
            out[name] = f"FAIL: {e}"
        except KeyError as e:
            out[name] = f"FAIL: {e} not set"
        except requests.RequestException as e:
            # URL にトークンが含まれ得るので、例外の種類だけを出す
            out[name] = f"FAIL: network error ({type(e).__name__})"

    run("GH_PAT (secrets write)", check_gh_pat)
    run("Gmail", gmail_access_token)
    if include_canva:
        run("Canva (refresh + rotate + save)", canva_access_token)
    else:
        out["Canva"] = "SKIPPED: set CHECK_CANVA=true (consumes and rotates the one-time refresh token)"
    if os.environ.get("IG_ACCESS_TOKEN"):
        def instagram():
            # 読み取りのみ: アカウント・権限・公開枠を確認する。投稿もコンテナ作成もしない
            from sg_calendar.instagram import (COMMENT_PERMISSION, REQUIRED_PERMISSIONS, Instagram,
                                               InstagramError)
            ig = Instagram(os.environ.get("IG_USER_ID", "").strip(), os.environ["IG_ACCESS_TOKEN"].strip())
            try:
                out["Instagram account"] = f"@{ig.account().get('username')}"
                granted = ig.permissions()
                missing = [p for p in REQUIRED_PERMISSIONS if p not in granted]
                out["Instagram permissions"] = ("OK" if not missing else f"MISSING {missing}") + \
                    f"; comments control: {'OK' if COMMENT_PERMISSION in granted else 'MISSING ' + COMMENT_PERMISSION}"
                used, total = ig.publishing_limit()
                out["Instagram publishing quota (24h)"] = f"{used}/{total}"
            except InstagramError as e:
                raise AuthError(str(e)) from None
            if missing:
                raise AuthError(f"missing permissions {missing}")
        run("Instagram (read-only)", instagram)
    else:
        out["Instagram"] = "SKIPPED: IG_ACCESS_TOKEN not set"
    if os.environ.get("META_ACCESS_TOKEN"):
        from sg_calendar.meta_check import run_check
        out["Meta (META_ACCESS_TOKEN, read-only)"] = run_check()
    if os.environ.get("METRICOOL_USER_TOKEN"):
        def metricool():
            r = requests.get("https://app.metricool.com/api/admin/simpleProfiles",
                             headers={"X-Mc-Auth": os.environ["METRICOOL_USER_TOKEN"].strip()},
                             params={"userId": os.environ.get("METRICOOL_USER_ID", "").strip()},
                             timeout=30)
            if not r.ok:
                raise AuthError(f"Metricool returned {r.status_code}")
            blog = os.environ.get("METRICOOL_BLOG_ID", "").strip()
            ids = {str(p.get("id")) for p in (r.json() if isinstance(r.json(), list) else [])}
            if blog and ids and blog not in ids:
                raise AuthError("METRICOOL_BLOG_ID is not one of this account's brands")
        run("Metricool", metricool)
    else:
        out["Metricool"] = "SKIPPED: METRICOOL_USER_TOKEN not set"
    return out
