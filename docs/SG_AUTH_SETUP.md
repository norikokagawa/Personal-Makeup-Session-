# Authentication setup (Gmail / Canva / Metricool)

Keep `DRY_RUN=true` and `AUTO_PUBLISH=false` until every check below is `OK`.

Never paste a token, secret or password into chat, an issue, a commit or a terminal command line. The repository is **public**: Actions logs, artifacts and issues can be seen by others.

## 0. Current state (investigated 2026-10-12)

| Secret | Used by | Status |
|---|---|---|
| `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` | `daily-instagram-post.yml` (existing, manual-only, last run 2026-05-31) and `sg-calendar-daily.yml` (new) | refresh → **400** (`invalid_grant` type). No token-issuing script exists in the repo, so it was issued by hand. Most likely cause: OAuth app in *Testing* status → refresh tokens expire after 7 days |
| `CANVA_CLIENT_ID` / `CANVA_CLIENT_SECRET` / `CANVA_REFRESH_TOKEN` | both workflows above | refresh → **400 `invalid_grant` "Invalid refresh token"**. Canva refresh tokens are **single-use**; each refresh returns a new one that must be saved. The existing `daily_post.py` treats a failed save as "non-fatal", so one failed save leaves a dead token |
| `GH_PAT` | both workflows (save the rotated Canva token) | unknown. `auth-check` reports it without showing it |
| `IG_USER_ID` / `IG_ACCESS_TOKEN` | existing workflow only | not touched |
| `METRICOOL_*` | new workflow only | not set |

**Impact of overwriting.** Only the two workflows above use these secrets, and `deploy.yml` uses none. Both target the same Gmail account and the same Canva integration, so new tokens fix both. Nothing else needs to change.

Caveats:
- After re-issue, the two workflows must **not run at the same time**. Both consume the one-time Canva token. The new workflow runs one at a time (`concurrency: canva-refresh-token`); just don't trigger the old one manually during tests.
- The existing `daily_post.py` prints the first 6 characters of `CANVA_CLIENT_SECRET` to its (public) log. The new code never prints secrets. Consider regenerating the Canva client secret while you are re-issuing (step 2), and avoid running the old workflow.
- The root-level `get_canva_token.py` prints the client secret and refresh token to the terminal. Use the new script instead.

## 1. Gmail — `GMAIL_REFRESH_TOKEN`

Google Cloud Console → the project that owns the existing OAuth client:

1. **APIs & Services → OAuth consent screen (Google Auth Platform → Audience)**
   - `atelier-r-make.com` on Google Workspace → choose **User type: Internal**. Refresh tokens then do not expire weekly and no verification is needed.
   - Otherwise → **Publish app (In production)**. `gmail.readonly` is a restricted scope: Google shows an "unverified app" warning that you can pass for your own account. Tokens no longer expire after 7 days.
2. **Clients**: the client must be type **Desktop app** (loopback `http://127.0.0.1` redirect). If the existing one is a Web client, create a Desktop client.
3. **Data access**: only `.../auth/gmail.readonly` is needed (both workflows only read mail).
4. On your Mac, in a clone of this repo:
   ```
   brew install gh && gh auth login        # first time only
   pip3 install requests
   python3 scripts/auth/issue_gmail_token.py
   ```
   The client ID and secret are typed hidden. The script checks that the new token works, then runs `gh secret set` directly. Nothing is printed or saved to a file.
5. Optional: Google Account → Security → Third-party access → remove old grants of the same app.

## 2. Canva — `CANVA_REFRESH_TOKEN`

1. Canva Developer Portal → **Your integrations** → the integration with client ID `OC-AZ44ZCIXRVRk`.
   - Scopes: `asset:read`, `design:content:read` (same as now; enough for export).
   - Authentication → Redirect URL `http://127.0.0.1:8080` is registered (the existing script uses it).
   - Recommended: **Generate secret** to rotate the client secret (see the caveat above).
2. On your Mac: `python3 scripts/auth/issue_canva_token.py`. The secret is typed hidden. The new refresh token goes straight to `gh secret set CANVA_REFRESH_TOKEN`; if you regenerated the client secret, answer `y` to also update `CANVA_CLIENT_SECRET`.
3. From then on **only GitHub Actions uses that token**. Do not run the old token scripts again.

## 3. `GH_PAT` (needed to save the rotated Canva token)

GitHub → Settings → Developer settings → **Fine-grained tokens** → generate:
- Repository access: only `norikokagawa/Personal-Makeup-Session-`
- Permissions: **Secrets: Read and write** (Metadata: read is added automatically)
- Expiration: e.g. 90 days. Put a calendar reminder; the workflow stops with a clear message when it expires.

Then save it without showing it: `gh secret set GH_PAT --repo norikokagawa/Personal-Makeup-Session-` and paste at the hidden prompt.

## 4. Metricool — `METRICOOL_USER_TOKEN` / `METRICOOL_USER_ID` / `METRICOOL_BLOG_ID`

- **Availability:** the API is only on the **Advanced** and **Custom** plans. Check the current plan in Metricool → Billing.
- **Token:** Metricool → Account settings → **API**. It is sent as the `X-Mc-Auth` header. Regenerating it invalidates the old one immediately.
- **userId / blogId:** open the @r.makeup.session brand in the browser; both appear in the URL (`userId=…&blogId=…`). `blogId` is the brand, not the user.
- Save all three with `gh secret set METRICOOL_USER_TOKEN --repo …` (and the same for `METRICOOL_USER_ID` and `METRICOOL_BLOG_ID`).
- Check before go-live:
  - The Instagram account must be a **Business** account connected through Facebook for automatic stories. Creator-account stories go out as a phone notification instead.
  - Media URLs must be public and not expire. The workflow stores images on the public `instagram-media` branch.
  - The exact request fields for carousel and story posts must be confirmed against the official API docs (app.metricool.com/resources/apidocs) on the first non-public test, with drafts only.

## 5. Verify (shows only OK / FAIL)

The `auth-check` mode (in `.github/workflows/sg-calendar-daily.yml`) refreshes each credential and prints only `OK`, `FAIL: <reason code>` or `SKIPPED`:

- `GH_PAT (secrets write)`
- `Gmail`
- `Canva`: only with `check_canva=true`, because that consumes and re-saves the one-time token
- `Metricool`

After merging to `main` it can be started manually from the Actions tab. Until then it runs on pushes to the test branch.
