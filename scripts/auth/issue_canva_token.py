#!/usr/bin/env python3
"""
CANVA_REFRESH_TOKEN を再発行して GitHub Secrets に直接保存する (手元の Mac で実行)

  python3 scripts/auth/issue_canva_token.py

- 既存インテグレーション (Client ID OC-AZ44ZCIXRVRk, リダイレクト http://127.0.0.1:8080) を使う
- スコープ: asset:read design:content:read (書き出しに必要な最小限。既存と同じ)
- Canva の refresh token は1回限り。ここでは更新処理を行わず、取得した token をそのまま保存する
  (ここで試しに更新すると token が入れ替わり、保存した値が無効になるため)
"""
import getpass
import secrets
import sys
import urllib.parse

from _common import confirm, http, pkce, receive_code, require_gh, set_secret

CLIENT_ID = "OC-AZ44ZCIXRVRk"
PORT = 8080
REDIRECT = f"http://127.0.0.1:{PORT}"
SCOPES = "asset:read design:content:read"


def main():
    require_gh()
    client_secret = getpass.getpass("Canva Client Secret (入力は表示されません): ").strip()
    verifier, challenge = pkce()
    state = secrets.token_urlsafe(16)
    url = "https://www.canva.com/api/oauth/authorize?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": CLIENT_ID, "redirect_uri": REDIRECT, "scope": SCOPES,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
    })
    code = receive_code(url, PORT, state)
    r = http("POST", "https://api.canva.com/rest/v1/oauth/token", basic_auth=(CLIENT_ID, client_secret), data={
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
        "redirect_uri": REDIRECT,
    })
    if not r.ok:
        sys.exit(f"トークン交換に失敗: {r.status_code} {r.json().get('error')}")
    data = r.json()
    if "refresh_token" not in data:
        sys.exit("refresh token が返りませんでした")
    granted = set(data.get("scope", "").split())
    missing = set(SCOPES.split()) - granted
    if granted and missing:
        sys.exit(f"不足しているスコープ: {' '.join(sorted(missing))}")
    # access token で読み取り専用の呼び出しを1回だけ試す (refresh token は消費しない)
    me = http("GET", "https://api.canva.com/rest/v1/users/me",
              headers={"Authorization": f"Bearer {data['access_token']}"})
    print("✓ Canva の認証を確認しました" if me.ok else f"注意: 確認用 API が {me.status_code} を返しました")

    set_secret("CANVA_REFRESH_TOKEN", data["refresh_token"])
    if confirm("CANVA_CLIENT_SECRET も今回入力した値で上書きしますか (シークレットを再生成した場合のみ)"):
        set_secret("CANVA_CLIENT_SECRET", client_secret)
    print("完了。以後この refresh token は GitHub Actions だけが使います (手元で再利用しないでください)。")


if __name__ == "__main__":
    main()
