# Ooops Content Engine — Build Plan for Claude Code (v3)

Repo: https://github.com/mayankdotdesign/ooops-content-pipeline

This is a phased build. Do not skip ahead — later phases depend on earlier
ones. Where a phase says "wait," stop and ask the user rather than
guessing or proceeding with placeholder assets.

## Credentials — read this first, do not skip

Never put raw credentials (tokens, passwords, API keys) in this file, in
any file committed to the repo, or in chat. The repo is public.

- `IG_ACCESS_TOKEN` and `IG_ACCOUNT_ID` **already exist** as GitHub repo
  secrets from the original pipeline setup. Reference them as
  `secrets.IG_ACCESS_TOKEN` / `secrets.IG_ACCOUNT_ID` in workflow files,
  exactly as the existing `daily-post.yml` already does. Do not ask the
  user to paste these anywhere, and do not create new ones — they're
  already configured.
- New secrets needed for email (see "Email Setup" section below) follow
  the same rule: the user adds them directly via GitHub's Settings ->
  Secrets UI. Claude Code never sees or requests the raw values — it
  only references secret names in workflow YAML.

## Do not rebuild the existing pipeline from scratch

The posting pipeline already exists and is live (rendering, posting,
GitHub Actions cron). Read the current repo state first — key files:
`scripts/render_post.py`, `scripts/post_to_instagram.py`,
`.github/workflows/daily-post.yml`, `content_queue/queue.json`. Extend
this code, don't replace it wholesale.

**Non-obvious lessons from the original build — preserve these, don't
"fix" them without understanding why they're there:**
- The Instagram access token is an `IGAA`-prefixed token (Instagram API
  with Instagram Login). These tokens **only work against
  `graph.instagram.com`, not `graph.facebook.com`** — using the wrong
  base URL fails silently with confusing errors.
- Instagram caps hashtags at **5 per post** (changed Dec 2025, down
  from 30). Exceeding this gets the whole post request rejected.
- The GitHub Actions workflow needs `permissions: contents: write` set
  explicitly on the job — without it, the workflow can check out the
  repo but can't push the rendered image back, which fails with a 403.
- There's an ~8 second `sleep` after `git push` and before calling the
  Instagram API, to let GitHub's raw-content CDN catch up so Instagram
  can actually fetch the freshly-pushed image URL. Removing this can
  reintroduce a "media could not be fetched" failure.
- The repo must stay **public** — `raw.githubusercontent.com` URLs for
  private repos aren't fetchable by Instagram's servers.

---

## Cross-phase requirements (read this before starting Phase 0)

Two requirements affect multiple phases. Build them in from the start —
do not defer and retrofit later:

1. **Publishing is 2 posts/day, US-evening-timed, single OR carousel.**
   Phase 4's schema must support single/carousel via `slides` array
   length from the start. Phase 5's weekly batch must produce 14 posts
   (2/day x 7 days) from the start. Phase 7 only updates the cron
   schedule and publish-time logic.
2. **Logo appears only on app-marketing posts, not relatable/couple
   content posts.** Must exist in the schema (Phase 4) and in how
   research/drafting decides what to generate (Phase 5), not just in
   the renderer (Phase 2).

---

## Email Setup — REQUIRED before Phase 6, prompt the user immediately

The two-cycle approval flow (Phase 6) needs Claude Code to both **send**
review emails and **read replies** (the user replies to the same email
thread with an edited, attached spreadsheet once done). Sending alone
(SMTP) is not enough — reading replies needs IMAP access, which needs
setup only the user can do.

**At the very start of this build (during Phase 0), prompt the user to:**
1. Enable 2-Step Verification on their Gmail account, if not already on
2. Generate a Gmail **App Password** (Google Account -> Security ->
   2-Step Verification -> App Passwords) — a 16-character password
   separate from their normal login
3. Confirm IMAP is enabled (Gmail -> Settings -> Forwarding and
   POP/IMAP -> Enable IMAP)
