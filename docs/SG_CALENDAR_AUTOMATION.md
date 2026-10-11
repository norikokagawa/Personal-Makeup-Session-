# atelierR Singapore November Calendar — Daily Instagram Automation

Status: **TEST MODE** (`DRY_RUN=true`, `AUTO_PUBLISH=false`, schedules commented out). The existing `daily-instagram-post.yml` / `scripts/daily_post.py` are untouched.

## Policy (2026-10-11)

- Canva `DAGsRHlSvkw` pages **1 and 2** are updated automatically every morning. Page 3 (Sydney) is never changed.
- Booked slot = `#ff5757` + strikethrough. Open slot = `#545454`, no strikethrough. A struck slot with no booking record is treated as manually closed and never reopened automatically.
- Only confirmed bookings from STORES mail (by reservation number) are applied. Normal changes need no per-change approval.
- **Automatic stop + notification**:
  - two active bookings on one slot
  - change/cancel mail without an original booking
  - an unconfirmed change/cancel request
  - a booking at a date/time the design has no cell for
  - Canva not matching the ledger
  - any failed verification or image check
  - auth errors
- **Instagram (via Metricool) at 05:00 SGT daily**, even when nothing changed:
  - feed: 2-image carousel (pages 1 and 2)
  - two separate stories (page 1, page 2)
  - no same-day duplicates

## Architecture

| Time (SGT) | Runner | Does |
|---|---|---|
| 04:00 | GitHub Actions `run_daily.py ledger` | Gmail → ledger by reservation number → `state/ledger.json` on branch `instagram-media` |
| 04:15 | Claude routine (`docs/SG_CANVA_ROUTINE.md`) | ledger vs. Canva pages 1–2 → `format_text` on the time cells only → `canva_step.py verify` → commit → `state/canva_state.json` |
| 04:40 | GitHub Actions `run_daily.py post` | Re-reads Gmail; refuses to post unless it matches `canva_state.json` → Canva export (PNG, pro, 1080×1350, pages 1–2) → image checks → stories 1080×1920 → Metricool |

Why the Canva step is a Claude routine: Canva's public REST API (Connect API) exports and copies designs but cannot edit elements in an existing design. The Canva connector's editing transaction can, and it was verified on a copy first (below). No layout is rebuilt.

Code: `scripts/sg_calendar/` (`ledger.py`, `canva_doc.py`, `canva_step.py`, `images.py`, `metricool.py`, `run_daily.py`). Config: `config/sg_calendar.json`, `config/sg_caption.txt`. Tests: `python -m unittest tests/test_sg_calendar.py`.

## Test results (2026-10-11)

| Check | Result |
|---|---|
| Gmail ledger | 34 active Nov reservations; no Nov change/cancel mails |
| Pages 1–2 read automatically from cell text (no hard-coded IDs) | 15 dates; weekdays 4 slots, weekends 6 |
| Plan on the real ledger | strike 11/15 11:00; keep 11/08 17:00 as manual; **2 blockers** (11/29 15:00 double booking; open change request 1a12b734…) |
| Auto-update on test copy `DAHXvZlAaxU` | page 1 strike + page 2 reopen applied, `verify` OK (and it rejects unplanned/no-op diffs), committed, re-read confirmed |
| Original `DAGsRHlSvkw` | not modified |
| High-quality export | Canva export job for pages 1–2 (pro, 1080×1350) succeeded. Download and pixel checks run in GitHub Actions (blocked in the Claude sandbox) |
| Metricool | payloads built (carousel POST + 2 STORY, drafts). Live API not tested: no `METRICOOL_*` secrets yet |

## Before production

1. Resolve the two blockers (or add the inquiry id to `acknowledged_inquiries`).
2. Add `METRICOOL_USER_TOKEN`, `METRICOOL_USER_ID`, `METRICOOL_BLOG_ID` secrets; run `post` manually with `dry_run=false, auto_publish=false` → confirm 3 drafts.
3. Create the Claude routine (04:15 SGT, Canva connector, this repo) with `docs/SG_CANVA_ROUTINE.md` as its prompt; switch the target to `DAGsRHlSvkw`.
4. Remove the `push` trigger, uncomment `schedule`, set `AUTO_PUBLISH` for scheduled runs.
5. Instagram comments-off must be set manually (no Metricool API option).
