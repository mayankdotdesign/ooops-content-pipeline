# How the pipeline actually works — a plain-language walkthrough

Three automated jobs run in the background (GitHub Actions), plus
Claude doing the actual thinking/writing work when something needs
judgment. Nothing posts to Instagram without you approving it twice —
once on the words, once on the actual image.

**Updated 2026-09-17**: the three jobs no longer run on GitHub's own
`schedule:` trigger — it repeatedly proved unreliable (silently dropped
firings, sometimes for an hour+) across this build. All three are now
triggered by external cron jobs on cron-job.org hitting each
workflow's `workflow_dispatch` API endpoint instead — same effect as
someone clicking "Run workflow," just automated and actually reliable:

| Job (cron-job.org) | Fires | Hits workflow |
|---|---|---|
| "ooops IG posting - review cycle" | every 15 min, all day | `review-cycle.yml` |
| "ooops IG posting - daily post" | 4:30 AM & 6:30 AM IST | `daily-post.yml` |
| "ooops IG posting - track engagement" | 5:30 PM IST | `track-engagement.yml` |

**Updated 2026-09-17 (research)**: "Claude goes and reads Reddit/
Instagram" below used to mean generic web search, which turned out to
be unable to reliably verify anything on either platform (an audit
found every IG follower-count citation from an earlier batch was
fabricated 4x-1,000x too high, and zero real Reddit citations existed
despite the intent). Research now goes through the **Scrape Creators
MCP connector** — a real, paid-API-backed scraper (not a hobby
project) that returns genuine posts, comments, and engagement numbers
(likes/comments/upvotes/views) for both Instagram and Reddit, verified
against independent checks before being trusted. Every `source_note`
citation going forward must be a real, checkable permalink/URL — not a
plausible-sounding but unverified claim. Uses Scrape Creators credits
(track via `v1_account_credit_balance`); budget deliberately, don't
burn the free allowance on exploratory searches that don't ship.

The user can also supply real meme/reference images directly (e.g. a
screenshot of a quote graphic) — those go in `assets/meme-references/`
and get adapted via the `photo` slide layout, no research tool needed.

## A realistic week, step by step

**Monday — Claude drafts a new batch.** Phase 5 kicks off: Claude
searches Reddit/Instagram via the Scrape Creators connector for real,
relevant, currently-resonating posts, checks what's already worked
(`content_queue/performance.json`), and writes ~14 new posts — hook
text, caption, hashtags, CTA — following `docs/voice-guide.md` and the
hard content rules in `docs/ooops-context.md` (no fidelity/abuse
topics, no overclaiming the app exists yet, etc). Every post gets a
note on exactly which real, verified post inspired it (`source_note`
— a real permalink, checked, not assumed). Committed to
`content_queue/queue.json` as
`"drafted"`.

**Within ~15 minutes — content review sheet appears.** The next
"review cycle" cron-job.org tick runs `scripts/review_cycle.py`, which
notices drafted posts sitting there, writes one row per post into a
fresh tab in the Google Sheet
(`content-2026-09-22`, say), and emails a notification with a link.
Each row has the text, caption, hashtags, CTA — no images yet, nothing's
rendered.

**You review the words.** Go through the rows, mark each row's
**Content Status**: Approved / Need Change / Rejected, with a comment
in **Content Comments** wherever something needs to change.

**Each row processes independently, as soon as it's filled in** — you
don't have to finish every row before any of them move:
- **Rejected** rows are dropped from the queue entirely.
- **Need Change** rows pause — Claude reads your comment, fixes the
  actual post, and clears the comment to signal it's done. The next
  cron tick pushes the fix back into that *same row*, clears its
  status so you can look again, and emails you that a revision is
  ready — same as the first-time review email. Can loop a few times.
- **Approved** rows move to "content approved" — but don't render yet.

**Rendering only starts once the WHOLE batch's content is approved** —
this is deliberate (per your request): no image gets generated until
every post in the batch is either approved or dropped, so no render
effort is wasted on copy that might still change. Once that's true, the
automation renders every approved post's actual Instagram-ready image
(1080x1080, "ooops" logo top-right, "ooopsapp.com" bottom-center,
text always vertically centered — locked in 2026-09-17) and fills in
an **Image Link(s)** column on the *same rows, same tab* — each URL is
a real clickable hyperlink, not just plain text, even for a carousel's
multiple images in one cell. No new tab, just new columns appear.
Another email tells you it's ready.

**You review the visuals.** Click the image links, mark **Visual
Status** / **Visual Comments** the same way, on the same rows. Same
loop: Need Change → Claude fixes and re-renders → same row updates;
Rejected → dropped; Approved → that post is now `"queued"`, fully done,
waiting to post.

**Posting happens on its own schedule.** `.github/workflows/daily-post.yml`
looks for the oldest `"queued"` post and publishes it to Instagram —
2x/day (4:30 AM & 6:30 AM IST), no app-promo posts per what you asked
for a few weeks starting 2026-09-17 (docs/build-plan.md). Carousels
work fine (tested end-to-end with a real 3-slide post the same day).
It pulls the caption and the already-approved image(s); nothing new
gets generated at post time.