4. Add two new GitHub repo secrets: `GMAIL_ADDRESS` and
   `GMAIL_APP_PASSWORD` (the user does this directly in GitHub's UI —
   Claude Code never handles the raw password)

**How the reply-based approval actually works once set up:**
- Claude Code sends the review email with the `.xlsx` attached, subject
  line following a consistent pattern (e.g. `Ooops Content Review —
  [date]`) so replies can be matched back
- A script polls the inbox via IMAP for a reply to that thread with an
  attachment
- Once found, that reply's attachment **is** the "returned" file — no
  special text/keyword needed in the email body, the presence of the
  reply with attachment is the signal that the user is done
- Download the attachment, parse the Status/Comments columns, proceed
  per Phase 6's stage transitions

Do not build Phase 6 until this setup is confirmed done — surface the
steps above to the user before writing any Phase 6 code, so the
approval cycle doesn't break on first real use.

---

## Phase 0: Asset Intake (BLOCKING — wait for user)

The user will provide, via this repo or direct upload:
- `assets/logo/ooops-logo.png` (exact filename TBD by user)
- `assets/backgrounds/bg-1.png` and `assets/backgrounds/bg-2.png`
- Screenshots of reference couple-chat-style posts (for Phase 1 voice study)
- Sample posts designed by the user in Figma, saved under
  `assets/design-reference/` — the primary visual spec for Phase 2

**Do not generate background textures, gradients, or noise.** The user
designs BG1/BG2 externally and hands you finished files — load and use
them as-is, resize/crop to 1080x1350 only.

**Do not add text-legibility treatments (semi-transparent panels, etc.)
on your own judgment** — the user verifies this in Figma before handoff.

