#!/usr/bin/env python3
"""
毎朝5:55 JST に実行:
1. Canva デザインをエクスポート (PNG)
2. Gmail で STORES 予約メールを確認
3. Instagram に自動投稿
"""
import os
import sys
import time
import requests
import pytz
from datetime import datetime

JST = pytz.timezone("Asia/Tokyo")
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_API = "https://api.canva.com/rest/v1"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
IG_API = "https://graph.facebook.com/v19.0"
CANVA_DESIGN_ID = os.environ.get("CANVA_DESIGN_ID", "DAGsRHlSvkw")


# ── Canva ──────────────────────────────────────────────────────────────────

def canva_access_token():
    r = requests.post(CANVA_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["CANVA_REFRESH_TOKEN"],
        "client_id": os.environ["CANVA_CLIENT_ID"],
        "client_secret": os.environ["CANVA_CLIENT_SECRET"],
    })
    r.raise_for_status()
    return r.json()["access_token"]


def export_canva(token):
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.post(
        f"{CANVA_API}/designs/{CANVA_DESIGN_ID}/exports",
        headers=headers,
        json={"format": {"type": "png"}, "pages": [1]},
    )
    r.raise_for_status()
    job_id = r.json()["job"]["id"]
    print(f"Export job: {job_id}")

    for i in range(40):
        time.sleep(3)
        s = requests.get(f"{CANVA_API}/exports/{job_id}", headers=headers).json()
        status = s["job"]["status"]
        print(f"  [{i+1}/40] {status}")
        if status == "success":
            return s["job"]["urls"][0]
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

def post_instagram(image_url, caption):
    uid = os.environ["IG_USER_ID"]
    tok = os.environ["IG_ACCESS_TOKEN"]

    r = requests.post(f"{IG_API}/{uid}/media",
                      data={"image_url": image_url, "caption": caption,
                            "access_token": tok})
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"Media create error: {d['error']['message']}")
    cid = d["id"]
    print(f"Media container: {cid}")

    r = requests.post(f"{IG_API}/{uid}/media_publish",
                      data={"creation_id": cid, "access_token": tok})
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"Publish error: {d['error']['message']}")
    return d["id"]


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(JST)
    print(f"=== Daily Post: {now.strftime('%Y-%m-%d %H:%M JST')} ===\n")

    print("1. Exporting Canva design...")
    image_url = export_canva(canva_access_token())
    print(f"   URL: {image_url[:80]}...\n")

    print("2. Checking Gmail for today's bookings...")
    bookings = get_todays_bookings()

    print("3. Building caption...")
    md = now.strftime("%-m月%-d日")
    if bookings:
        caption = (f"{md}の予約状況です。\n"
                   f"本日{len(bookings)}件のご予約をいただいています。\n"
                   f"ご予約はプロフィールリンクよりお願いいたします。\n\n"
                   f"#メイク #makeup #メイクアップ #メイクレッスン "
                   f"#makeupartist #beauty #シンガポール #Singapore")
    else:
        caption = (f"{md}の予約状況です。\n"
                   f"ご予約はプロフィールリンクよりお願いいたします。\n\n"
                   f"#メイク #makeup #メイクアップ #メイクレッスン "
                   f"#makeupartist #beauty #シンガポール #Singapore")

    print(f"4. Posting to Instagram...")
    post_id = post_instagram(image_url, caption)
    print(f"\n✅ Done! Instagram post ID: {post_id}")


if __name__ == "__main__":
    main()
