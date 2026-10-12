"""
手元の Mac で使う OAuth 共通処理。トークンは画面にもファイルにも出さない。

保存方法は2通り (自動で選ぶ):
  - GitHub CLI (gh) にログイン済みなら gh secret set で直接保存
  - gh がなければ、値をクリップボードにだけコピーし、GitHub の画面に貼り付けてもらう
    (貼り付け後にクリップボードを消去する)
"""
import base64
import hashlib
import http.server
import json
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

REPO = "norikokagawa/Personal-Makeup-Session-"


SECRETS_PAGE = f"https://github.com/{REPO}/settings/secrets/actions"


def have_gh():
    return bool(shutil.which("gh")) and \
        subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0


def require_gh():
    """gh があれば使い、なければクリップボード方式で進める (Homebrew 不要)。"""
    if have_gh():
        print("GitHub CLI (gh) で Secrets に直接保存します。")
    else:
        if not shutil.which("pbcopy"):
            sys.exit("この Mac でクリップボードが使えません。gh をインストールしてください (brew install gh)。")
        print("GitHub CLI がないため、値をクリップボード経由で GitHub の画面に貼り付けます。")


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
    """Save a secret without ever printing it or writing it to disk."""
    if have_gh():
        subprocess.run(["gh", "secret", "set", name, "--repo", REPO], input=value, text=True, check=True)
        return
    subprocess.run(["pbcopy"], input=value, text=True, check=True)
    print(f"""
──────────────────────────────────────────────
{name} の値をクリップボードにコピーしました (画面には表示していません)。
1. ブラウザで次のページを開いてください:
   {SECRETS_PAGE}
2. 一覧の {name} の右にある鉛筆アイコン (Update) を押します
   (一覧にない場合は「New repository secret」→ Name に {name})
3. 値の欄をクリックして ⌘ + V で貼り付け → 「Update secret」(または「Add secret」) を押します
──────────────────────────────────────────────""")
    input("保存できたら Enter キーを押してください (クリップボードを消去します): ")
    subprocess.run(["pbcopy"], input="", text=True, check=True)
    print(f"✓ {name} を保存し、クリップボードを消去しました")


def confirm(question):
    return input(f"{question} [y/N]: ").strip().lower() == "y"


class Resp:
    """Minimal response (標準ライブラリのみ。追加インストール不要)."""

    def __init__(self, status, body):
        self.status_code, self.ok = status, 200 <= status < 300
        try:
            self._json = json.loads(body or b"{}")
        except ValueError:
            self._json = {}

    def json(self):
        return self._json


def http(method, url, data=None, headers=None, basic_auth=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=dict(headers or {}))
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    if basic_auth:
        token = base64.b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return Resp(r.status, r.read())
    except urllib.error.HTTPError as e:
        return Resp(e.code, e.read())
