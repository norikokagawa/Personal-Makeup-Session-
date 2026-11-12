"""
Gmail OAuth 認証ヘルパー（初回のみ実行）

使い方:
  1. 下記の CLIENT_ID / CLIENT_SECRET を書き換える
  2. 実行: python scripts/gmail_auth.py
  3. 表示された URL をブラウザで開いてGoogleアカウントでログイン・許可
  4. 表示された認証コードをターミナルに貼り付けてEnter
  5. 表示された Refresh token を GitHub Secrets に登録する:
       GMAIL_CLIENT_ID     ← client_id
       GMAIL_CLIENT_SECRET ← client_secret
       GMAIL_REFRESH_TOKEN ← 表示された refresh_token
"""

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
flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
print("\n以下のURLをブラウザで開いてGoogleアカウントにログインし、表示されたコードをコピーしてください:\n")
print(auth_url)
print()

code = input("認証コードを貼り付けてEnter: ").strip()
flow.fetch_token(code=code)
creds = flow.credentials

print("\n=== GitHub Secrets に登録してください ===")
print(f"GMAIL_CLIENT_ID     = {CLIENT_ID}")
print(f"GMAIL_CLIENT_SECRET = {CLIENT_SECRET}")
print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
