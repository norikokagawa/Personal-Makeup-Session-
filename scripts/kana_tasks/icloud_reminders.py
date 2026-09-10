#!/usr/bin/env python3
"""iCloud リマインダー (Apple Reminders) への CalDAV 書き込みクライアント.

秘書の kana さんが管理するタスク表から抽出したタスクを、iPhone の
「リマインダー」App に直接追加するためのスクリプト。

依存は requests のみ（caldav ライブラリは不要）。毎晩の自動実行は使い捨ての
コンテナ上で走るため、pip install を挟まずに動くことを優先している。

必要な環境変数:
    ICLOUD_APPLE_ID        Apple ID のメールアドレス
    ICLOUD_APP_PASSWORD    appleid.apple.com で発行した「App用パスワード」
    ICLOUD_REMINDERS_LIST  書き込み先リスト名（省略時は最初のリマインダーリスト）

使い方:
    # 1. 接続確認とリマインダーリストの一覧表示
    python3 icloud_reminders.py --test-connection

    # 2. タスクを追加
    python3 icloud_reminders.py --input tasks.json
    cat tasks.json | python3 icloud_reminders.py

tasks.json の形式:
    {
      "tasks": [
        {
          "title": "伊勢丹発注",
          "due": "2026-09-21",                    # 省略可
          "notes": "アクションプラン R様 / 2026.9",  # 省略可
          "priority": "high",                     # high|normal|low、省略可
          "dedupe_key": "actionplan|伊勢丹発注"     # 重複防止キー（推奨）
        }
      ]
    }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import requests

CALDAV_ROOT = "https://caldav.icloud.com"
NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:caldav"}
JST = timezone(timedelta(hours=9))
UID_DOMAIN = "kana-tasks.atelier-r-make.com"

# 期日に時刻指定がないタスクを、何時のリマインダーとして鳴らすか（JST）
DEFAULT_DUE_HOUR = 9

PRIORITY_MAP = {"high": 1, "normal": 5, "low": 9}


class ReminderError(Exception):
    """設定ミスや iCloud 側のエラーをユーザー向け日本語メッセージで包む。"""


# --------------------------------------------------------------------------
# iCalendar 組み立て
# --------------------------------------------------------------------------

def _escape(text: str) -> str:
    """RFC 5545 のテキスト値エスケープ。"""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _fold(line: str) -> str:
    """1行75オクテット以内に折り返す。日本語が UTF-8 の途中で切れないようにする。"""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line

    chunks: list[bytes] = []
    start = 0
    limit = 75  # 1行目は75、継続行は先頭の空白1オクテットぶん74まで
    while start < len(raw):
        end = min(start + limit, len(raw))
        # UTF-8 の継続バイト (10xxxxxx) の途中で切らないよう手前に戻す
        while end > start and end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        chunks.append(raw[start:end])
        start = end
        limit = 74
    head = chunks[0].decode("utf-8")
    tail = "".join("\r\n " + c.decode("utf-8") for c in chunks[1:])
    return head + tail


def _utc_stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_due(value: str) -> tuple[datetime, bool]:
    """期日文字列を datetime に変換する。

    戻り値は (datetime, 日付のみ指定だったか)。タイムゾーン未指定は JST とみなす。
    """
    text = value.strip()
    date_only = len(text) == 10  # "2026-09-11"
    if date_only:
        text += f"T{DEFAULT_DUE_HOUR:02d}:00:00"
    # Python 3.11 の fromisoformat は "Z" も解釈できる
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed, date_only


def build_uid(task: dict) -> str:
    """同じタスクからは必ず同じ UID を作り、二重登録を防ぐ。

    `dedupe_key` があればそれだけを種にする。タスク表のように後から期限や
    優先度が編集される取得元では、これを使わないと編集のたびに別タスクとして
    追加されてしまう。指定がなければ元メール ID・タイトル・期限から作る。
    """
    dedupe_key = str(task.get("dedupe_key", "") or "").strip()
    if dedupe_key:
        seed = dedupe_key
    else:
        seed = "|".join(
            [
                str(task.get("source_message_id", "")),
                str(task.get("title", "")).strip(),
                str(task.get("due", "")).strip(),
            ]
        )
    if not seed.strip("|"):
        return f"{uuid.uuid4().hex}@{UID_DOMAIN}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:32]
    return f"{digest}@{UID_DOMAIN}"


def build_vtodo(task: dict, uid: str, now: datetime | None = None) -> str:
    title = str(task.get("title", "")).strip()
    if not title:
        raise ReminderError("タスクに title がありません。")

    now = now or datetime.now(timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//atelier R//kana-tasks//JA",
        "CALSCALE:GREGORIAN",
        "BEGIN:VTODO",
        f"UID:{uid}",
        f"DTSTAMP:{_utc_stamp(now)}",
        f"CREATED:{_utc_stamp(now)}",
        f"SUMMARY:{_escape(title)}",
        "STATUS:NEEDS-ACTION",
    ]

    notes = str(task.get("notes", "") or "").strip()
    if notes:
        lines.append(f"DESCRIPTION:{_escape(notes)}")

    priority = PRIORITY_MAP.get(str(task.get("priority", "")).lower())
    if priority:
        lines.append(f"PRIORITY:{priority}")

    due_raw = task.get("due")
    if due_raw:
        due, _ = _parse_due(str(due_raw))
        # TZID を使うと VTIMEZONE 定義が必要になるため UTC 形式で書く
        lines.append(f"DUE:{_utc_stamp(due)}")
        # DUE だけでは通知が鳴らないので、期日時刻ちょうどにアラームを付ける
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"TRIGGER;VALUE=DATE-TIME:{_utc_stamp(due)}",
            f"DESCRIPTION:{_escape(title)}",
            "END:VALARM",
        ]

    lines += ["END:VTODO", "END:VCALENDAR"]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


# --------------------------------------------------------------------------
# CalDAV クライアント
# --------------------------------------------------------------------------

class ICloudReminders:
    def __init__(self, apple_id: str, app_password: str, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (apple_id, app_password)
        self.session.headers.update({"User-Agent": "kana-tasks/1.0"})

    def _propfind(self, url: str, body: str, depth: str) -> ET.Element:
        response = self.session.request(
            "PROPFIND",
            url,
            data=body.encode("utf-8"),
            headers={
                "Depth": depth,
                "Content-Type": 'application/xml; charset="utf-8"',
            },
            timeout=self.timeout,
        )
        if response.status_code == 401:
            raise ReminderError(
                "iCloud の認証に失敗しました (401)。\n"
                "  ・ICLOUD_APPLE_ID が Apple ID のメールアドレスか\n"
                "  ・ICLOUD_APP_PASSWORD が通常のパスワードではなく\n"
                "    appleid.apple.com で発行した「App用パスワード」か\n"
                "  を確認してください。"
            )
        if response.status_code not in (207, 200):
            raise ReminderError(
                f"iCloud への PROPFIND が失敗しました "
                f"({response.status_code}): {response.text[:300]}"
            )
        return ET.fromstring(response.content)

    @staticmethod
    def _absolute(base: str, href: str) -> str:
        if href.startswith("http"):
            return href
        scheme, _, rest = base.partition("://")
        host = rest.split("/", 1)[0]
        return f"{scheme}://{host}{href}"

    def discover_lists(self) -> list[dict]:
        """リマインダー (VTODO) を置けるリストを列挙する。"""
        principal_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:propfind xmlns:d="DAV:"><d:prop>'
            "<d:current-user-principal/>"
            "</d:prop></d:propfind>"
        )
        tree = self._propfind(CALDAV_ROOT + "/", principal_body, "0")
        node = tree.find(".//d:current-user-principal/d:href", NS)
        if node is None or not node.text:
            raise ReminderError(
                "iCloud のアカウント情報を取得できませんでした。"
                "App用パスワードを再発行して試してください。"
            )
        principal_url = self._absolute(CALDAV_ROOT, node.text)

        home_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            "<d:prop><c:calendar-home-set/></d:prop></d:propfind>"
        )
        tree = self._propfind(principal_url, home_body, "0")
        node = tree.find(".//c:calendar-home-set/d:href", NS)
        if node is None or not node.text:
            raise ReminderError("iCloud のカレンダーホームを取得できませんでした。")
        home_url = self._absolute(principal_url, node.text)

        list_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            "<d:prop><d:displayname/>"
            "<c:supported-calendar-component-set/>"
            "</d:prop></d:propfind>"
        )
        tree = self._propfind(home_url, list_body, "1")

        found: list[dict] = []
        for response in tree.findall("d:response", NS):
            href_node = response.find("d:href", NS)
            if href_node is None or not href_node.text:
                continue
            comps = {
                c.get("name")
                for c in response.findall(
                    ".//c:supported-calendar-component-set/c:comp", NS
                )
            }
            if "VTODO" not in comps:
                continue
            name_node = response.find(".//d:displayname", NS)
            found.append(
                {
                    "name": (name_node.text or "").strip() if name_node is not None else "",
                    "url": self._absolute(home_url, href_node.text),
                }
            )
        if not found:
            raise ReminderError(
                "リマインダーのリストが1つも見つかりませんでした。"
                "iPhone の設定 > Apple ID > iCloud で「リマインダー」がオンか確認してください。"
            )
        return found

    def pick_list(self, preferred_name: str | None) -> dict:
        lists = self.discover_lists()
        if preferred_name:
            for item in lists:
                if item["name"] == preferred_name:
                    return item
            names = "、".join(i["name"] or "(名前なし)" for i in lists)
            raise ReminderError(
                f"「{preferred_name}」というリマインダーリストが見つかりません。\n"
                f"利用できるリスト: {names}"
            )
        return lists[0]

    def add_todo(self, list_url: str, uid: str, ics: str) -> str:
        """VTODO を追加する。同じ UID が既にあれば追加しない (412)。

        戻り値は "created" または "duplicate"。
        """
        url = list_url.rstrip("/") + f"/{uid}.ics"
        response = self.session.put(
            url,
            data=ics.encode("utf-8"),
            headers={
                "Content-Type": "text/calendar; charset=utf-8",
                # 既存があれば上書きせず 412 を返させる（完了済みを復活させない）
                "If-None-Match": "*",
            },
            timeout=self.timeout,
        )
        if response.status_code in (200, 201, 204):
            return "created"
        if response.status_code == 412:
            return "duplicate"
        raise ReminderError(
            f"リマインダーの追加に失敗しました "
            f"({response.status_code}): {response.text[:300]}"
        )


# --------------------------------------------------------------------------
# エントリポイント
# --------------------------------------------------------------------------

def load_credentials() -> tuple[str, str, str | None]:
    apple_id = os.environ.get("ICLOUD_APPLE_ID", "").strip()
    password = os.environ.get("ICLOUD_APP_PASSWORD", "").strip()
    missing = [
        name
        for name, value in (
            ("ICLOUD_APPLE_ID", apple_id),
            ("ICLOUD_APP_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise ReminderError(
            "環境変数が設定されていません: " + "、".join(missing) + "\n"
            "設定手順は scripts/kana_tasks/README.md を参照してください。"
        )
    return apple_id, password, os.environ.get("ICLOUD_REMINDERS_LIST", "").strip() or None


def read_tasks(path: str | None) -> list[dict]:
    raw = sys.stdin.read() if path in (None, "-") else open(path, encoding="utf-8").read()
    if not raw.strip():
        return []
    data = json.loads(raw)
    tasks = data.get("tasks", data) if isinstance(data, dict) else data
    if not isinstance(tasks, list):
        raise ReminderError("tasks.json の形式が正しくありません（tasks は配列である必要があります）。")
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="kana さんのタスクを iPhone のリマインダーに追加する"
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="iCloud に接続できるか確認し、リマインダーリストを一覧表示する",
    )
    parser.add_argument("--input", "-i", help="タスク JSON のパス（省略時は標準入力）")
    parser.add_argument("--list", help="書き込み先リスト名（ICLOUD_REMINDERS_LIST より優先）")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="iCloud には送らず、生成される内容だけ表示する",
    )
    args = parser.parse_args()

    try:
        if args.dry_run:
            tasks = read_tasks(args.input)
            for task in tasks:
                uid = build_uid(task)
                print(f"--- {task.get('title', '(no title)')} (UID {uid}) ---")
                print(build_vtodo(task, uid))
            print(f"合計 {len(tasks)} 件（dry-run のため送信していません）")
            return 0

        apple_id, password, env_list = load_credentials()
        client = ICloudReminders(apple_id, password)

        if args.test_connection:
            lists = client.discover_lists()
            print("iCloud に接続できました。リマインダーのリスト:")
            for item in lists:
                print(f"  - {item['name'] or '(名前なし)'}")
            print(
                "\nこのうち1つの名前を ICLOUD_REMINDERS_LIST に設定してください"
                "（未設定なら一番上のリストを使います）。"
            )
            return 0

        tasks = read_tasks(args.input)
        if not tasks:
            print("追加するタスクはありませんでした。")
            return 0

        target = client.pick_list(args.list or env_list)
        created, duplicates = [], []
        for task in tasks:
            uid = build_uid(task)
            result = client.add_todo(target["url"], uid, build_vtodo(task, uid))
            (created if result == "created" else duplicates).append(task.get("title", ""))

        label = target["name"] or "(名前なし)"
        print(f"リスト「{label}」に {len(created)} 件を追加しました。")
        for title in created:
            print(f"  + {title}")
        if duplicates:
            print(f"すでに登録済みのため {len(duplicates)} 件はスキップしました。")
            for title in duplicates:
                print(f"  = {title}")
        return 0

    except ReminderError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"エラー: タスク JSON を読めませんでした: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"エラー: iCloud に接続できませんでした: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
