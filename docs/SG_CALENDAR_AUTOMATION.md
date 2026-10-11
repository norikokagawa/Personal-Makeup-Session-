# atelierR Singapore November Calendar — Daily Instagram Automation

Status: **TEST MODE** (`DRY_RUN=true`, `AUTO_PUBLISH=false`, schedules commented out). The existing `daily-instagram-post.yml` / `scripts/daily_post.py`, the original Canva design and the Instagram account are untouched.

## What it does every morning

- Canva `DAGsRHlSvkw` pages **1–2** are updated from confirmed STORES bookings without per-change approval. Page 3 (Sydney) is never touched.
  - Booked = `#ff5757` + strikethrough; open = `#545454`.
  - Struck slots without a booking record are treated as manually closed and never reopened automatically.
- The **official Instagram API** (the same Graph API flow as the existing system) publishes at **05:00 SGT**, also on days without changes:
  - feed: high-quality JPEG **2-image carousel** (pages 1–2, 1080×1350)
  - **2 stories** (1080×1920, each page whole and unscaled)
- Feed comments are switched off after publishing (`comment_enabled=false`, needs `instagram_manage_comments`).
- **Stops and notifies** (GitHub Issue → email) when any of these happens:
  - two bookings on one slot
  - a change/cancel mail for an unknown reservation
  - an unconfirmed change request
  - a booking with no cell on pages 1–2
  - bookings changed since the last verified Canva update
  - an image check fails
  - auth errors
  - the watchdog finds unpublished items after 05:00

## Components

| File | Role |
|---|---|
| `scripts/sg_calendar/ledger.py` | STORES mail → ledger by reservation number (numbers hashed/masked in anything stored or logged) |
| `scripts/sg_calendar/canva_doc.py`, `canva_step.py` | read pages 1–2, plan strike/unstrike, verify before commit (used by the Claude routine) |
| `scripts/sg_calendar/images.py` | export checks, edges, JPEG q95 4:4:4 with PSNR check, 1080×1920 stories |
| `scripts/sg_calendar/instagram.py` | Graph API client: containers, carousel, STORIES, publish, comments off, read-only checks |
| `scripts/sg_calendar/post_state.py` | duplicate-safe state per item (FEED, STORY_1, STORY_2) |
| `scripts/sg_calendar/auth.py` | strict Canva token rotation; `auth-check` (OK/FAIL only) |
| `scripts/sg_calendar/run_daily.py` | modes `ledger`, `post`, `watchdog`, `auth-check` |
| `.github/workflows/sg-calendar-daily.yml` | runner (manual / push-test / backup schedules) |
| `docs/SG_SCHEDULING.md` | 05:00 design, fallbacks, always-on services |
| `docs/SG_CANVA_ROUTINE.md` | Claude routine prompt |
| `docs/SG_AUTH_SETUP.md` | credential re-issue steps |

## Modes

| `DRY_RUN` | `AUTO_PUBLISH` | Effect |
|---|---|---|
| true | false | No writes anywhere. Canva step uses the test copy `DAHXvZlAaxU`. With `ig_probe=true`, only **private** containers are created (never published). |
| false | false | Non-public rehearsal: images and post state saved on `instagram-media`, containers created, **nothing published** |
| false | true | Production: publishes at 05:00 |

`metricool.py` is kept for reference only and is unused.