**Also prompt the user for Gmail App Password setup here** (see "Email
Setup" above) — don't wait until Phase 6 to discover it's missing.

---

## Phase 1: Voice Calibration (BLOCKING — depends on Phase 0 screenshots)

1. Study the user's screenshots — real couple-chat text aesthetics:
   imperfect punctuation, natural texting rhythm, tone that reads as a
   person, not a brand
2. Supplement with broader research into authentic relationship/LDR
   text content
3. Write findings to `docs/voice-guide.md` — concrete dos/don'ts,
   example phrasings, patterns to avoid
4. Every future caption/text-generation step must read this file first

Living document — update as more material comes in.

---

## Phase 2: Design System

- Build slide layout types using the **user's Figma samples as the
  visual spec**:
  - `hook`, `bullet_list`, `photo`, `stat_card`
  - `logo_endcard` — **only for `post_type: app_promo` items**, never
    on `post_type: relatable` posts
- Font: Nunito (already in repo, `assets/fonts/`) — the repo now has
  the full family (Regular, Medium, SemiBold, Bold, ExtraBold, Black +
  italics, 16 files). **Do not default to "first file found" font
  loading** — this was a real bug in the original single-font renderer
  and will pick an arbitrary weight now that 16 variants exist. Match
  font weight to what's actually used in the corresponding Figma
  design-reference sample for that slide type. If the user explicitly
  states a weight when sharing a specific creative, that instruction
  overrides the design-reference inference.
- No texture/grain generation, no auto-legibility panels

---

## Phase 3: Engagement Tracking

- Pull Instagram Insights (reach, likes, comments, saves, shares) per
  post via the Graph API — use `graph.instagram.com`, matching the
  existing posting script's base URL
- Store in `content_queue/performance.json`, keyed by post ID
- Log BG variant, content angle, and `post_type` per post
- Runs daily via GitHub Actions cron

---

## Phase 4: Queue Schema

```json
{
  "id": 1,
  "post_type": "relatable",
  "slides": [
    { "layout": "hook", "text": "..." },
    { "layout": "bullet_list", "items": ["item 1", "item 2"] }
  ],
  "bg_variant": 1,
  "caption": "...",
  "hashtags": ["#...", "..."],
  "cta": "...",
  "angle": "...",
  "stage": "drafted",
  "reviewer_comments": "",
  "created_at": "..."
}
```

- `post_type`: `"relatable"` (majority, no logo) or `"app_promo"`
  (occasional, uses `logo_endcard`)
- `slides` length: 1 = single-image post, 2-10 = carousel
- `stage`: `drafted -> content_review -> content_approved -> rendered
  -> visual_review -> queued -> posted` (or `content_needs_change` /
  `visual_needs_change`, looping back for revision)
- Remember: hashtags array must stay <= 5 items (existing constraint
  from the live pipeline)

---

## Phase 5: Weekly Research & Batch Generation

1. Read `docs/voice-guide.md` (mandatory every cycle)
2. Read `content_queue/performance.json` if populated
3. Research from **both** Reddit (US/UK subs — r/LongDistance,
   r/relationships, r/dating_advice) **and Instagram directly** — both
   are required sources, not Reddit-primary with IG as an afterthought
4. Western (US/UK) audience focus — USD, US-relatable scenarios
5. Draft 14 posts/cycle (2/day x 7 days)
6. Mix `post_type` (mostly relatable, occasional app_promo) and
   single/carousel formats; alternate `bg_variant` roughly evenly
7. Write to `queue.json` with `"stage": "drafted"`
8. Commit and push

### Depth requirements — this research must not be shallow or generic

Quality here is determined by these constraints, not by how much time is
spent. Enforce all of the following:

- **Minimum source count**: at least 20 distinct Reddit threads/comments
  and 15 distinct Instagram posts/accounts reviewed before drafting
  begins, across the full batch — not per post, but the batch shouldn't
  be drafted from a handful of searches.
- **Per-post source note**: each of the 14 drafted posts must include an
  internal note (in the commit message or a `source_note` field, not
  shown to the end user) citing the specific thread, comment, or IG post
  that inspired it. If a post can't point to a specific real source, it
  wasn't researched — it was generated from general training knowledge,
  which is exactly what this pipeline is trying to avoid.
- **No source reuse**: two posts in the same batch should not draw from
  the same source. Fourteen distinct real inputs are required for
  fourteen posts, not one good thread stretched thin.
- **Cliché avoidance list**: explicitly avoid generic relationship-
  content tropes that read as AI-generated regardless of source
  research — phrases like "communication is key," generic love-quote
  templates, or anything that could have been written without reading a
  single real post. Cross-check every draft against `docs/voice-guide.md`
  specifically for this.
- **If genuinely good material isn't found for all 14 slots**: draft
  fewer, well-sourced posts rather than padding the batch with weaker,
  generically-written ones to hit the number. Flag the shortfall to the
  user rather than silently lowering quality to meet volume.

---

## Phase 6: Two-Cycle Approval (same day, Excel-based, email reply-driven)

Requires the Email Setup section above to be complete first.

### Cycle 1: Content approval
1. For `drafted` items, generate `.xlsx` at
   `content_queue/review/content-review-[date].xlsx` with columns: Post
   ID, Content/slide text, Caption, Hashtags, CTA, Post type, Status
   (dropdown: Approved / Need Change / Rejected), My Comments
2. Items -> `"stage": "content_review"`
3. Send email (see Email Setup) with the file attached, consistent
   subject line for reply-matching
4. Poll inbox via IMAP for the user's reply with attachment
5. Parse returned file:
   - `Approved` -> `"stage": "content_approved"`
   - `Need Change` -> apply `My Comments`, regenerate, loop to
     `"stage": "content_review"` for a fast same-day re-check
   - `Rejected` -> drop from queue

### Cycle 2: Visual approval (same day, after Cycle 1)
1. Render images/carousels for `content_approved` items ->
   `"stage": "rendered"`
2. Generate `.xlsx` at `content_queue/review/visual-review-[date].xlsx`
   with: Post ID, image/carousel link(s), caption (context), Status
   dropdown, My Comments
3. Items -> `"stage": "visual_review"`
4. Send second email same day, same subject-line/reply pattern
5. Poll for reply, parse:
   - `Approved` -> `"stage": "queued"`
   - `Need Change` -> re-render per comments, loop to `"stage": "rendered"`
   - `Rejected` -> drop from queue

No WhatsApp notification channel — email only, both cycles.

---

## Phase 7: Publishing Cadence Update

If Phases 4 and 5 were built correctly, this is only:
- Cron posts 2 `queued` items/day instead of 1
- Re-anchor posting time to US evening hours (was IST-peak)
- Confirm existing single/carousel branch logic works for both formats

If this phase needs schema, volume, or post_type changes, something was
built wrong earlier — fix the actual phase, don't patch here.

---

## Build order

Phase 0 (wait for assets + prompt Gmail setup) -> Phase 1 (wait for
screenshots, blocking) -> Phase 2 + Phase 3 (parallel) -> Phase 4 ->
Phase 5 -> Phase 6 (only after Email Setup confirmed) -> Phase 7.

---

## Status log

Keep this section updated as phases close out — it's the source of
truth for "where are we" across sessions, separate from the plan text
above (which doesn't change).

- **2026-09-15** — Phase 0 in progress. Gmail App Password done,
  `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` added as repo secrets. Nunito
  font family (16 files) uploaded to `assets/fonts/`, replacing the old
  placeholder `DMSans-Bold.ttf`. Intake folders created:
  `assets/logo/`, `assets/backgrounds/`, `assets/design-reference/`,
  `assets/voice-reference/` — waiting on actual files in each. Old
  pre-plan test queue entries (5 items, flat schema) cleared from
  `content_queue/queue.json`; the one test render
  (`content_queue/rendered/1.png`) was removed — it was never actually
  published to Instagram (queue status never reached `"posted"`), only
  rendered and committed.

- **2026-09-15 (later)** — Logo (`Logo.png`, 815x254), both backgrounds
  (`BG1.png` light peach, `BG2.png` coral, both 1620x2025 — will
  downscale to 1080x1350), and 6 design-reference files verified
  (`Reference_text_post_1/2`, `Reference_image_post_1/2`, `IG carousel`,
  `Webpage UI` — each as matched PNG+SVG pairs, SVGs confirmed
  well-formed Figma exports). `voice-reference/` still empty — user is
  adding those separately, Phase 1 stays blocked until they land.

  **Typography spec confirmed for Phase 2**: Nunito **Bold**, -3%
  letter-spacing, 100% line-height. Matches what's visible in the
  reference PNGs (tight tracking, no extra leading).

  **Emoji rendering researched for Phase 2** (Pillow can't draw color
  emoji from a plain unicode string by default): Apple's actual iOS
  emoji artwork (`Apple Color Emoji`) is proprietary and not
  redistributable — can't legally ship it in this public repo. Two free
  options: **Noto Color Emoji** (Google, OFL 1.1, no attribution
  required, ships as one large ~10-25MB font with fixed-size color
  strikes) or **Twemoji** (CC-BY 4.0, attribution needed — a README
  credit line is enough per the project's own guidance). Given the
  reference designs use a small, curated emoji set (🚩❤️🎮😴😬🎉📦🍕🛏️😤 etc.)
  as bullet markers/chips rather than arbitrary user text, the planned
  approach is: pull just the needed Twemoji PNGs as static assets and
  `Image.paste()` them onto the canvas at render time, rather than
  bundling a multi-MB emoji font — avoids Noto Color Emoji's fixed
  bitmap-size quirk and keeps the repo light. Add a Twemoji credit line
  to the README when this ships.

  **Open question raised with user, not yet resolved**: the reference
  posts show a small corner "ooops" watermark badge (+ `ooopsapp.com`
  text on the text-post layout) on posts that are clearly `relatable`
  content (the LDR/jar posts), not `app_promo`. This appears distinct
  from the big `logo_endcard` slide (seen as the *last* slide of the IG
  carousel reference, with the large logo + "join the waitlist" CTA) —
  reading is: small watermark = on every post regardless of
  `post_type`; big `logo_endcard` layout = `app_promo`-only, per the
  original rule. Needs explicit user confirmation before Phase 2 encodes
  it either way.
