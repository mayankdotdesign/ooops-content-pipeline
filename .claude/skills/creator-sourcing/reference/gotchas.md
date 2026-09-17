# Data-quality landmines

Every item here was hit in a real run and produced (or nearly produced) a wrong
answer. The scripts already handle them — this file explains *why*, so you don't
"simplify" the handling away.

## 1. Pinned posts break chronological order — never use `edges[0]`

The Instagram grid returns up to 3 pinned posts first, and pinned posts are often
old. In one 58-creator run, the first post in the grid was older than the newest by:

| creator | first-vs-newest gap |
|---|---|
| crystxl.am | 686 days |
| itspierreboo | 651 days |
| drgts_dermatology | 430 days |

**Recency must be `max(taken_at_timestamp)`.** Using `edges[0]` would have wrongly
dropped many *active* creators as stale under a 60-day rule. This is the single
most dangerous bug in the pipeline because the output looks perfectly plausible.

Side effect: the 12 returned posts are the *grid's* 12, not the 12 most recent.
Pinned posts are usually top performers, which inflates the mean. `pinned_in_sample`
records how many, so the skew is visible.

## 2. Like counts are null or -1 when hidden — don't average them

- `edge_liked_by.count` can be `null`.
- `edge_media_preview_like.count` can be `-1`.
- `like_and_view_counts_disabled: true` marks posts with likes switched off.

These are *different* states and they don't always agree. Rules:

1. take `edge_liked_by.count` if it's an int `>= 0`
2. else take `edge_media_preview_like.count` if it's an int `>= 0`
3. else the value is genuinely unavailable → `null`

In jq, beware: `null < 0` is **true**, so `map(select(.<0))` silently counts nulls
as negatives. Test with `select(.==null)` and `select(.<0)` separately.

A creator hiding likes on all 12 posts gets `engagement_rate: null`. Show that as
`—`, never as `0%` — a zero implies measured-and-bad, a dash implies not-measurable.

## 3. A 12-post mean is dominated by one viral post

This is not an edge case; in one run **28 of 58** creators had a top post ≥5× their
median. The mean is not wrong, it's just not *typical*:

| creator | ER mean | ER median | top vs median |
|---|---|---|---|
| reneerouleau | 15.93% | 0.17% | 1,062× |
| taylorwordenskin | 67.89% | 0.73% | 627× |
| crystxl.am | 68.64% | 8.24% | 71× |

Always compute both. The requested formula stays primary, the median rides along,
and the dashboard toggles between them. Reporting only the mean will send someone
to pitch a creator whose typical post gets 0.17% engagement.

Sanity check: organic Instagram engagement is roughly 1–6%. Anything above ~15%
is a viral spike, a tiny-follower account, or a bug — go look at the raw post array
before believing it.

## 4. Some handles break the MCP transport, deterministically

Certain profiles fail with `Failed to parse SSE message: Invalid JSON: EOF while
parsing a string`. This is **not** transient and **not** concurrency:

- same handles fail across 3 attempts
- they fail on `v1_instagram_profile` *and* `v2_instagram_user_posts`
- other handles in the same parallel batch succeed

Fallback ladder:
1. retry once (rules out genuine flakiness)
2. try `v1_instagram_basic_profile` with the numeric `userId` — a much smaller
   payload that often succeeds. Get the id from the hashtag/reels post `owner.id`.
   It returns bio + followers but **no posts**, so metrics stay unavailable.
3. if both fail, record the handle in `unavailable` and surface it in the output.

Never let these vanish silently — a creator missing from a dashboard is
indistinguishable from a creator who was never found.

## 5. Reels search doesn't echo the query back

`v2_instagram_reels_search` responses contain no query field, so when several
spill to disk you cannot tell which file is which. Label by call order, then
**verify**: count a distinctive query word inside each file. In one run the file
labelled "skin barrier repair" contained 50 occurrences of "barrier" and the other
contained 0 — that confirms the mapping instead of assuming it.

`collect_pool.py` prints this check automatically.

## 6. Responses are enormous and spill to disk — that's fine

A single profile response is 250–780 KB. It exceeds the tool-result limit and gets
written to the session `tool-results` directory. Don't fight this: it keeps context
clean. Parse the files with `jq`/Python and never read them wholesale into context.

`trim=true` works but only saves ~12% (380 KB vs 433 KB) because the post array
dominates. Pass it anyway; don't expect it to solve size.

## 7. The profile endpoint already includes the last 12 posts

`data.user.edge_owner_to_timeline_media.edges` holds exactly 12 posts with
`edge_liked_by`, `edge_media_to_comment`, and `taken_at_timestamp`. So profile +
posts is **one call per creator, not two**. Halves both cost and wall-clock.

## 8. Discovery returns brands and off-topic accounts

`v1_instagram_search_profiles` matches Google-indexed *captions*, not just bios, so
a cooking account that once mentioned "esthetician" lands in the pool. Roughly a
fifth of a raw pool is brands, retailers, or noise.

Don't silently filter it — the user asked for creators in a niche, and deciding
what counts as on-brand is their call. Surface it and say so.

## 9. Some emails belong to talent management, not the creator

Addresses on agency domains (`@select.co`, `@thedigitaldept.com`,
`@outshinetalent.com`, `@dulcedo.com`) are management, not the creator. They're the *correct* contact for a paid
partnership, but the pitch differs from a cold note to a solo esthetician. Tag them
(`contacts.py` does) rather than presenting them as personal addresses.

## 10. Link-in-bio pages hide contacts the bio doesn't have

Resolving Linktree/Komi surfaced 3 emails that were nowhere in the Instagram bio,
including one sitting in the Linktree **description** field rather than its
`email_address` field. Always regex the whole payload, not just the obvious key.

Komi URL forms matter: `http://x.komi.io/` returned 404 while `https://x.komi.io`
resolved. Retry with the other form before recording a failure.
