#!/usr/bin/env python3
"""
Canva 更新ステップ用 CLI (Claude の定期実行ルーチンから呼ぶ)

  plan   --ledger L --before B            → 更新操作 (format_text) と停止理由を JSON で出力
  verify --before B --after A --plan P    → 計画外の変更が1つでもあれば exit 1
  state  --ledger L --snapshot A --design D → 投稿ステップが照合する canva_state.json を出力

B / A は read-design の design_content (pages 1-2) か、同じ形の簡易スナップショット。
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sg_calendar import canva_doc, ledger as ledger_mod  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config" / "sg_calendar.json").read_text())


def _load(p):
    return json.loads(Path(p).read_text())


def cmd_plan(a):
    lg = ledger_mod.from_json(_load(a.ledger))
    g = canva_doc.grid(canva_doc.snapshot(_load(a.before)))
    p = canva_doc.plan(lg, g, CONFIG["manual_closed"], CONFIG["acknowledged_inquiries"])
    out = {k: p[k] for k in ("strike", "unstrike", "keep_manual", "blockers")}
    out["ops"] = {str(k): v for k, v in p["ops"].items()}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 2 if p["blockers"] else 0


def cmd_verify(a):
    ops = {int(k): v for k, v in _load(a.plan)["ops"].items()}
    problems = canva_doc.verify(canva_doc.snapshot(_load(a.before)),
                                canva_doc.snapshot(_load(a.after)), ops)
    print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False, indent=2))
    return 1 if problems else 0


def cmd_state(a):
    data = _load(a.ledger)
    snap = canva_doc.snapshot(_load(a.snapshot))
    canva_doc.grid(snap)                        # 読めない表なら例外で止める
    state = {"date": datetime.now(ZoneInfo(CONFIG["timezone"])).strftime("%Y-%m-%d"),
             "design_id": a.design, "ledger_fingerprint": ledger_mod.fingerprint(data),
             "snapshot": snap}
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--ledger", required=True); p.add_argument("--before", required=True)
    v = sub.add_parser("verify"); v.add_argument("--before", required=True); v.add_argument("--after", required=True)
    v.add_argument("--plan", required=True)
    s = sub.add_parser("state"); s.add_argument("--ledger", required=True); s.add_argument("--snapshot", required=True)
    s.add_argument("--design", required=True)
    a = ap.parse_args(argv)
    return {"plan": cmd_plan, "verify": cmd_verify, "state": cmd_state}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
