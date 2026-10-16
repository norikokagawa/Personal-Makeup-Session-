# 05:00 SGT publishing — triggers and fallbacks

Instagram's API has **no scheduled publishing**. A job must be running at 05:00 and call `media_publish`. The `post` job prepares the private containers early, waits, and publishes at 05:00:00 SGT. If it starts late, it publishes immediately.

Each run is self-contained: it reads Gmail, builds the images and posts. Nothing has to run before it, so a single trigger that fires between about 04:10 and 04:55 is enough.

## Triggers (no own server needed)

| Service | Role | Cost |
|---|---|---|
| **GitHub Actions** schedule | `post` at 04:07 and 04:31 SGT, `watchdog` at 05:17 | free (public repo) |
| **cron-job.org** | Minute-accurate extra trigger through GitHub's `workflow_dispatch` API, for days when GitHub's schedule runs late | free |

GitHub's own `schedule` is best effort; the old workflow in this repo once ran hours late. That is why there is a second, external trigger.

**Duplicate starts are safe.**
- Runs are serialised (`concurrency: sg-calendar-daily`).
- `post` returns `ALREADY_POSTED` once all three items are published.
- Partly done work resumes from `records/<date>.json`, using Instagram's container status as the source of truth.

## Failure scenarios

| Failure | What happens |
|---|---|
| GitHub schedule late | cron-job.org has already started `post`. |
| cron-job.org down | The GitHub schedule still runs. |
| All triggers late | `post` publishes as soon as it starts; `watchdog` has already notified that 05:00 was missed. |
| Run dies mid-publish | The next trigger resumes. An item whose container is `PUBLISHED` is marked done and **not re-posted**; one still `FINISHED` is published with the same container. |
| Instagram rejects a post | That item is `failed` and retried on the next trigger, up to 3 times. The other items continue; `watchdog` notifies. |
| Old feed post cannot be deleted | Today's post stays up; the run notifies so the old one can be deleted by hand. |
| Token expired / permission missing | Exit 1 → Issue "認証切れの可能性". `auth-check` tells which service. |

## Setup at go-live (after approval)

1. Merge this branch to `main`: `workflow_dispatch` only works for workflows on the default branch. This adds a new workflow file and does not change `daily-instagram-post.yml`. Note that `deploy.yml` redeploys GitHub Pages on every push to `main` (same site plus the new files).
2. Uncomment the `schedule` block and set the schedule's `DRY_RUN`/`AUTO_PUBLISH` values in the workflow.
3. **cron-job.org**: create a job (timezone Asia/Singapore, 03:45 daily — the story images are ready before 04:00; the run waits until 05:00 to publish the feed).
   - It sends `POST https://api.github.com/repos/norikokagawa/Personal-Makeup-Session-/actions/workflows/sg-calendar-daily.yml/dispatches`.
   - Body: `{"ref":"main","inputs":{"mode":"post","dry_run":"false","auto_publish":"true"}}`.
   - Header: `Authorization: Bearer <token>`. `<token>` is a fine-grained PAT limited to this repository with **Actions: Read and write** only. It is entered in cron-job.org, never in the repo.
