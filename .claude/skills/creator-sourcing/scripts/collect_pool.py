#!/usr/bin/env python3
"""
Stage 1 — merge three-way search results into one deduped raw pool.

Scans the session tool-results cache for ScrapeCreators search responses that
spilled to disk, plus an optional JSON of results that came back inline, and
writes a deduped creator pool.

    python3 collect_pool.py --cache-dir DIR --out output/raw-pool.json \
        [--inline scratch/profile-search.json] [--reels-queries "q1,q2"]

--inline expects {"<query>": [{username,url,follower_count,biography}, ...], ...}
  (profile-search results are small and usually return inline, not to a file)

Reels responses do not echo their query, so they are labelled from
--reels-queries in call order. The script prints a keyword-overlap check per
reels file — VERIFY that before trusting the labels.
"""
import argparse, collections, glob, json, os, re, sys


def load(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return None


def add(pool, username, url, followers, bio, source):
    u = (username or "").strip().lstrip("@")
    if not u:
        return
    if u not in pool:
        pool[u] = {"handle": u,
                   "profile_url": url or f"https://www.instagram.com/{u}/",
                   "follower_count": followers, "bio": bio, "sources": []}
    r = pool[u]
    if not r["bio"] and bio:
        r["bio"] = bio
    if r["follower_count"] is None and followers is not None:
        r["follower_count"] = followers
    if source not in r["sources"]:
        r["sources"].append(source)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--inline")
    ap.add_argument("--reels-queries", default="")
    args = ap.parse_args()

    pool = collections.OrderedDict()

    # --- profile search (inline) ---
    if args.inline:
        data = load(args.inline) or {}
        for query, rows in data.items():
            for r in rows:
                add(pool, r.get("username"), r.get("url"), r.get("follower_count"),
                    r.get("biography") or r.get("bio"), f"profile_search:{query}")

    # --- profile search (spilled) ---
    for p in sorted(glob.glob(os.path.join(args.cache_dir, "*search_profiles*"))):
        d = load(p)
        if not d:
            continue
        q = d.get("query", "?")
        for r in d.get("profiles", []):
            add(pool, r.get("username"), r.get("url"), r.get("follower_count"),
                r.get("biography"), f"profile_search:{q}")

    # --- hashtag search ---
    for p in sorted(glob.glob(os.path.join(args.cache_dir, "*search_hashtag*"))):
        d = load(p)
        if not d:
            continue
        tag = d.get("hashtag", "?")
        for post in d.get("posts", []):
            o = post.get("owner") or {}
            add(pool, o.get("username"), None, o.get("follower_count"), None,
                f"hashtag:{tag}")

    # --- reels search (no query echoed — label by call order, then VERIFY) ---
    queries = [q.strip() for q in args.reels_queries.split(",") if q.strip()]
    reel_files = sorted(glob.glob(os.path.join(args.cache_dir, "*reels_search*")))
    sanity = {}
    for i, p in enumerate(reel_files):
        d = load(p)
        if not d:
            continue
        label = queries[i] if i < len(queries) else f"file{i+1}"
        reels = d.get("reels", [])
        blob = json.dumps(reels).lower()
        terms = [t for t in re.split(r"\W+", label.lower()) if len(t) > 3]
        sanity[label] = {t: blob.count(t) for t in terms} or {"(no long terms)": 0}
        for post in reels:
            o = post.get("owner") or {}
            add(pool, o.get("username"), None, o.get("follower_count"), None,
                f"reels:{label}")

    records = list(pool.values())
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)

    by = collections.Counter()
    for r in records:
        for s in r["sources"]:
            by[s.split(":")[0]] += 1
    multi = [r["handle"] for r in records if len({s.split(':')[0] for s in r["sources"]}) > 1]

    print(f"UNIQUE HANDLES : {len(records)}")
    for k, v in by.items():
        print(f"  via {k:<16}: {v}")
    print(f"  found 2+ ways   : {len(multi)} -> {multi}")
    print(f"  missing bio     : {len([r for r in records if not r['bio']])} "
          f"(hashtag/reels owners carry followers but no bio — enrich fills these)")
    if sanity:
        print("\nREELS LABEL CHECK — each query's own words should appear in its own file:")
        for label, counts in sanity.items():
            print(f"  {label!r}: {counts}")
        print("  If a query's words score 0 in its file, the order is wrong — fix --reels-queries.")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
