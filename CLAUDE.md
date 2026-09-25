# Working rules for Claude in this repo

## Review before anything goes live (set by the user, 2026-09-25)

- **Only create content when the user says so.** New reels, music picks,
  copy rewrites, covers: don't render or draft them until the user
  explicitly asks ("go", "create the reels", etc.). Proposing and
  discussing is fine; producing is on request.
- **Everything created gets reviewed by the user first.** Send the actual
  output (the rendered mp4s, the copy, the track list) and wait for
  approval. Nothing enters `content_queue/` as postable, and nothing gets
  committed as `queued` with a rendered `.mp4`, until the user has
  approved that exact output.
- **Posting is live.** A queued item with `content_queue/rendered/<id>.mp4`
  on `main` will post at the next 23:00 / 03:00 UTC slot. Treat committing
  one as publishing.
- **Analysis:** before reporting results, pull every data source
  (`content_queue/performance.json`, `account_insights.json`,
  `tracking_meta.json`, Scrape Creators, dashboard screenshots), check for
  confounded variables, and don't present hypotheses as findings.

## Reel batch rules

- Every post is a Reel (no static posts). Paper templates (light/coral);
  grain gradient only as a deliberate test.
- No music track repeats within a batch (repeats across batches are OK).
  Tracks must be free/no-attribution (Mixkit, Chosic), and fit the brand:
  warm, mellow, adult -- never childish or horror/eerie. Only the first
  ~10 seconds play.
- Reel text/settings come from `queue.json` via
  `python scripts/export_reel_posts.py`; never hand-edit
  `reel-studio/src/reelPosts.json`.

See `docs/pipeline-walkthrough.md` for how the pipeline works.
