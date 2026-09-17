#!/usr/bin/env python3
"""
Stage 2 — compute engagement metrics from cached profile responses.

    python3 enrich.py --cache-dir DIR --pool output/raw-pool.json \
        --out output/enriched.json \
        [--min-followers 5000] [--max-followers 500000] \
        [--max-age-days 60] [--limit 40]

The Instagram profile endpoint returns the last 12 posts inline, so one call per
creator covers both profile and posts. This script never calls the API — it only
parses what the agent already fetched.

Three data-quality rules are load-bearing here; see reference/gotchas.md:
  1. recency = max(taken_at_timestamp), NOT edges[0] — pinned posts sit out of order
  2. likes  = edge_liked_by.count, falling back to edge_media_preview_like.count;
              both can be null or -1 when the account hides like counts
  3. a 12-post MEAN is dominated by one viral reel — medians are computed too
"""
import argparse, collections, datetime, glob, json, os, sys


def median(xs):
    if not xs:
        return None
    s = sorted(xs)
    m = len(s) // 2
    return float(s[m]) if len(s) % 2 else (s[m - 1] + s[m]) / 2


def likes_of(node):
    """Returns (value, used_fallback). None when the account hides like counts."""
    a = (node.get("edge_liked_by") or {}).get("count")
    b = (node.get("edge_media_preview_like") or {}).get("count")
    if isinstance(a, int) and a >= 0:
        return a, False
    if isinstance(b, int) and b >= 0:
        return b, True
    return None, True


def newest_profiles(cache_dir):
    """username -> user object, from the most recent cached response per handle."""
    best = {}
    for path in glob.glob(os.path.join(cache_dir, "*instagram_profile*")):
        d = None
        try:
            with open(path) as fh:
                d = json.load(fh)
        except Exception:
            continue
        u = (d.get("data") or {}).get("user")
        if not u or not u.get("username"):
            continue
        if not (u.get("edge_owner_to_timeline_media") or {}).get("edges"):
            continue
        mt = os.path.getmtime(path)
        if u["username"] not in best or mt > best[u["username"]][0]:
            best[u["username"]] = (mt, u)
    return {k: v[1] for k, v in best.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-followers", type=int, default=0)
    ap.add_argument("--max-followers", type=int, default=10**12)
    ap.add_argument("--max-age-days", type=int, default=60)
    ap.add_argument("--limit", type=int, default=0, help="0 = keep all")
    ap.add_argument("--now", type=float, default=None, help="unix ts override")
    args = ap.parse_args()

    import time
    NOW = args.now or time.time()
    CUTOFF = NOW - args.max_age_days * 86400

    with open(args.pool) as fh:
        pool = {r["handle"]: r for r in json.load(fh)}
    profiles = newest_profiles(args.cache_dir)

    rows, no_data, stale, out_of_range = [], [], [], []

    for handle, base in pool.items():
        u = profiles.get(handle)
        if not u:
            no_data.append(handle)
            continue

        edges = u["edge_owner_to_timeline_media"]["edges"][:12]
        likes, comments, stamps, pinned, hidden = [], [], [], 0, 0
        for e in edges:
            n = e["node"]
            lv, fb = likes_of(n)
            if lv is not None:
                likes.append(lv)
                if fb:
                    hidden += 1
            c = (n.get("edge_media_to_comment") or {}).get("count")
            if isinstance(c, int) and c >= 0:
                comments.append(c)
            if n.get("taken_at_timestamp"):
                stamps.append(n["taken_at_timestamp"])
            if n.get("pinned_for_users"):
                pinned += 1

        followers = (u.get("edge_followed_by") or {}).get("count") or base.get("follower_count")
        if followers is None:
            no_data.append(handle)
            continue

        if not (args.min_followers <= followers <= args.max_followers):
            out_of_range.append((handle, followers))
            continue

        avg_l = round(sum(likes) / len(likes), 1) if likes else None
        avg_c = round(sum(comments) / len(comments), 1) if comments else None
        med_l, med_c = median(likes), median(comments)
        last_ts = max(stamps) if stamps else None   # rule 1

        er = round((avg_l + avg_c) / followers * 100, 3) if None not in (avg_l, avg_c) else None
        er_med = round((med_l + med_c) / followers * 100, 3) if None not in (med_l, med_c) else None
        skew = round(max(likes) / med_l, 1) if likes and med_l else None

        rec = {
            "handle": handle,
            "profile_url": base["profile_url"],
            # take the bio from the profile response: hashtag/reels discovery
            # carries followers but no bio, so the pool is only ~half populated
            "bio": u.get("biography") or base.get("bio"),
            "sources": base.get("sources", []),
            "follower_count": followers,
            "avg_likes": avg_l, "avg_comments": avg_c, "engagement_rate": er,
            "median_likes": med_l, "median_comments": med_c,
            "engagement_rate_median": er_med,
            "top_post_vs_median": skew,
            "last_post_date": datetime.datetime.utcfromtimestamp(last_ts).strftime("%Y-%m-%d") if last_ts else None,
            "days_since_last_post": int((NOW - last_ts) // 86400) if last_ts else None,
            "posts_analyzed": len(edges),
            "pinned_in_sample": pinned,
            "likes_hidden_posts": hidden,
        }

        if last_ts is None or last_ts < CUTOFF:
            stale.append((handle, rec["days_since_last_post"]))
            continue
        rows.append(rec)

    # rank by engagement rate, nulls last
    rows.sort(key=lambda r: (r["engagement_rate"] is None, -(r["engagement_rate"] or 0)))
    truncated = 0
    if args.limit and len(rows) > args.limit:
        truncated = len(rows) - args.limit
        rows = rows[:args.limit]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)

    meta = {
        "sourced": len(pool),
        "kept": len(rows),
        "stale": [list(x) for x in sorted(stale, key=lambda x: -(x[1] or 0))],
        "out_of_range": [list(x) for x in out_of_range],
        "unavailable": no_data,
        "truncated_by_limit": truncated,
        "max_age_days": args.max_age_days,
        "follower_range": [args.min_followers,
                           None if args.max_followers >= 10**12 else args.max_followers],
    }
    mpath = os.path.join(os.path.dirname(os.path.abspath(args.out)), "run-meta.json")
    with open(mpath, "w") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    cut = datetime.datetime.utcfromtimestamp(CUTOFF).strftime("%Y-%m-%d")
    print(f"sourced            : {len(pool)}")
    print(f"outside follower   : {len(out_of_range)}")
    print(f"stale (< {cut}) : {len(stale)}")
    for h, d in meta["stale"][:10]:
        print(f"    {h:<30} {d}d")
    print(f"no profile data    : {len(no_data)} -> {no_data}")
    print(f"truncated by limit : {truncated}")
    print(f"KEPT               : {len(rows)}")
    nulls = [r['handle'] for r in rows if r['engagement_rate'] is None]
    skewed = [r for r in rows if (r['top_post_vs_median'] or 0) >= 5]
    print(f"  null ER (likes hidden on all 12): {len(nulls)} -> {nulls}")
    print(f"  viral-skewed (top >=5x median)  : {len(skewed)}")
    if skewed:
        worst = max(skewed, key=lambda r: r['top_post_vs_median'])
        print(f"     worst: {worst['handle']} mean {worst['engagement_rate']}% "
              f"vs median {worst['engagement_rate_median']}% ({worst['top_post_vs_median']}x)")
    print(f"\nwrote {args.out} and {mpath}")


if __name__ == "__main__":
    sys.exit(main())
