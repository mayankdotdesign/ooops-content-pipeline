# Per-platform endpoint map

All tools are ScrapeCreators MCP tools. The server id is an opaque UUID — find it
with a keyword `ToolSearch` (e.g. `instagram profile scrape`) rather than assuming
one. See the `scrapecreators-api` skill for the full routing tables.

Most calls cost **1 credit**. A full run is roughly `searches + creators + link-in-bio`
calls — a 66-creator Instagram run cost about 115 credits end to end.

---

## Instagram — verified, this is the reference implementation

| Stage | Tool | Notes |
|---|---|---|
| Profile search | `v1_instagram_search_profiles` | `query`; returns bio + followers inline. Matches Google-indexed captions too — brings noise. Pages 1–11. |
| Hashtag search | `v1_instagram_search_hashtag` | `hashtag` (no `#`); owners carry followers but **no bio** |
| Reels search | `v2_instagram_reels_search` | `query`; **no query echoed in response** — see gotchas §5 |
| Profile + posts | `v1_instagram_profile` | `handle`, `trim=true`. Returns last 12 posts inline — one call, not two |
| Fallback profile | `v1_instagram_basic_profile` | `userId`; small payload, survives the SSE bug, but **no posts** |
| Fallback posts | `v2_instagram_user_posts` | `handle`; separate posts feed |

Metric field paths (under `data.user`):

```
followers  edge_followed_by.count
posts      edge_owner_to_timeline_media.edges[].node
  likes      .edge_liked_by.count   → fallback .edge_media_preview_like.count
  comments   .edge_media_to_comment.count
  timestamp  .taken_at_timestamp        (use max(), not [0] — gotchas §1)
  pinned     .pinned_for_users
```

---

## TikTok — VERIFIED (skincare run, Aug 2026)

| Stage | Tool | Notes |
|---|---|---|
| Profile search | `v1_tiktok_search_users` | `query`. Returns follower_count but **NO `signature`/bio**, contrary to the tool description. Matches handle strings literally — searching a phrase like "skin barrier" returns 30 micro-accounts whose handle contains it, all under 1K followers. |
| Hashtag search | `v1_tiktok_search_hashtag` | `hashtag`; items under `aweme_list[]`. Authors carry `signature` but **`follower_count` is always 0**. |
| Keyword search | `v1_tiktok_search_keyword` | `query`. With `trim=true` items are **flat** (`.author`, `.statistics`), NOT nested under `aweme_info` as documented. Authors carry real follower counts. |
| Profile | `v1_tiktok_profile` | `handle`. Gives `user.signature`, `user.bioLink.link`, `statsV2.followerCount` (precise string; `stats` is rounded). `itemList` is always empty — **no posts**. |
| Posts + followers | `v3_tiktok_profile_videos` | `handle`, `trim=true`. Returns **10** videos (not 12) AND `author.follower_count` — so this is **one call per creator**, same as Instagram. |

Field paths (per item in `aweme_list`):

```
likes     .statistics.digg_count
comments  .statistics.comment_count
views     .statistics.play_count
timestamp .create_time            (unix; .create_time_utc also present)
followers .author.follower_count  (populated here, zeroed in hashtag search)
```

**Pinned posts: there is no flag.** TikTok has no `pinned_for_users` equivalent and
`sort_by=latest` still returns pinned videos first. One creator's first three videos
were from 2023 followed by 2026 posts. Detect by scanning from the head while
`ts[i] < max(ts[i+1:])`, and take recency from `max(create_time)` (gotchas §1).

**The follower-based engagement rate is meaningless on TikTok.** The For You page
distributes beyond followers, so likes routinely exceed follower count. In a
70-creator run the median ER on followers was **7.67%** and 11 creators scored
**over 100%** — one at 334% (131K avg likes on 39K followers). Use
`(likes + comments) / views`; that same pool had a median of **5.0%**, which is a
real number. Compute the follower-based one if asked, but never lead with it.

## YouTube — endpoints exist, response shapes NOT yet verified

| Stage | Tool |
|---|---|
| Search | `v1_youtube_search` |
| Hashtag | `v1_youtube_search_hashtag` |
| Channel | `v1_youtube_channel` |
| Videos | `v1_youtube_channel_videos` (cursor: `continuationToken`) |
| Shorts | `v1_youtube_channel_shorts` |

YouTube has no "likes ÷ followers" convention that maps cleanly to an Instagram
engagement rate — views are the primary metric and subscriber counts are often
hidden. Agree the formula with the user before computing anything.

---

## Adding a platform

1. Confirm the tools exist via keyword `ToolSearch`.
2. Fetch **one** creator and dump top-level keys plus one post's keys.
3. Write the field paths into this file before running the batch.
4. Only then run the fleet — a wrong field path across 60 creators wastes the
   whole run's credits and produces confident, wrong numbers.
