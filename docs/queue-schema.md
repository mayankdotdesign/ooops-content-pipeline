# content_queue/queue.json schema (Phase 4)

Each item:

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
  "source_note": "",
  "created_at": "...",
  "ig_media_id": null,
  "review_tab": null
}
```

## Fields

- `id` — int, unique, sequential.
- `post_type` — `"relatable"` (majority, no branding at all) or
  `"app_promo"` (occasional; a single-slide app_promo post gets the
  small corner watermark, a multi-slide app_promo carousel gets the
  watermark on no slide and instead ends with a dedicated
  `logo_endcard` slide as its last entry). See "Logo placement" below —
  this is not optional per-item config, it's derived from `post_type` +
  `slides` length + position, enforced by the renderer, not something a
  content-drafting step should try to set directly.
- `slides` — array, length 1-10. Length 1 = single-image post, 2+ =
  carousel. Each entry: `{"layout": ..., ...layout-specific fields}`.
  - `layout: "hook"` — `{"text": "..."}` (paragraphs separated by `\n\n`)
  - `layout: "bullet_list"` — `{"items": ["🚩 ...", "❤️ ...", ...]}`
    (each item is emoji + text, rendered as one line)
  - `layout: "stat_card"` — `{"stat": "$180", "caption": "..."}`
  - `layout: "photo"` — `{"photo_path": "...", "caption": "..."}`
    (`photo_path` relative to repo root)
  - `layout: "logo_endcard"` — no fields needed; fixed branded slide.
    **Only valid as the literal last slide of an `app_promo` carousel.**
    The renderer errors if it appears anywhere else.
- `bg_variant` — `1` (BG1, light) or `2` (BG2, coral). Applies to the
  whole post; carousels don't currently mix backgrounds mid-post.
- `caption`, `hashtags` (max 5, existing hard constraint), `cta` — the
  actual IG post text, built the same way `post_to_instagram.py` always
  has.
- `angle` — content angle tag (`jar_entry`, `ldr_pain`, etc.), used for
  performance logging (Phase 3) and Phase 5's mix requirements.
- `stage` — one of: `drafted`, `content_review`, `content_approved`,
  `content_needs_change`, `rendered`, `visual_review`,
  `visual_needs_change`, `queued`, `posted`. See Phase 6 for the
  transition logic — this file only defines the enum, not when each
  transition fires.
- `reviewer_comments` — free text from the review sheet's "My Comments"
  column, empty string when unused. When an item is `*_needs_change`
  and Claude Code has revised it, **clearing this back to `""` is the
  signal** that `scripts/review_cycle.py`'s resubmit step picks up —
  reviewer_comments non-empty on a `*_needs_change` item means "still
  waiting on a fix," don't touch.
- `source_note` — optional. Phase 5's per-post research citation
  (specific Reddit thread/comment or IG post that inspired the draft).
  Not shown to end users.
- `created_at` — ISO 8601 timestamp.
- `ig_media_id` — set by `post_to_instagram.py` after a successful
  publish; null/absent before that. Required by
  `scripts/track_engagement.py` (Phase 3) to pull insights.
- `review_tab` — the Google Sheets tab name (e.g. `content-2026-09-17`)
  this item is/was actively under review in. Set when an item enters
  `content_review` or `visual_review`. Revisions (`resubmit_*_review`
  in `review_cycle.py`) reuse this same tab rather than creating a new
  one each round — a fresh tab only gets created for a genuinely new
  weekly batch. null/absent before an item has ever entered review.

## Logo placement (derived, not a separate field)

Resolved 2026-09-16/17, see the build-plan status log for the full
reasoning:

- `post_type: "relatable"` → never branded, no watermark, no
  `logo_endcard`, regardless of slide count.
- `post_type: "app_promo"`, `len(slides) == 1` → that one slide renders
  with the small corner watermark (`design_system.draw_watermark`).
- `post_type: "app_promo"`, `len(slides) > 1` → every slide unbranded
  EXCEPT the last, whose `layout` must be `"logo_endcard"`.

## Where rendering actually happens

Per Phase 6, images are rendered during the **visual-approval cycle**
(`content_approved` → render → `rendered` → `visual_review`), not on
publish day. By the time an item reaches `stage: "queued"`, its
image(s) already exist in `content_queue/rendered/` and are already
committed/pushed. `daily-post.yml` only posts `queued` items — it does
not render anything itself. This is why the old "render, commit, sleep
8, post" sequence collapsed to just "post" in the new workflow; see
`.github/workflows/daily-post.yml`.

## Rendered image paths

- Single-slide item: `content_queue/rendered/<id>.png`
- Carousel item: `content_queue/rendered/<id>/1.png`, `.../2.png`, ...
  (1-indexed, matches `slides` order)

## Reels (the only posted format from 2026-09-25)

A queued item posts only if `content_queue/rendered/<id>.mp4` exists
(rendered from `reel-studio/`, see docs/pipeline-walkthrough.md's Reels
section). `daily-post.yml` skips items without one; `post_to_instagram.py`
refuses to post without one; there is no static fallback.
`media_type=REELS`, `share_to_feed=true` (also lands on the grid); Reels
process asynchronously, so `post_reel()` polls `status_code` until
`FINISHED` before publishing. **Order in `queue.json` is posting order.**

Optional per-item `reel` block (metadata for analysis, copied into
`performance.json` by the tracker): `template` (`paper-light` /
`paper-coral` / `grain`), `music` (file in `reel-studio/public/audio/`,
no extension), `stagger` (frames per word, default 6), `est_seconds`,
`slot` (`S1` = 23:00 UTC, `S2` = 03:00 UTC; historical posts use
`slot_utc`), `experiment` (e.g. `grain_test`, `send_cta_9-10s`).
