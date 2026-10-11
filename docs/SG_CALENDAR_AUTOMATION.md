# atelierR Singapore November Calendar — Daily Instagram Automation

Status: **TEST MODE** (`DRY_RUN=true`, `AUTO_PUBLISH=false`, no cron). Do not enable the schedule until production go-live is explicitly approved.

## 1. Existing environment (survey 2026-10-11)

| Item | Finding |
|---|---|
| Existing job | `.github/workflows/daily-instagram-post.yml` + `scripts/daily_post.py`. Manual trigger only; its cron was removed on 2026-05-31 ("Disable scheduled Instagram posting"). It posts **directly through the Instagram Graph API**, not Metricool, as a 6-page carousel, and only lists Gmail subjects. Left untouched. |
| Secrets used | `CANVA_CLIENT_ID/SECRET/REFRESH_TOKEN` (scopes `asset:read design:content:read`, rotated via `GH_PAT`), `GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN`, `IG_USER_ID`, `IG_ACCESS_TOKEN`. **No Metricool secrets yet.** |
| Metricool | Not referenced anywhere in the repo; no Metricool connector in Claude. |
| Canva `DAGsRHlSvkw` | 3 pages, 1080×1350. p1 = Singapore Nov 6–15, p2 = Singapore Nov 18–29, p3 = Sydney Oct 23–Nov 1. |
| Booked marker ("横線") | Table cell **text strikethrough + colour `#ff5757`**; an open slot has no strikethrough and colour `#545454`. Font, size and weight are untouched by the toggle. Cell map: `config/sg_nov_page1.json`. |
| Slots on p1 | Weekdays 11/12/13/14:00 (4); Sat/Sun 11/12/13/15/16/17:00 (6, **no 14:00**). |

## 2. Daily flow (`scripts/sg_calendar/run_daily.py`)

1. **Gmail**: read STORES mail (booked / changed / cancelled / inquiry), build a ledger **by reservation number**, period 2026-11-06..30. Duplicate notifications count once; inquiries never change the ledger.
2. **Stop conditions** (exit 2 → GitHub Issue): any anomaly (double-booked slot, change/cancel for unknown number, unparseable mail), a booking at a time the page has no cell for, or any difference from the approved Canva state. In those cases **nothing is posted**, so an outdated calendar is never published.
3. **Canva update** is never automatic: a Claude session opens a draft edit, shows the before/after preview, and saves only after approval. Then `approved_booked` in `config/sg_nov_page1.json` is updated.
4. **Images**: official Canva export (`png`, `export_quality: pro`, 1080×1350, lossless) → verified size/format. The story image is a 1080×1920 canvas with the **whole** feed image pasted 1:1 at y=285 on the design background `#f6f4f1`, then verified pixel-for-pixel.
5. **Metricool**: list the day's Instagram posts first. The feed (`POST`, approved caption from `config/sg_caption.txt`) and the story (`STORY`, no caption) are created independently, and each is skipped if one of that type already exists that day. Publish time is 05:00 SGT, or the nearest feasible time (+10 min) if that has passed. With `AUTO_PUBLISH=false`, posts are created as **drafts**.
6. **Record**: `records/<date>.json` on the `instagram-media` branch distinguishes *scheduled* from *published*. Instagram publication is confirmed later from Metricool's status, never assumed at scheduling time.

Comments-off: the Metricool API exposes no option to disable comments, so this must be set **manually** (or the published media switched afterwards via the Graph API `comment_enabled=false`, if wanted).

## 3. One-day test plan

| # | Check | How | Result 2026-10-11 |
|---|---|---|---|
| 1 | Gmail extraction is accurate | Ledger from all STORES Singapore mail | 34 Nov reservations; 0 cancellations/changes in Nov ✅ |
| 2 | Booked slots match Canva lines | `diff_against_design` | **2 differences** (see §4) ⚠️ |
| 3 | Other Canva elements unchanged | Draft edit of one cell, compare document + thumbnail, then cancel | Only the target cell changed ✅ (draft discarded) |
| 4 | High-quality images | Canva export `pro` 1080×1350 succeeded; size/story checks run in code and tests | Export job ✅; download blocked in this sandbox, so verify in Actions |
| 5 | Two independent Metricool posts | Dry-run payloads (POST + STORY) | Payloads ✅; live API untested (no token, host blocked here) |
| 6 | Same-day duplicate prevention | Unit test + Metricool listing | Unit-tested ✅; live pending |
| 7 | Posts even with no booking change | No-diff path runs to scheduling | ✅ (dry run) |

Run the tests with `python -m unittest tests/test_sg_calendar.py`.

## 4. Open items found in the test

- **11/15 11:00**: booked (#136683000) but not struck → preview ready, awaiting approval.
- **11/08 17:00**: struck, but no booking mail → not changed automatically (it may be a manual block).
- **11/29 15:00** (page 2): two active reservations (#136653243, #144069220). Page 2 must not be edited.
- **Inquiry 2026-10-11**: #136683000 asks to move from 15 Nov to 11 Nov. Not applied; no STORES change mail yet.
- Bookings on 18–29 Nov sit on page 2, which is out of scope for edits.

## 5. Go-live checklist (only after explicit approval)

1. Add secrets `METRICOOL_USER_TOKEN`, `METRICOOL_USER_ID`, `METRICOOL_BLOG_ID` (Metricool Advanced plan API).
2. Run the workflow manually with `dry_run=false, auto_publish=false` → confirm two drafts in Metricool.
3. Uncomment the `schedule` in `.github/workflows/sg-calendar-daily.yml` and set `AUTO_PUBLISH` for scheduled runs.
4. Failures and stops open a GitHub Issue, which emails the repo owner. Auth failures (Gmail, Canva, Metricool 401/403) exit 1 with "re-authorise".
