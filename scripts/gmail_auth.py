"""
Gmail OAuth 認証ヘルパー（初回のみ実行）

使い方:
  1. Google Cloud Console で「OAuth 2.0 クライアント ID」を作成し
     client_id と client_secret を控える
  2. 下記の CLIENT_ID / CLIENT_SECRET を書き換えて実行:
       python scripts/gmail_auth.py
  3. ブラウザが開くので Google アカウントでログインして許可する
  4. 表示された Refresh token を GitHub Secrets に登録する:
       GMAIL_CLIENT_ID     ← client_id
       GMAIL_CLIENT_SECRET ← client_secret
       GMAIL_REFRESH_TOKEN ← 表示された refresh_token

Google Cloud Console:
  https://console.cloud.google.com/apis/credentials
  必要な API: Gmail API (読み取りのみ)
  アプリの種類: デスクトップアプリ
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID     = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0)

print("\n=== GitHub Secrets に登録してください ===")
print(f"GMAIL_CLIENT_ID     = {CLIENT_ID}")
print(f"GMAIL_CLIENT_SECRET = {CLIENT_SECRET}")
print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
