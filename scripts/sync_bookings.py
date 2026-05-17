"""
5:58 PM JST に Gmail (STORES 予約) を確認して Canva を自動更新するスクリプト。

必須環境変数:
  GMAIL_CLIENT_ID
  GMAIL_CLIENT_SECRET
  GMAIL_REFRESH_TOKEN
  CANVA_ACCESS_TOKEN
"""

import os
import re
import base64
import time
import datetime
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Canva 設定 ─────────────────────────────────────────────────────────────────

CANVA_API    = "https://api.canva.com/rest/v1"
CANVA_TOKEN  = os.environ["CANVA_ACCESS_TOKEN"]
CANVA_HEADS  = {"Authorization": f"Bearer {CANVA_TOKEN}"}

DESIGN_ID = "DAGsRHlSvkw"

PAGE_IDS = [
    "PB85YJ4J9PlqqkZh",  # 1: Singapore
    "PB8Wnp7wnbTdwrdz",  # 2
    "PB9KXjDb4Y1mW8xG",  # 3
    "PBbCnl7s3JD3yp8V",  # 4
    "PBksdWKJwCT6JQWm",  # 5
    "PBlKbNkjCXVYBbGQ",  # 6
    "PBtMqq5LNTdh596V",  # 7
]

PAGES = [{"page_id": pid, "is_responsive": False, "is_empty": False} for pid in PAGE_IDS]

TABLE_PREFIX = "PB85YJ4J9PlqqkZh-LBW0KMppyFY35KXZ-"

# ── セルマッピング (Singapore June) ───────────────────────────────────────────
# キー: (日付の日, "HH:MM" 24時間表記)  値: テーブルセルの末尾ID
SINGAPORE_JUNE = {
    # THU 18
    (18, "11:00"): "A3",
    (18, "12:00"): "A4",
    (18, "13:00"): "A5",
    (18, "14:00"): "A6",
    # FRI 19
    (19, "11:00"): "C3",
    (19, "12:00"): "C4",
    (19, "13:00"): "C5",
    (19, "14:00"): "C6",
    # SAT 20
    (20, "10:00"): "D3",
    (20, "11:00"): "D4",
    (20, "12:00"): "D5",
    (20, "14:00"): "D6",
    (20, "15:00"): "D7",
    (20, "16:00"): "D8",
    # SUN 21
    (21, "10:00"): "E3",
    (21, "11:00"): "E4",
    (21, "12:00"): "E5",
    (21, "14:00"): "E6",
    (21, "15:00"): "E7",
    (21, "16:00"): "E8",
    # TUE 23
    (23, "11:00"): "F3",
    (23, "12:00"): "F4",
    (23, "13:00"): "F5",
    (23, "14:00"): "F6",
    # WED 24
    (24, "11:00"): "H3",
    (24, "12:00"): "H4",
    (24, "13:00"): "H5",
    (24, "14:00"): "H6",
    # THU 25
    (25, "11:00"): "g85teJdZzJu-YeCLA:mm5yj6b9:l",
    (25, "12:00"): "g85teJdZzJu-YeCLA:mm5yj6b9:m",
    (25, "13:00"): "g85teJdZzJu-YeCLA:mm5yj6b9:n",
    (25, "14:00"): "g85teJdZzJu-YeCLA:mm5yj6b9:o",
    # SAT 27
    (27, "10:00"): "g85teJdZzJu-YeCLA:mm5yj3gj:c",
    (27, "11:00"): "g85teJdZzJu-YeCLA:mm5yj3gj:d",
    (27, "12:00"): "g85teJdZzJu-YeCLA:mm5yj3gk:e",
    (27, "14:00"): "g85teJdZzJu-YeCLA:mm5yj3gk:f",
    (27, "15:00"): "g85teJdZzJu-YeCLA:mm5yj3gk:g",
    (27, "16:00"): "g85teJdZzJu-YeCLA:mm5yj3gk:h",
    # SUN 28
    (28, "10:00"): "g85teJdZzJu-YeCLA:mm5yj1hb:3",
    (28, "11:00"): "g85teJdZzJu-YeCLA:mm5yj1hb:4",
    (28, "12:00"): "g85teJdZzJu-YeCLA:mm5yj1hb:5",
    (28, "14:00"): "g85teJdZzJu-YeCLA:mm5yj1hb:6",
    (28, "15:00"): "g85teJdZzJu-YeCLA:mm5yj1hb:7",
    (28, "16:00"): "g85teJdZzJu-YeCLA:mm5yj1hc:8",
    # TUE 30
    (30, "11:00"): "_u2I8gGbbHA0oQE8A:mnmhwj8c:3",
    (30, "12:00"): "_u2I8gGbbHA0oQE8A:mnmhwj8c:4",
    (30, "13:00"): "_u2I8gGbbHA0oQE8A:mnmhwj8c:5",
    (30, "14:00"): "_u2I8gGbbHA0oQE8A:mnmhwj8d:6",
}

# 場所名 → セルマップ（今後 Sydney, Tokushima など追加予定）
LOCATION_MAP = {
    "singapore": SINGAPORE_JUNE,
}

