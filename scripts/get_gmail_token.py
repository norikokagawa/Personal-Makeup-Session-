#!/usr/bin/env python3
"""
Gmail OAuth2 - refresh token取得スクリプト
ターミナルで実行: python3 scripts/get_gmail_token.py
"""
import http.server
import json
import os
import urllib.parse
import urllib.request
import webbrowser

REDIRECT_URI = "http://localhost:8080"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def main():
    CLIENT_ID = input("GMAIL_CLIENT_ID を入力してください: ").strip()
    CLIENT_SECRET = input("GMAIL_CLIENT_SECRET を入力してください: ").strip()

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("\nブラウザを開きます...")
    webbrowser.open(auth_url)

    auth_code = None

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in query:
                auth_code = query["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>OK! Terminal \xe3\x81\xab\xe6\x88\xbb\xe3\x81\xa3\xe3\x81\xa6\xe3\x81\x8f\xe3\x81\xa0\xe3\x81\x95\xe3\x81\x84\xe3\x80\x82</h2></body></html>"
            )

        def log_message(self, format, *args):
            pass

    print("ブラウザでGoogleにログインして許可してください...")
    server = http.server.HTTPServer(("localhost", 8080), Handler)
    server.handle_request()

    if not auth_code:
        print("ERROR: 認証コードが取得できませんでした")
        return

    print("\nトークンを取得中...")
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: {e.code} {e.read().decode()}")
        return

    refresh_token = tokens.get("refresh_token")
    if refresh_token:
        print("\n✅ 成功!")
        print(f"\nGMAIL_REFRESH_TOKEN =\n{refresh_token}")
        print("\nこの値をGitHub Secrets の GMAIL_REFRESH_TOKEN に更新してください。")
    else:
        print(f"\nERROR: refresh_tokenが含まれていません: {tokens}")


if __name__ == "__main__":
    main()
