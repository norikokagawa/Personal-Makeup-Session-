# Canva step — instructions for the daily Claude routine (04:15 SGT)

Why a Claude routine: the public Canva Connect REST API cannot edit elements inside an existing design. The only route verified to change **just the strikethrough and colour of a time cell** is the Canva connector's editing transaction (`read-design` → `edit-design format_text` → `commit`). It was verified on 2026-10-11 on the test copy `DAHXvZlAaxU`. The routine needs the **Canva** connector and push access to this repository.

Target design: `DAGsRHlSvkw` in production, `DAHXvZlAaxU` (test copy) while `DRY_RUN=true`. Pages **1 and 2 only**. Page 3 (Sydney) must never be read for editing or changed.

## Steps

1. `git fetch origin instagram-media` and read `state/ledger.json` (written by the 04:00 `ledger` job). If it is missing or not from today, **stop** and report.
2. `read-design` the target with `open_transaction: true`, `page_indices: [1, 2]`, `fields: ["design_content", "thumbnails"]`.
3. Save the returned `design_content` as `before.json`, either verbatim or in the compact form used by `tests/fixtures/canva_copy_before.json` (one string per cell: `id|text|strike(1/0)|color|weight`).
4. `python scripts/sg_calendar/canva_step.py plan --ledger state/ledger.json --before before.json > plan.json`
   - exit 2 (blockers) → `edit-design finalize: cancel`, open a GitHub issue with the blockers, **stop**. Do not post.
   - empty `ops` → cancel the transaction (nothing to change) and go to step 7 with `after.json = before.json`.
5. For each page in `plan.json.ops`: `edit-design` with `page_index`, `finalize: keep_open` and exactly those `format_text` operations. Nothing else is allowed: no text, position, size or font operations.
6. Build `after.json` from the `document` returned by each edit (same format as step 3), then run
   `python scripts/sg_calendar/canva_step.py verify --before before.json --after after.json --plan plan.json`
   - exit 0 → `edit-design finalize: commit`
   - otherwise → `edit-design finalize: cancel`, open an issue with the problems, **stop**.
7. `python scripts/sg_calendar/canva_step.py state --ledger state/ledger.json --snapshot after.json --design <target> > canva_state.json`, then commit it to `instagram-media` as `state/canva_state.json` and push.
8. The 04:40 `post` job re-reads Gmail and refuses to post unless the ledger and this state match exactly.

## Rules

- Booked = `#ff5757` + strikethrough; open = `#545454`, no strikethrough.
- A struck slot with no booking record is treated as **manually closed** and never opened automatically. `config/sg_calendar.json → manual_closed` protects slots even after a cancellation.
- Change or cancel *requests* by inquiry never change the calendar. They block until the booking changes in STORES, or the mail id is added to `acknowledged_inquiries`.
