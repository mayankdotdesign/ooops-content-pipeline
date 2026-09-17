---
name: creator-sourcing
description: >-
  End-to-end creator sourcing for influencer and partnership outreach. Discovers
  creators on a platform three independent ways (profile/bio search, hashtag
  search, reels/video search), enriches each with follower count, average likes
  and comments, engagement rate and last-post date, ranks by engagement, resolves
  public contact paths (bio emails and link-in-bio pages), and renders a
  filterable dashboard. Use when the user asks to source, find, research, vet or
  build a list of creators, influencers, or accounts in a niche — or mentions
  creator sourcing, influencer discovery, an outreach list, or a creator database.
  Inputs: platform, niche keywords, follower range, number of results.
allowed-tools: ToolSearch, Bash, Read, Write, Edit, Artifact
---

# Creator Sourcing

Turns a niche into a ranked, contactable creator list plus a dashboard.

**Requires the ScrapeCreators MCP connector.** Confirm it with a keyword
`ToolSearch` (e.g. `instagram profile scrape`) before promising anything; if no
tools come back, say the connector isn't attached and stop.

Read `reference/gotchas.md` before writing any metric code. Every rule in it
comes from a real failure, and several produce confident, plausible, wrong
numbers when ignored.

## Inputs

Collect these up front. Ask only for what's missing and genuinely changes the run;
otherwise use the defaults.

| Input | Default | Notes |
|---|---|---|
| `platform` | instagram | Instagram is verified end to end. TikTok/YouTube: read `reference/platforms.md` and verify field paths on one creator first. |
| `niche keywords` | — | Required. Needs 2–3 bio/profile terms, 2–3 hashtags, 2 video-search phrases. Derive them from the niche and **show the user the list before spending credits**. |
| `follower range` | no limit | Applied after enrichment, on the fresh follower count. |
| `how many results` | all | A cut-off applied after ranking, not during discovery. |

Also worth settling early: **mean or median engagement** for the ranking (see
gotchas §3), and whether the contact stage covers all results or just the top N.

## Pipeline

Set `CACHE` to the session tool-results directory — large responses spill there
and every script reads them from disk:

```bash
CACHE="$(dirname "$CLAUDE_SCRATCHPAD")/tool-results"   # or locate it from a tool result path
```

### 1 · Discover — three independent ways

Run all searches **in one parallel batch**. Three methods matter because each
surfaces creators the others miss, and anyone found by 2+ is a stronger signal.

- profile/bio search × each keyword — `v1_instagram_search_profiles`
- hashtag search × each hashtag — `v1_instagram_search_hashtag`
- reels/video search × each phrase — `v2_instagram_reels_search`

Profile-search results usually return inline; write them to
`scratch/profile-search.json` as `{"<query>": [{username,url,follower_count,biography}]}`.
Hashtag and reels results spill to `$CACHE` on their own.

```bash
python3 scripts/collect_pool.py --cache-dir "$CACHE" \
  --inline scratch/profile-search.json \
  --reels-queries "phrase one,phrase two" \
  --out output/raw-pool.json
```

**Check the reels label output it prints** before continuing (gotchas §5).

### 2 · Enrich

One `v1_instagram_profile` call per handle with `trim=true`. It returns the last
12 posts inline, so this covers profile *and* posts in a single call. Batch ~16 at
a time. Handles that fail with an SSE parse error need the fallback ladder in
gotchas §4 — retry, then `v1_instagram_basic_profile` by `userId`, then record as
unavailable.

```bash
python3 scripts/enrich.py --cache-dir "$CACHE" --pool output/raw-pool.json \
  --out output/enriched.json \
  --min-followers 5000 --max-followers 500000 \
  --max-age-days 60 --limit 40
```

Computes both mean and median engagement, drops creators silent past
`--max-age-days`, applies the follower range, ranks by engagement rate, and writes
`output/run-meta.json` with everything dropped and why. Read its stdout — it
reports null-engagement creators and viral skew.

### 3 · Contact paths

Public sources only: the creator's own bio and their own link-in-bio page.

Bio emails are extracted automatically. Link-in-bio pages return **inline**, so
resolve them yourself and hand over the contact fields:

- `v1_linktree` (returns an `email_address` field), `v1_komi`, `v1_pillar`,
  `v1_linkbio`, `v1_linkme`
- regex the *whole* payload for emails — one run found an address in Linktree's
  `description` rather than `email_address` (gotchas §10)

Write `scratch/linkinbio.json` keyed by handle (schema in `scripts/contacts.py`), then:

```bash
python3 scripts/contacts.py --enriched output/enriched.json \
  --linkinbio scratch/linkinbio.json --cache-dir "$CACHE" --top 40
```

`--cache-dir` also picks each creator's own `external_url` out of the cached
profile, which is often the only contact path for accounts with no bio email.

Agency/management addresses get tagged automatically — flag them in your summary,
since the outreach differs.

### 4 · Dashboard

```bash
python3 scripts/build_dashboard.py --enriched output/enriched.json \
  --meta output/run-meta.json --out output/creator-pool.html \
  --title "Creator Pool" --platform instagram --niche "skincare" \
  --captured "13 Aug 2026"
```

Self-contained HTML, no network calls. Verify before publishing: open it with the
browser tools, exercise the filters against expected counts, check dark mode and
mobile overflow. Then publish with the **Artifact** tool.

To update an existing dashboard, republish the **same file path** so it keeps its URL.

## Reporting back

State plainly:

- how many were sourced, and how many survived each filter
- **who was dropped and why** — stale, out of range, or API-unavailable. A creator
  missing from a dashboard is indistinguishable from one never found.
- the mean/median split if any creator is viral-skewed, with the worst example
- which contacts are agency rather than personal
- credits spent

Do not present the pool as vetted for brand fit. Discovery matches captions as well
as bios, so brands and off-topic accounts will be in there; say so.

## Scope

This sources public professional data for partnership outreach. Keep to public
bios and creators' own link-in-bio pages. Don't compile personal information
beyond a business contact path, and don't send anything on the user's behalf
without explicit approval.
