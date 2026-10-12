#!/usr/bin/env python3
"""
GMAIL_REFRESH_TOKEN を再発行して GitHub Secrets に直接保存する (手元の Mac で実行)

  python3 scripts/auth/issue_gmail_token.py

- スコープは gmail.readonly のみ (読み取り専用)
- Client ID は秘密ではないので表示入力。Secret は非表示入力 (文字数と形式だけ確認表示)
- トークンは画面に出さず GitHub Secrets に保存する
  (gh があれば直接、なければクリップボード経由で GitHub の画面に貼り付け)
- GMAIL_CLIENT_ID は変更しない。GMAIL_CLIENT_SECRET は確認のうえ今回の値で更新できる
- 保存前に、取得した refresh token でアクセストークンを取得できることを確認する
"""
import getpass
import secrets
import sys
import urllib.parse

from _common import confirm, pkce, receive_code, request, require_gh, set_secret

PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def ask_client_id():
    while True:
        v = input("Google OAuth Client ID を貼り付けて Enter: ").strip()
        if v.endswith(".apps.googleusercontent.com"):
            return v
        print("  → 形式が違います (末尾が .apps.googleusercontent.com のはず)。もう一度貼り付けてください。")


def ask_client_secret():
    # 値は表示しない。空のまま進むと Google が 400 invalid_request を返すため、ここで止める
    while True:
        v = getpass.getpass("Google OAuth Client Secret を貼り付けて Enter (画面には何も表示されません): ").strip()
        if not v:
            print("  → 何も入力されていません。⌘ + V で貼り付けてから Enter を押してください。")
            continue
        ok = v.startswith("GOCSPX-")
        print(f"  受け取りました: {len(v)} 文字 / GOCSPX- で始まる: {'はい' if ok else 'いいえ'}")
        if ok or confirm("  GOCSPX- で始まっていません。このまま進みますか"):
            return v


def describe(r):
    j = r.json()
    return j.get("error"), j.get("error_description", "")


def main():
    require_gh()
    client_id = ask_client_id()
    client_secret = ask_client_secret()
    verifier, challenge = pkce()
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "login_hint": "noriko.kagawa@atelier-r-make.com",
    })
    code = receive_code(url, PORT, state)
    r = request("POST", "https://oauth2.googleapis.com/token", data={
        "code": code, "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code", "code_verifier": verifier,
    })
    if not r.ok:
        err, desc = describe(r)
        hint = ""
        if "secret" in desc.lower():
            hint = "\n→ Client Secret が空か、貼り付けに失敗しています。もう一度実行して貼り付け直してください。"
        elif err == "redirect_uri_mismatch":
            hint = (f"\n→ OAuth クライアントが『ウェブ アプリケーション』型なら、承認済みのリダイレクト URI に "
                    f"{REDIRECT} を追加してから再実行してください。")
        elif err in ("invalid_client", "unauthorized_client"):
            hint = "\n→ Client ID / Secret の組み合わせが違います。同じ OAuth クライアントの値か確認してください。"
        elif err == "invalid_grant":
            hint = "\n→ 許可コードの期限切れです。もう一度最初から実行してください。"
        sys.exit(f"トークン交換に失敗: {r.status_code} {err} ({desc}){hint}")
    data = r.json()
    if "refresh_token" not in data:
        sys.exit("refresh token が返りませんでした (Google アカウントの『サードパーティ接続』から"
                 "このアプリのアクセスを削除して再実行してください)")
    if SCOPE not in data.get("scope", ""):
        sys.exit("gmail.readonly が許可されていません。同意画面でチェックを入れて再実行してください")

    # 保存前の動作確認 (Google の refresh token は再利用可能なので消費しても問題ない)
    t = request("POST", "https://oauth2.googleapis.com/token", data={
        "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
        "client_id": client_id, "client_secret": client_secret})
    if not t.ok:
        sys.exit("取得した refresh token で更新できませんでした: %s (%s)" % describe(t))
    print("✓ 取得した refresh token で認証できることを確認しました")

    set_secret("GMAIL_REFRESH_TOKEN", data["refresh_token"])
    if confirm("GMAIL_CLIENT_SECRET を、今回入力した新しいシークレットで更新しますか (GMAIL_CLIENT_ID は変更しません)"):
        set_secret("GMAIL_CLIENT_SECRET", client_secret)
    print("完了しました。Claude に「Gmail の再認証が終わった」と伝えてください。")


if __name__ == "__main__":
    main()
