# kana さんのタスクメールを iPhone のリマインダーに入れる仕組み

秘書の kana さんから Gmail に届くタスクまとめを、毎晩 21 時ごろ（日本時間）に
自動で読み取り、iPhone の「リマインダー」App に追加します。

```
kana さんのメール ──▶ Gmail ──▶ 毎晩の自動実行（Claude）
                                    │  メール本文からタスクを抽出
                                    ▼
                          icloud_reminders.py
                                    │  CalDAV
                                    ▼
                        iCloud ──▶ iPhone のリマインダー
```

タスクの抽出は Claude が本文を読んで行うので、kana さんが箇条書き・表・普通の
文章のどれで書いても対応できます。決まったフォーマットをお願いする必要はありません。

## セットアップ（初回のみ）

### 1. Apple の「App用パスワード」を発行する

iCloud には通常の Apple ID パスワードでは接続できません。専用のパスワードを作ります。

1. https://appleid.apple.com にサインイン
2. 「サインインとセキュリティ」→「App用パスワード」
3. 「＋」で新規作成。名前は `kana tasks` など分かりやすいもの
4. 表示される `abcd-efgh-ijkl-mnop` 形式の文字列を控える（この画面を閉じると二度と表示されません）

不要になったら同じ画面からいつでも失効させられます。Apple ID 本体のパスワードは
変わりませんし、このパスワードでできるのはカレンダー／リマインダーの読み書きだけです。

### 2. 環境変数を設定する

Claude Code の環境設定（Environment variables / Secrets）に登録します。
**public リポジトリなので、これらを絶対にファイルへ書かないでください。**

| 変数名 | 内容 | 必須 |
|---|---|---|
| `ICLOUD_APPLE_ID` | Apple ID のメールアドレス | ✅ |
| `ICLOUD_APP_PASSWORD` | 手順1で発行した App用パスワード | ✅ |
| `KANA_EMAIL` | kana さんの送信元メールアドレス | ✅ |
| `ICLOUD_REMINDERS_LIST` | 書き込み先のリスト名（例: `仕事`）。未設定なら先頭のリスト | 任意 |

### 3. ネットワークの許可リストに iCloud を追加する

**これを行わないと自動実行は動きません。** 現在この実行環境は厳格な許可リスト方式で、
`caldav.icloud.com` への通信が 403 で拒否されます（GitHub など一部のホストのみ許可）。

環境設定のネットワークポリシーで、次のホストを許可してください。

```
caldav.icloud.com
*.caldav.icloud.com      # iCloud は p01-caldav.icloud.com のような
                         # パーティションホストへリダイレクトします
```

ネットワークポリシーの変更方法は
https://code.claude.com/docs/en/claude-code-on-the-web を参照してください。

### 4. 接続を確認する

```bash
python3 scripts/kana_tasks/icloud_reminders.py --test-connection
```

成功するとリマインダーのリスト名が一覧表示されます。そのうち1つを
`ICLOUD_REMINDERS_LIST` に設定してください。

### 5. 毎晩の Routine を作る

`nightly_routine_prompt.md` を開き、書かれているとおり claude.ai の Routines 画面で
定期実行を作成してください（**Gmail コネクタを有効にすること**）。

以上で完了です。以降は毎晩 21 時ごろに自動で動きます。

## 手元で試す

iCloud に送らずに、生成される内容だけを確認できます（認証情報も不要）。

```bash
echo '{"tasks":[{"title":"テスト","due":"2026-09-11T10:00:00+09:00"}]}' \
  | python3 scripts/kana_tasks/icloud_reminders.py --dry-run
```

実際に1件追加してみる場合:

```bash
echo '{"tasks":[{"title":"テスト"}]}' \
  | python3 scripts/kana_tasks/icloud_reminders.py
```

## タスク JSON の形式

```json
{
  "tasks": [
    {
      "title": "石鹸の在庫を発注する",
      "due": "2026-09-11T10:00:00+09:00",
      "notes": "前回と同じ業者で",
      "priority": "high",
      "source_message_id": "19fb03c774730d98"
    }
  ]
}
```

| フィールド | 説明 |
|---|---|
| `title` | リマインダーのタイトル（必須） |
| `due` | 期日。`2026-09-11` のように日付だけでも可（その場合は朝9時） |
| `notes` | メモ欄に入る補足 |
| `priority` | `high` / `normal` / `low` |
| `source_message_id` | 元メールの ID。重複防止に使うので入れておくのが望ましい |

タイムゾーンを書かない日時は日本時間として扱います。

## 同じタスクが二重に入らない理由

`source_message_id` + `title` + `due` から決まった UID を作り、その UID を
ファイル名として iCloud に書き込みます。書き込みは `If-None-Match: *` 付きなので、
同じ UID が既にあればサーバー側が 412 を返して**上書きせずスキップ**します。

つまり:

- 同じメールを翌日また読んでも、タスクは増えません
- **一度完了にしたタスクが復活することもありません**（上書きしないため）

## トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| `iCloud に接続できませんでした` / `403` | 手順3のネットワーク許可リストが未設定 |
| `iCloud の認証に失敗しました (401)` | 通常の Apple ID パスワードを入れている。App用パスワードを使う |
| `リマインダーのリストが1つも見つかりません` | iPhone の 設定 →〈自分の名前〉→ iCloud で「リマインダー」をオンにする |
| `「〇〇」というリマインダーリストが見つかりません` | `--test-connection` で実際のリスト名を確認して設定し直す |

## このディレクトリに個人情報を置かないこと

このリポジトリは **public** です。タスク本文にはお客様のお名前や連絡先が
含まれる可能性があるため、この仕組みはタスクの内容を一切リポジトリに保存しません。
毎晩の処理では、抽出したタスクを一時ディレクトリに置いて iCloud に送り、その場で捨てます。