# ── Gmail 認証 ────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)

# ── メール解析 ─────────────────────────────────────────────────────────────────

def decode_body(msg):
    parts = msg["payload"].get("parts", [])
    if parts:
        for p in parts:
            if p["mimeType"] == "text/plain":
                return base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8", errors="ignore")
    data = msg["payload"]["body"].get("data", "")
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore") if data else ""

def parse_booking(body: str) -> dict | None:
    """STORES 予約メール本文から予約情報を抽出する。"""
    # 予約内容（場所）
    loc_m = re.search(r"◆予約内容[:：]\s*\n\s*(.+)", body)
    # 予約日時: 2026年06月25日（木）11:00 ～ 11:45
    dt_m  = re.search(r"◆予約日時[:：]\s*\n\s*(\d{4})年(\d{2})月(\d{2})日.*?(\d{1,2}:\d{2})\s*[～~]", body)

    if not (loc_m and dt_m):
        return None

    raw_loc = loc_m.group(1).strip()
    day  = int(dt_m.group(3))
    hour, minute = map(int, dt_m.group(4).split(":"))

    # 24時間表記に正規化（STORESは通常24h、念のため）
    time_str = f"{hour:02d}:{minute:02d}"

    # 場所名を正規化
    loc_key = raw_loc.lower()
    for key in LOCATION_MAP:
        if key in loc_key:
            return {"location": key, "day": day, "time": time_str, "raw_location": raw_loc}
    return None

def is_cancellation(subject: str, body: str) -> bool:
    return "キャンセル" in subject or "キャンセル" in body

# ── Canva 更新 ─────────────────────────────────────────────────────────────────

def canva_open_transaction() -> tuple[str, list]:
    r = requests.post(f"{CANVA_API}/design/{DESIGN_ID}/editing_session/open",
                      headers=CANVA_HEADS)
    r.raise_for_status()
    data = r.json()
    return data["transaction_id"], data["pages"]

def canva_format_cell(transaction_id: str, pages: list, element_id: str, booked: bool):
    color      = "#FF0000" if booked else "#4D4D4D"
    strikethrough = "strikethrough" if booked else "none"
    body = {
        "transaction_id": transaction_id,
        "page_index": 1,
        "pages": pages,
        "operations": [{
            "type": "format_text",
            "element_id": element_id,
            "formatting": {"color": color, "strikethrough": strikethrough},
        }],
    }
    r = requests.post(f"{CANVA_API}/design/{DESIGN_ID}/editing_session/perform",
                      headers=CANVA_HEADS, json=body)
    r.raise_for_status()

def canva_commit(transaction_id: str):
    r = requests.post(f"{CANVA_API}/design/{DESIGN_ID}/editing_session/commit",
                      headers=CANVA_HEADS,
                      json={"transaction_id": transaction_id})
    r.raise_for_status()

def update_canva(location: str, day: int, time_str: str, booked: bool):
    cell_map = LOCATION_MAP.get(location)
    if not cell_map:
        print(f"  ⚠ 未対応の場所: {location}")
        return

    cell_suffix = cell_map.get((day, time_str))
    if not cell_suffix:
        print(f"  ⚠ セルが見つかりません: day={day} time={time_str}")
        return

    element_id = TABLE_PREFIX + cell_suffix
    status = "予約済（赤）" if booked else "空き（黒）"
    print(f"  → Canva更新: {location} {day}日 {time_str} → {status}")

    txn_id, pages = canva_open_transaction()
    try:
        canva_format_cell(txn_id, pages, element_id, booked)
        canva_commit(txn_id)
    except Exception as e:
        requests.post(f"{CANVA_API}/design/{DESIGN_ID}/editing_session/cancel",
                      headers=CANVA_HEADS, json={"transaction_id": txn_id})
        raise e

# ── メイン ────────────────────────────────────────────────────────────────────

def main():
    print("Gmail を確認中...")
    svc = get_gmail_service()

    # 過去 24 時間の STORES 予約メールを検索
    query = 'from:"STORES 予約" newer_than:1d'
    results = svc.users().messages().list(userId="me", q=query).execute()
    messages = results.get("messages", [])
    print(f"  {len(messages)} 件のメールが見つかりました")

    if not messages:
        print("新着予約メールなし。終了します。")
        return

    processed = 0
    for m in messages:
        msg = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
        subject = next(
            (h["value"] for h in msg["payload"]["headers"] if h["name"] == "Subject"), ""
        )
        body = decode_body(msg)

        info = parse_booking(body)
        if not info:
            print(f"  スキップ（解析不可）: {subject}")
            continue

        booked = not is_cancellation(subject, body)
        action = "予約" if booked else "キャンセル"
        print(f"\n{action}: {info['raw_location']} {info['day']}日 {info['time']}")
        update_canva(info["location"], info["day"], info["time"], booked)
        processed += 1
        time.sleep(1)

    print(f"\n完了: {processed} 件を更新しました。")

if __name__ == "__main__":
    main()
