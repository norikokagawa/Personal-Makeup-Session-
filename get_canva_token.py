#!/usr/bin/env python3
"""
Canva OAuth PKCE フロー でリフレッシュトークンを取得するスクリプト
Mac のターミナルで実行: python3 get_canva_token.py
"""
import base64, hashlib, os, secrets, urllib.parse, webbrowser, json
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

# ── 設定 ──────────────────────────────────────────────────────────────────────
CLIENT_ID     = "OC-AZ44ZCIXRVRk"
REDIRECT_URI  = "http://127.0.0.1:8080"
SCOPES        = "asset:read design:content:read"
TOKEN_URL     = "https://api.canva.com/rest/v1/oauth/token"

# ─────────────────────────────────────────────────────────────────────────────

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_pkce():
    verifier  = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge

captured = {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        captured["code"]  = qs.get("code",  [None])[0]
        captured["error"] = qs.get("error", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>OK! This tab can be closed.</h2>")
        # Notify server to stop
        self.server._BaseServer__shutdown_request = True

    def log_message(self, *a): pass  # suppress access logs

def main():
    client_secret = input("CANVA_CLIENT_SECRET を入力してください: ").strip()

    verifier, challenge = make_pkce()

    params = {
        "response_type":         "code",
        "client_id":             CLIENT_ID,
        "redirect_uri":          REDIRECT_URI,
        "scope":                 SCOPES,
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
    }
    auth_url = "https://www.canva.com/api/oauth/authorize?" + urllib.parse.urlencode(params)

    print("\nブラウザが開きます。Canva でアクセスを許可してください...")
    webbrowser.open(auth_url)

    print("認証待機中... (ポート 8080)")
    server = HTTPServer(("127.0.0.1", 8080), Handler)
    server.handle_request()  # 1回だけ受け取る

    code = captured.get("code")
    if not code:
        print(f"\nエラー: {captured.get('error')}")
        return

    print("認証コードを取得しました。トークンを交換中...")
    r = requests.post(TOKEN_URL, data={
        "grant_type":    "authorization_code",
        "client_id":     CLIENT_ID,
        "client_secret": client_secret,
        "code":          code,
        "code_verifier": verifier,
        "redirect_uri":  REDIRECT_URI,
    })
    r.raise_for_status()
    d = r.json()

    print("\n" + "="*60)
    print("✅ 取得成功！以下の値を GitHub Secrets に設定してください")
    print("="*60)
    print(f"\nCANVA_CLIENT_ID:     {CLIENT_ID}")
    print(f"CANVA_CLIENT_SECRET: {client_secret}")
    print(f"CANVA_REFRESH_TOKEN: {d['refresh_token']}")
    print()

if __name__ == "__main__":
    main()
