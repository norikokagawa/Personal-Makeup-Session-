"""
認証まわり (秘密情報は一切ログに出さない)

毎日の実行に必要なのは Gmail (予約メールの読み取り) と Meta (Instagram 投稿) の2つだけ。
check(): 各サービスの認証が通るかだけを確認し、成功/失敗とエラーコードのみ返す。
"""
import os

import requests

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class AuthError(PermissionError):
    pass


def _err(r):
    """Error code only (e.g. 'invalid_grant'); never the response body."""
    try:
        return r.json().get("error", str(r.status_code))
    except ValueError:
        return str(r.status_code)


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


def check():
    """{service: "OK" | "FAIL: reason" | details} — no secret values."""
    out = {}
    try:
        gmail_access_token()
        out["Gmail"] = "OK"
    except AuthError as e:
        out["Gmail"] = f"FAIL: {e}"
    except KeyError as e:
        out["Gmail"] = f"FAIL: {e} not set"
    except requests.RequestException as e:
        # URL にトークンが含まれ得るので、例外の種類だけを出す
        out["Gmail"] = f"FAIL: network error ({type(e).__name__})"
    if os.environ.get("META_ACCESS_TOKEN"):
        from sg_calendar.meta_check import run_check
        meta = run_check()
        out["Meta (META_ACCESS_TOKEN, read-only)"] = meta
        if not str(meta.get("verdict", "")).startswith("READY"):
            out["Meta verdict"] = f"FAIL: {meta.get('verdict')}"
    else:
        out["Meta"] = "FAIL: META_ACCESS_TOKEN not set"
    return out
