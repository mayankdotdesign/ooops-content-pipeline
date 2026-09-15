# Ooops Content Pipeline — 100% Free

## What this does
1. `scripts/generate_ideas.py` — Claude (via Claude Code) writes new post
   concepts into `content_queue/queue.json` weekly.
2. `scripts/render_post.py` — turns a queued idea into a styled 1080x1350
   image using Pillow (no paid image API).
3. `.github/workflows/daily-post.yml` — GitHub Actions cron, runs daily,
   free (public repos get unlimited Actions minutes; private repos get
   2,000 free min/month, plenty for this).
4. `scripts/post_to_instagram.py` — posts to IG via the free Graph API.

## One-time setup (do this part yourself — takes ~30-60 min, some of it
is a multi-day wait on Meta's side)

### Step 1 — Instagram account
1. Make sure @ooops.app is a **Professional (Business)** account
   (Settings → Account type).
2. Link it to a Facebook Page (create a barebones "Ooops" Page if you
   don't have one — free, takes 2 minutes).

### Step 2 — Meta Developer app
1. Go to developers.facebook.com → My Apps → Create App → "Business" type.
2. Add the **Instagram Graph API** product to the app.
3. Under App Review, request these permissions:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement`.
   - For a single account you own, Meta usually grants these without
     a lengthy review, but it can take a few days. This is the one
     step you can't rush.

### Step 3 — Get your long-lived access token + account ID
1. Use Graph API Explorer (developers.facebook.com/tools/explorer) to
   generate a short-lived token with the permissions above.
2. Exchange it for a long-lived token (60 days) via the
   `oauth/access_token` endpoint — instructions in Meta's docs.
   *(Ask me and I'll walk you through the exact curl command when
   you're at this step.)*
3. Get your `IG_ACCOUNT_ID` by calling
   `GET /me/accounts` then `GET /{page-id}?fields=instagram_business_account`.

### Step 4 — Push this repo to GitHub (needs laptop — GitHub's secrets
UI isn't great on mobile)
1. Create a new repo, push this folder.
2. Repo → Settings → Secrets and variables → Actions → add:
   - `IG_ACCESS_TOKEN`
   - `IG_ACCOUNT_ID`
3. That's it — the workflow runs daily and picks up the next queued post.

## Weekly content refresh (this is the "don't think about it" part)
Open this repo in Claude Code and say:
> "Generate 7 new post ideas for next week using generate_ideas.py's
> angles and content_queue/performance.json, then add them to the queue."

Claude Code reads your past performance, writes fresh ideas straight
into `queue.json`. No manual writing needed.

## Known limitation
Access tokens expire every 60 days — a calendar reminder to refresh it
is the one manual touchpoint left. This could be automated too but
needs a token-refresh cron, worth adding once the core loop is proven.
