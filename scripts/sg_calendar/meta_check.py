"""
META_ACCESS_TOKEN の読み取り専用接続テスト (投稿・コンテナ作成は一切しない)

報告するのは: トークンの種類・アプリ ID・有効期限・権限、アクセスできる Facebook ページと
連携 Instagram アカウント、@r.makeup.session の公開枠、既存 IG_USER_ID との一致 (一致/不一致のみ)。
トークン値や IG_USER_ID の値は出力しない。
"""
import os
from datetime import datetime, timezone

import requests

from sg_calendar.instagram import GRAPH

TARGET_USERNAME = "r.makeup.session"
NEEDED = {
    "instagram_basic": "Instagram アカウントの参照",
    "instagram_content_publish": "フィード・ストーリーズの投稿",
    "pages_show_list": "連携 Facebook ページの取得",
    "pages_read_engagement": "ページ経由で Instagram アカウントを解決",
    "instagram_manage_comments": "投稿後のコメントオフ",
    "business_management": "ビジネスポートフォリオ経由の資産アクセス (システムユーザー)",
}
REQUIRED = ("instagram_basic", "instagram_content_publish", "pages_show_list")


def _get(path, token, **params):
    try:
        r = requests.get(f"{GRAPH}/{path}", params={**params, "access_token": token}, timeout=60)
    except requests.RequestException as e:
        return None, f"network error ({type(e).__name__})"
    try:
        body = r.json()
    except ValueError:
        body = {}
    if not r.ok:
        err = body.get("error") or {}
        return None, f"HTTP {r.status_code} code={err.get('code')} subcode={err.get('error_subcode')}"
    return body, None


def _when(ts):
    if not ts:
        return "never"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def run_check():
    token = os.environ.get("META_ACCESS_TOKEN", "").strip()
    if not token:
        return {"META_ACCESS_TOKEN": "SKIPPED: not set"}
    out = {}

    # 1. トークン自体 (debug_token はトークン自身で自己診断できる)
    dbg, err = _get("debug_token", token, input_token=token)
    if err:
        out["token"] = f"FAIL: debug_token {err}"
    else:
        d = dbg.get("data", {})
        out["token"] = {
            "valid": d.get("is_valid"),
            "app_id": d.get("app_id"),
            "app_name": d.get("application"),
            "type": d.get("type"),
            "expires": _when(d.get("expires_at")),
            "data_access_expires": _when(d.get("data_access_expires_at")),
        }
        targets = {g.get("scope"): len(g.get("target_ids") or []) for g in d.get("granular_scopes", [])}
        out["token"]["scoped_assets"] = targets or "all granted assets"

    # 2. 権限
    perms, err = _get("me/permissions", token)
    granted = sorted(p["permission"] for p in (perms or {}).get("data", []) if p.get("status") == "granted")
    if err:
        out["permissions"] = f"FAIL: {err}"
    else:
        out["permissions"] = {p: ("OK" if p in granted else "MISSING") + f" — {why}" for p, why in NEEDED.items()}

    # 3. トークンの主体
    me, err = _get("me", token, fields="id,name")
    out["token_subject"] = f"FAIL: {err}" if err else me.get("name")

    # 4. ページと連携 Instagram アカウント
    pages, err = _get("me/accounts", token, fields="name,instagram_business_account{id,username}", limit=50)
    ig_id = None
    if err:
        out["pages"] = f"FAIL: {err}"
    else:
        listed = []
        for p in pages.get("data", []):
            iga = p.get("instagram_business_account") or {}
            listed.append({"page": p.get("name"), "instagram": f"@{iga['username']}" if iga else "(none)"})
            if iga.get("username") == TARGET_USERNAME:
                ig_id = iga["id"]
        out["pages"] = listed or "no Facebook Pages visible to this token"

    # 5. 対象アカウント
    if ig_id:
        out["@r.makeup.session"] = "FOUND via linked Facebook Page"
        acct, err = _get(ig_id, token, fields="username,media_count")
        out["account_read"] = f"FAIL: {err}" if err else f"OK (@{acct.get('username')}, {acct.get('media_count')} posts)"
        lim, err = _get(f"{ig_id}/content_publishing_limit", token, fields="quota_usage,config")
        if err:
            out["publishing_limit"] = f"FAIL: {err}"
        else:
            row = (lim.get("data") or [{}])[0]
            out["publishing_limit"] = f"OK ({row.get('quota_usage')}/{(row.get('config') or {}).get('quota_total')} used in 24h)"
        existing = os.environ.get("IG_USER_ID", "").strip()
        out["IG_USER_ID secret"] = ("not set" if not existing else
                                    "MATCHES this account" if existing == ig_id else "DIFFERS from this account")
    else:
        out["@r.makeup.session"] = "NOT FOUND among Pages visible to this token"

    missing = [p for p in REQUIRED if p not in granted]
    ok = (isinstance(out.get("token"), dict) and out["token"]["valid"] and not missing and ig_id is not None
          and str(out.get("publishing_limit", "")).startswith("OK"))
    out["verdict"] = "READY for feed + stories (no post was made)" if ok else \
        f"NOT READY (missing: {missing or '-'}; account found: {bool(ig_id)})"
    return out
