# 05:00 SGT publishing — triggers, fallbacks, always-on services

Instagram's API has **no scheduled publishing**. A job must be running at 05:00 and call `media_publish`. The job prepares the private containers early, waits, and publishes at 05:00:00 SGT. If it starts late, it publishes immediately.

GitHub's own `schedule` trigger is **best effort**. This repo's old workflow ran 4–10 h late in May 2026, so it is only the last-resort fallback here.

## No own server needed

All three are hosted services that run whether or not your computer or Claude Code is open.

| Service | Role | Cost |
|---|---|---|
| **GitHub Actions** (this repo) | Runs every step: `ledger`, `post`, `watchdog` | free (public repo) |
| **Claude cloud routine** | Daily Canva update via the Canva connector, then starts the GitHub `post` run | included in the Claude plan |
| **cron-job.org** (or any external cron) | Minute-accurate backup trigger: calls GitHub's `workflow_dispatch` API | free |

## Daily timeline (SGT)

| Time | Trigger | Action |
|---|---|---|
| 04:00 | Claude routine (primary) | Dispatch `ledger` → wait for it → Canva step (`docs/SG_CANVA_ROUTINE.md`) → dispatch `post` |
| 04:07 | cron-job.org → `ledger` | Backup ledger (harmless if already done) |
| 04:30 | cron-job.org → `post` | Backup post start |
| 04:23 | GitHub schedule → `post` | Last-resort backup (often late) |
| 05:00 | the running `post` job | Publishes the feed carousel and both stories (each tracked separately) |
| 05:17 / 05:20 | GitHub schedule and cron-job.org → `watchdog` | Fails, which opens a GitHub Issue (email), unless all three are `published` |

**Duplicate starts are safe.**
- Runs are serialised (`concurrency: canva-refresh-token`).
- `post` returns `ALREADY_POSTED` once all three are published.
- Partly done work resumes from `records/<date>.json`, using Instagram's container status as the source of truth.

## Failure scenarios

| Failure | What happens |
|---|---|
| Claude routine late or failed | cron-job.org starts `post` at 04:30. If bookings are unchanged since the last verified Canva update, the calendar is still correct and is posted. If they changed, `post` **stops and notifies** (no outdated calendar). |
| cron-job.org down | The Claude routine has already dispatched `post`; the GitHub schedule is a third path. |
| All triggers late | `post` publishes as soon as it starts; `watchdog` has already notified that 05:00 was missed. |
| Run dies mid-publish | The next trigger resumes. An item whose container is `PUBLISHED` is marked done and **not re-posted**. One still `FINISHED` is published with the same container (no duplicate). |
| Instagram rejects a post | That item is `failed` and retried on the next trigger, up to 3 times. The other items continue; `watchdog` notifies. |
| Token expired / permission missing | Exit 1 → Issue "認証切れの可能性". `auth-check` tells which service. |

## Setup at go-live (after approval)

1. Merge this branch to `main`: `workflow_dispatch` only works for workflows on the default branch. This adds a new workflow file and does not change `daily-instagram-post.yml`. Note that `deploy.yml` redeploys GitHub Pages on every push to `main` (same site plus the new files).
2. **cron-job.org**: create jobs (timezone Asia/Singapore) that `POST https://api.github.com/repos/norikokagawa/Personal-Makeup-Session-/actions/workflows/sg-calendar-daily.yml/dispatches` with body `{"ref":"main","inputs":{"mode":"post","dry_run":"false","auto_publish":"true"}}` (likewise for `ledger` and `watchdog`).
   - Header `Authorization: Bearer <token>`, where `<token>` is a fine-grained PAT limited to this repository with **Actions: Read and write** only.
   - The token is entered in cron-job.org's header field, never in the repo.
3. **Claude routine**: create it with the prompt in `docs/SG_CANVA_ROUTINE.md` (target `DAGsRHlSvkw`), schedule `CRON_TZ=Asia/Singapore 0 4 * * *`, and the Canva + GitHub connectors.
4. Uncomment the `schedule` block as the last-resort backup.
