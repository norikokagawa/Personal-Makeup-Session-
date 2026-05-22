"""
Canva OAuth 認証ヘルパー（初回のみ実行）

Macのターミナルで実行:
  python3 scripts/canva_auth.py

ブラウザが自動で開くので Canva にログインして許可する。
表示された CANVA_REFRESH_TOKEN を GitHub Secrets に登録する。
"""

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

CLIENT_ID     = os.environ.get("CANVA_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
REDIRECT_URI  = "http://127.0.0.1:8080"
SCOPES        = "design:content:read design:content:write"

AUTH_URL   = "https://www.canva.com/api/oauth/authorize"
TOKEN_URL  = "https://api.canva.com/rest/v1/oauth/token"

# PKCE
code_verifier  = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()

captured_code = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_code
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        captured_code = qs.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>OK! Go back to Terminal.</h1>")

    def log_message(self, *_):
        pass

server = http.server.HTTPServer(("127.0.0.1", 8080), Handler)
thread = threading.Thread(target=server.handle_request)
thread.start()

params = urllib.parse.urlencode({
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPES,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
})
url = f"{AUTH_URL}?{params}"
print("\nブラウザでCanvaにログインして許可してください...\n")
webbrowser.open(url)

thread.join(timeout=120)

if not captured_code:
    print("タイムアウト。もう一度実行してください。")
    exit(1)

data = urllib.parse.urlencode({
    "grant_type": "authorization_code",
    "code": captured_code,
    "redirect_uri": REDIRECT_URI,
    "code_verifier": code_verifier,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}).encode()

req = urllib.request.Request(TOKEN_URL, data=data,
      headers={"Content-Type": "application/x-www-form-urlencoded"})
resp = urllib.request.urlopen(req)
tokens = json.loads(resp.read())

print("\n=== GitHub Secrets に登録してください ===")
print(f"CANVA_CLIENT_ID     = {CLIENT_ID}")
print(f"CANVA_CLIENT_SECRET = {CLIENT_SECRET}")
print(f"CANVA_REFRESH_TOKEN = {tokens['refresh_token']}")
print(f"\n（参考）Access token: {tokens['access_token'][:40]}...")
