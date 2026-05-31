#!/usr/bin/env python3
"""
毎朝5:55 JST に実行:
1. Canva デザインをエクスポート (PNG)
2. Gmail で STORES 予約メールを確認
3. Instagram に自動投稿
"""
import base64
import os
import sys
import time
import requests
import pytz
from datetime import datetime

JST = pytz.timezone("Asia/Tokyo")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_API = "https://api.canva.com/rest/v1"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
IG_API = "https://graph.facebook.com/v19.0"
CANVA_DESIGN_ID = os.environ.get("CANVA_DESIGN_ID", "DAGsRHlSvkw")
SCHEDULE_PAGES = 6  # Canva design pages
REPO_BASE = (
    "https://raw.githubusercontent.com/norikokagawa/"
    "Personal-Makeup-Session-/main"
)
FALLBACK_SINGLE = f"{REPO_BASE}/schedule.png"
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "norikokagawa/Personal-Makeup-Session-")


# ── GitHub secret rotation ─────────────────────────────────────────────────

def _save_canva_refresh_token(new_token):
    """Update CANVA_REFRESH_TOKEN in GitHub Secrets using GH_PAT."""
    gh_pat = os.environ.get("GH_PAT", "").strip()
    if not gh_pat:
        print("  GH_PAT not set — cannot auto-save new refresh token")
        return
    try:
        from nacl import encoding, public as nacl_public
        headers = {
            "Authorization": f"Bearer {gh_pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key",
            headers=headers,
        )
        r.raise_for_status()
        key_data = r.json()
        pub_key = nacl_public.PublicKey(key_data["key"].encode(), encoding.Base64Encoder())
        encrypted = base64.b64encode(
            nacl_public.SealedBox(pub_key).encrypt(new_token.encode())
        ).decode()
        r = requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/CANVA_REFRESH_TOKEN",
            headers=headers,
            json={"encrypted_value": encrypted, "key_id": key_data["key_id"]},
        )
        r.raise_for_status()
        print("  CANVA_REFRESH_TOKEN auto-updated in GitHub Secrets")
    except Exception as e:
        print(f"  Secret auto-update failed (non-fatal): {e}")


# ── Canva ──────────────────────────────────────────────────────────────────

def canva_access_token():
    secret = os.environ["CANVA_CLIENT_SECRET"].strip()
    print(f"  Canva secret: {len(secret)} chars, starts with {secret[:6]}")
    r = requests.post(CANVA_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["CANVA_REFRESH_TOKEN"].strip(),
        "client_id": os.environ["CANVA_CLIENT_ID"].strip(),
        "client_secret": secret,
    })
    if not r.ok:
        print(f"Canva token error: {r.status_code} {r.text[:300]}")
    r.raise_for_status()
    data = r.json()
    if "refresh_token" in data:
        print("  Canva issued new refresh token (rotating) — saving...")
        _save_canva_refresh_token(data["refresh_token"])
    return data["access_token"]


def export_canva(token, num_pages=SCHEDULE_PAGES):
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.post(
        f"{CANVA_API}/exports",
        headers=headers,
        json={
            "design_id": CANVA_DESIGN_ID,
            "format": {"type": "png"},
            "pages": list(range(1, num_pages + 1)),
        },
    )
    print(f"Export request: {r.status_code} {r.text[:200]}")
    r.raise_for_status()
    job_id = r.json()["job"]["id"]
    print(f"Export job: {job_id}")

    for i in range(40):
        time.sleep(3)
        s = requests.get(f"{CANVA_API}/exports/{job_id}", headers=headers).json()
        status = s["job"]["status"]
        print(f"  [{i+1}/40] {status}")
        if status == "success":
            return s["job"]["urls"]  # list of URLs, one per page
        if status == "failed":
            raise RuntimeError(f"Canva export failed: {s}")

    raise TimeoutError("Canva export timed out")


# ── Gmail ──────────────────────────────────────────────────────────────────

def gmail_access_token():
    r = requests.post(GMAIL_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
    })
    r.raise_for_status()
    return r.json()["access_token"]


def get_todays_bookings():
    try:
        token = gmail_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        today = datetime.now(JST)
        after = today.strftime("%Y/%m/%d")

        r = requests.get(f"{GMAIL_API}/users/me/messages", headers=headers,
                         params={"q": f"subject:予約確認 after:{after}", "maxResults": 30})
        messages = r.json().get("messages", [])

        slots = []
        for m in messages[:15]:
            md = requests.get(
                f"{GMAIL_API}/users/me/messages/{m['id']}",
                headers=headers,
                params={"format": "metadata",
                        "metadataHeaders": ["Subject", "From"]},
            ).json()
            hdrs = {h["name"]: h["value"]
                    for h in md.get("payload", {}).get("headers", [])}
            subj = hdrs.get("Subject", "")
            frm = hdrs.get("From", "")
            if "stores" in frm.lower() or "予約" in subj:
                slots.append(subj)

        print(f"Gmail: {len(slots)} booking email(s) found today")
        return slots

    except Exception as e:
        print(f"Gmail warning (non-fatal): {e}")
        return []


