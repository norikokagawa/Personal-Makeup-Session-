#!/usr/bin/env python3
"""
Canva OAuth2 PKCE - refresh token取得スクリプト
ターミナルで実行: python3 scripts/get_canva_token.py
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import urllib.parse
import urllib.request
import webbrowser

CLIENT_ID = "OC-AZ44ZCIXRVRk"
REDIRECT_URI = "http://127.0.0.1:8080"
AUTH_URL = "https://www.canva.com/api/oauth/authorize"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
SCOPES = "asset:read design:content:read"


def generate_pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def main():
    client_secret = input("CANVA_CLIENT_SECRET を入力してください: ").strip()

    verifier, challenge = generate_pkce()

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
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

    print("ブラウザでCanvaにログインして「許可」をクリックしてください...")
    server = http.server.HTTPServer(("127.0.0.1", 8080), Handler)
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
        "client_secret": client_secret,
        "code_verifier": verifier,
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
        print(f"\nCANVA_REFRESH_TOKEN =\n{refresh_token}")
        print("\nこの値をGitHub Secrets の CANVA_REFRESH_TOKEN に更新してください。")
    else:
        print(f"\nERROR: refresh_tokenが含まれていません: {tokens}")


if __name__ == "__main__":
    main()
