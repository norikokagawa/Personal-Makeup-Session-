#!/usr/bin/env python3
"""
Canva OAuth2 PKCE flow - リフレッシュトークン取得
サーバーを先に起動してからブラウザを開く（確実版）
"""
import base64
import hashlib
import os
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

CLIENT_ID = "OC-AZ44ZCIXRVRk"
REDIRECT_URI = "http://127.0.0.1:8080"
SCOPES = "asset:read design:content:read"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"

with open("/tmp/cs.txt") as f:
    CLIENT_SECRET = f.read().strip()
print(f"Secret: {CLIENT_SECRET[:10]}... ({len(CLIENT_SECRET)}文字) 読み込み完了")

code_verifier = secrets.token_urlsafe(64)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b"=").decode()
state = secrets.token_hex(16)

params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPES,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
    "state": state,
}
auth_url = "https://www.canva.com/api/oauth/authorize?" + urllib.parse.urlencode(params)

auth_code = [None]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if "code" in query:
            auth_code[0] = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h1>✅ 認証成功！Terminalに戻ってください</h1>".encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code received")
    def log_message(self, *args):
        pass

# サーバーを先に起動してからブラウザを開く
server = HTTPServer(("127.0.0.1", 8080), Handler)
print("ブラウザで許可してください...")
webbrowser.open(auth_url)

server.handle_request()
server.server_close()

if not auth_code[0]:
    print("エラー: 認証コードを受け取れませんでした")
    exit(1)

r = requests.post(TOKEN_URL, data={
    "grant_type": "authorization_code",
    "code": auth_code[0],
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code_verifier": code_verifier,
})
data = r.json()
print(f"レスポンス keys: {list(data.keys())}")
if "refresh_token" not in data:
    print(f"エラー: {data}")
    exit(1)

with open("/tmp/refresh_token.txt", "w") as f:
    f.write(data["refresh_token"])
print("✅ 成功！Refresh Token保存済み")
print(f"   Token length: {len(data['refresh_token'])} chars")