# ── Instagram ──────────────────────────────────────────────────────────────

def _ig_post(uid, tok, data):
    r = requests.post(f"{IG_API}/{uid}/media", data={**data, "access_token": tok})
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"]["message"])
    return d["id"]


def _ig_wait_ready(tok, container_id, label="Container"):
    for i in range(30):
        time.sleep(5)
        r = requests.get(f"{IG_API}/{container_id}",
                         params={"fields": "status_code", "access_token": tok})
        status = r.json().get("status_code", "UNKNOWN")
        print(f"  {label} status: {status}")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Media container error: {r.json()}")
    raise TimeoutError(f"{label} timed out")


def post_instagram_single(image_url, caption):
    uid = os.environ["IG_USER_ID"]
    tok = os.environ["IG_ACCESS_TOKEN"]
    cid = _ig_post(uid, tok, {"image_url": image_url, "caption": caption})
    print(f"Media container: {cid}")
    _ig_wait_ready(tok, cid, "Single image")
    r = requests.post(f"{IG_API}/{uid}/media_publish",
                      data={"creation_id": cid, "access_token": tok})
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"]["message"])
    return d["id"]


def post_instagram_carousel(image_urls, caption):
    uid = os.environ["IG_USER_ID"]
    tok = os.environ["IG_ACCESS_TOKEN"]

    item_ids = []
    for i, url in enumerate(image_urls[:10]):
        cid = _ig_post(uid, tok, {"image_url": url, "is_carousel_item": "true"})
        print(f"  Carousel item {i+1}: {cid}")
        item_ids.append(cid)

    for i, item_id in enumerate(item_ids):
        _ig_wait_ready(tok, item_id, f"Item {i+1}")

    carousel_id = _ig_post(uid, tok, {
        "media_type": "CAROUSEL",
        "children": ",".join(item_ids),
        "caption": caption,
    })
    print(f"Carousel container: {carousel_id}")
    _ig_wait_ready(tok, carousel_id, "Carousel")

    r = requests.post(f"{IG_API}/{uid}/media_publish",
                      data={"creation_id": carousel_id, "access_token": tok})
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"]["message"])
    return d["id"]


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(JST)
    print(f"=== Daily Post: {now.strftime('%Y-%m-%d %H:%M JST')} ===\n")

    print("1. Exporting Canva design...")
    canva_urls = None
    try:
        canva_urls = export_canva(canva_access_token())
        print(f"   {len(canva_urls)} page(s) exported from Canva\n")
    except Exception as e:
        print(f"   Canva export failed: {e}")
        print(f"   Falling back to schedule_N.png in repo...\n")

    print("2. Checking Gmail for today's bookings...")
    bookings = get_todays_bookings()

    print("3. Building caption...")
    caption = ("Personal Makeup Session Schedule\n"
               "for each city is now available.\n\n"
               "Reservations can be made\n"
               "via the link in my profile.")

    if canva_urls:
        image_urls = canva_urls
    else:
        # Fallback: look for schedule_1.png ... schedule_7.png in repo
        urls = [f"{REPO_BASE}/schedule_{i}.png" for i in range(1, SCHEDULE_PAGES + 1)]
        image_urls = []
        for u in urls:
            resp = requests.head(u)
            if resp.status_code == 200:
                image_urls.append(u)
                print(f"   Found: schedule_{len(image_urls)}.png")
        if not image_urls:
            image_urls = [FALLBACK_SINGLE]
            print("   No schedule_N.png found, using schedule.png")

    print(f"4. Posting to Instagram ({len(image_urls)} image(s))...")
    if DRY_RUN:
        print("   [DRY RUN] 実際には投稿しません")
        print(f"   Caption: {caption}")
        for i, u in enumerate(image_urls, 1):
            print(f"   Image {i}: {u}")
        print("\n✅ Dry run complete!")
    else:
        if len(image_urls) == 1:
            post_id = post_instagram_single(image_urls[0], caption)
        else:
            post_id = post_instagram_carousel(image_urls, caption)
        print(f"\n✅ Done! Instagram post ID: {post_id}")


if __name__ == "__main__":
    main()
