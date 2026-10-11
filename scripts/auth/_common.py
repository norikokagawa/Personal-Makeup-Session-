"""手元の Mac で使う OAuth 共通処理。トークンは画面にもファイルにも出さず、gh で直接 Secrets に保存する。"""
import base64
import hashlib
import http.server
import secrets
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser

REPO = "norikokagawa/Personal-Makeup-Session-"


def require_gh():
    if not shutil.which("gh"):
        sys.exit("GitHub CLI (gh) が必要です: brew install gh → gh auth login")
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        sys.exit("gh にログインしてください: gh auth login")


def pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def receive_code(auth_url, port, state):
    """Open the consent page and wait for the redirect on 127.0.0.1:<port>."""
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [None])[0] != state:
                result["error"] = "state mismatch"
            elif "code" in q:
                result["code"] = q["code"][0]
            else:
                result["error"] = q.get("error", ["no code"])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>完了しました。このタブを閉じてターミナルに戻ってください。</h2>".encode())

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print("ブラウザで許可してください…")
    webbrowser.open(auth_url)
    server.handle_request()
    server.server_close()
    if "code" not in result:
        sys.exit(f"認証に失敗しました: {result.get('error')}")
    return result["code"]


def set_secret(name, value):
    """Pipe the value to `gh secret set` (never printed, never written to disk)."""
    subprocess.run(["gh", "secret", "set", name, "--repo", REPO], input=value, text=True, check=True)


def confirm(question):
    return input(f"{question} [y/N]: ").strip().lower() == "y"