**After it's live, a third job tracks performance.**
`.github/workflows/track-engagement.yml` pulls real Instagram Insights
(reach, likes, saves) daily at 5:30 PM IST into
`content_queue/performance.json`,
which Claude reads the next time it drafts a batch — so research and
writing get better informed by what's actually working over time.

## Where Claude comes in vs. what's fully automatic

| Always needs Claude | Fully automatic |
|---|---|
| Drafting a new weekly batch (Phase 5 research + writing) | Writing the review sheet, emailing notifications |
| Fixing a "Need Change" item (content or visual) | Checking the sheet for filled-in rows |
| Any policy/design decisions (e.g. "no app_promo for a few weeks") | Rendering approved posts |
| | Posting queued items to Instagram |
| | Pulling engagement data |

## The one Google Sheet

One spreadsheet (`GOOGLE_SHEET_ID`), one tab per weekly batch, named by
the date it started (e.g. `content-2026-09-22`). That tab carries the
batch through its *entire* lifecycle — columns:

`Post ID | Content/slide text | Caption | Hashtags | CTA | Post type | Content Status | Content Comments | Image Link(s) | Visual Status | Visual Comments`

The first six columns are written once, when the batch starts. Content
Status/Comments are yours to fill in during content review. Image
Link(s) gets filled in automatically once the whole batch's content is
approved. Visual Status/Comments are yours to fill in during visual
review. A new tab only ever appears for a genuinely new weekly batch —
revision rounds reuse the same tab, same rows.

## Reels (experimental, `reels-pipeline` branch, not live yet)

Static image posts can also render as vertical video Reels instead of
(or alongside) the flat PNG — same approved caption text, animated.
Lives entirely in `reel-studio/` (a Remotion project, gitignored
`node_modules`), separate from the Python pipeline above until it's
proven out. Not wired into `review_cycle.py` or `daily-post.yml` yet —
building/reviewing reels today is a manual step, done from this branch.

**Two templates**, both built from [remocn](https://remocn.dev) (a
free, MIT-licensed shadcn-style component registry for Remotion,
installed as a Claude Code skill — `npx skills add
https://github.com/Remocn/remocn/tree/main/skills/remocn -g`) plus
`@remotion/effects`:

- **Paper** (`PaperReel` light / `PaperReelCoral` coral) — the brand
  gradient background with a subtle animated paper-grain texture
  (`@remotion/effects`'s `paper()`, opacity 1 / blend mode
  `color-burn` on light, `screen` on coral — coral needed its own
  tuning, the light-variant values blew it out) and text that reveals
  word-by-word with every individual letter carrying its own tiny
  stop-motion wobble (`@remocn/paper-wobble`).
- **Grain gradient** (`GrainGradientReel`) — a live WebGL shader
  background (`@remocn/shader-grain-gradient`, the `blob` shape) drifting
  slowly in Ooops' coral, `scale: 8 / intensity: 0 / softness: 0.7` so
  the blob's own edge stays off-canvas and it reads as ambient wash, not
  a sticker. Same letter-wobble text as Paper.

Both templates take a `slides: string[]` prop (not just one string) —
a multi-slide carousel post (e.g. id 14's 3-slide arc) sequences each
slide through the same video, ~5s per slide, with a short fade at each
cut (`PaperSlides.tsx`). Duration is computed from `slides.length` via
Remotion's `calculateMetadata`, not hardcoded.

**Safe zones are real, not eyeballed** — text sits inside
`x: 80-900, y: 260-1740` on the 1080x1920 canvas (`safeZone.ts`),
measured directly off Remotion's own IG Reels reference overlay
(`elements/overlays/social-safe-zones`), so nothing lands under the
right-side like/comment/share rail or the caption/nav chrome.

**Audio: Mixkit and Chosic only** — both confirmed genuinely
attribution-free for commercial use (unlike Pixabay, whose free tier
needs a login to download, or the initial prototype's incompetech.com
track, which is CC-BY and would have needed a credit line in every
caption). Tracks live in `reel-studio/public/audio/`, picked per post
by mood rather than one track on repeat:
- `owies-ukulele.mp3` (Mixkit) — warm/playful, for lighter bickering angles
- `smile.mp3` (Mixkit) — light happy pop, general relatable
- `well-be-okay.mp3` (Mixkit) — warm/romantic, for LDR/sentimental angles

**Rendering needs `--gl=angle`** — both templates use WebGL
(`paper()`'s canvas effect, the shader gradient), which
`npx remotion render` can't access without that flag (or
`chromiumOptions: { gl: "angle" }` via the Node API). Whoever/whatever
renders these — a person locally or, later, a GitHub Actions step —
needs to pass it explicitly or the render fails outright.

To open the live editor and adjust a template's colors/opacity/shader
params by eye instead of guessing in code: `cd reel-studio && npm
install && npx remotion studio` — every tunable is a zod-schema prop,
so Studio's Props panel renders real sliders/dropdowns, not just a raw
JSON blob.
