# atelierR Singapore November Calendar — Daily Instagram Automation

Status: **TEST MODE** (`DRY_RUN=true`, `AUTO_PUBLISH=false`, schedules commented out). The existing `daily-instagram-post.yml` / `scripts/daily_post.py`, the original Canva design and the Instagram account are untouched.

## What it does every morning

Each morning needs only two connections: **Gmail** (read-only) and **Instagram** (`META_ACCESS_TOKEN`, no expiry). Canva and Claude are not part of the daily run.

1. Read the STORES booking mails and build the ledger by reservation number.
2. Work out which slots are taken: active bookings plus `manual_closed` in `config/sg_calendar.json`.
3. Build pages 1–2 from two fixed master images in `assets/sg_masters/`, exported once from copies of `DAGsRHlSvkw`.
   - `open_p*.png`: every slot gray (`#545454`) with no strikethrough (Canva copy `DAHX1S2EPR0`).
   - `booked_p*.png`: every slot red (`#ff5757`) with strikethrough (Canva copy `DAHX1QJavPQ`).
   - Each slot's box is found from the pixel difference of the two masters and matched to `config/sg_layout.json`.
   - The booked master's pixels are copied in for taken slots.
   - The result is verified pixel by pixel: every slot equals exactly one master, and nothing outside the slots changes.
   - Page 3 (Sydney) is never used.
4. Publish at **05:00 SGT** through the official Instagram API, also on days without changes:
   - feed: high-quality JPEG **2-image carousel** (1080×1350)
   - **2 stories** (1080×1920, each page whole and unscaled)
5. Switch off comments on the feed post (needs `instagram_manage_comments`).
6. Delete the feed posts this system published on earlier days (`delete_previous_feed`).
   - Only media IDs in our own `records/<date>.json` are deleted, and only if Instagram still reports our carousel with our caption.
   - If Instagram refuses the delete, the run notifies and the old post can be deleted by hand.

It **stops and notifies** (GitHub Issue → email) on any of these:
- two bookings on one slot
- a change/cancel mail for an unknown reservation
- an unconfirmed change request
- a booking with no slot on pages 1–2
- an image check fails
- auth errors
- the watchdog finds unpublished items after 05:00

## When the design changes

Copy pages 1–2 of the design twice. Set every time slot to open on one copy and to booked on the other, then export both as lossless PNG at 1080×1350 into `assets/sg_masters/`. Regenerate `config/sg_layout.json` if the table changed. The composer refuses to run if the masters and the layout do not line up.

## Components

| File | Role |
|---|---|
| `scripts/sg_calendar/ledger.py` | STORES mail → ledger by reservation number (numbers hashed/masked in anything stored or logged) |
| `scripts/sg_calendar/compose.py` | slot boxes from the masters, per-slot composition, pixel verification |
| `scripts/sg_calendar/images.py` | page checks, JPEG q95 4:4:4 with PSNR check, 1080×1920 stories |
| `scripts/sg_calendar/instagram.py` | Graph API client: containers, carousel, STORIES, publish, comments off, delete own post, read-only checks |
| `scripts/sg_calendar/post_state.py` | duplicate-safe state per item (FEED, STORY_1, STORY_2) |
| `scripts/sg_calendar/auth.py` | `auth-check` for Gmail and Meta (OK/FAIL only) |
| `scripts/sg_calendar/run_daily.py` | modes `post`, `ledger`, `watchdog`, `auth-check` |
| `scripts/sg_calendar/canva_doc.py` | reads a Canva table snapshot (used to regenerate `config/sg_layout.json`) |
| `.github/workflows/sg-calendar-daily.yml` | runner (manual / push-test / schedules) |
| `docs/SG_SCHEDULING.md` | 05:00 design and fallbacks |
| `docs/SG_AUTH_SETUP.md` | credential re-issue steps |

## Modes

| `DRY_RUN` | `AUTO_PUBLISH` | Effect |
|---|---|---|
| true | false | No writes anywhere. With `ig_probe=true`, only **private** containers are created (never published). |
| false | false | Non-public rehearsal: images and post state saved on `instagram-media`, containers created, **nothing published** |
| false | true | Production: publishes at 05:00 and deletes the previous day's feed post |

`metricool.py` is kept for reference only and is unused.
