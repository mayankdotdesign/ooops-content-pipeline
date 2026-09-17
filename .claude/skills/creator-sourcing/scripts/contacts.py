#!/usr/bin/env python3
"""
Stage 3 — attach public contact paths to each creator.

    python3 contacts.py --enriched output/enriched.json \
        [--linkinbio scratch/linkinbio.json] [--top 40]

Bio emails are extracted automatically from the bio text already in enriched.json.
Link-in-bio pages (Linktree/Komi/Pillar/Linkbio/Linkme) return INLINE from the MCP
call, so they cannot be read off disk — the agent resolves them and hands the
contact-relevant fields to this script as --linkinbio:

{
  "<handle>": {"service":"linktree","resolved":true,"email":"a@b.com","links":14,
               "booking":"https://...","website":"https://...",
               "business_contact":"https://wa.me/...", "business_contact_label":"WhatsApp — partnerships"}
}

Only `service` and `resolved` are required; everything else may be null.
Writes the `contact` object back into enriched.json in place.
"""
import argparse, collections, json, os, re, sys

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Talent-management domains: the right contact for partnerships, but NOT the
# creator personally — the outreach you write differs, so flag them.
AGENCY_DOMAINS = {
    "select.co": "Select Mgmt",
    "thedigitaldept.com": "The Digital Dept",
    "outshinetalent.com": "Outshine Talent",
    "iala.com": "IALA",
    "wme.com": "WME", "caa.com": "CAA", "uta.com": "UTA",
    "digitalbrandarchitects.com": "DBA", "viralnation.com": "Viral Nation",
}
SOCIAL = ("instagram.com", "tiktok.com", "youtube.com", "facebook.com",
          "threads.net", "threads.com", "twitter.com", "x.com")
LIB_HOSTS = ("linktr.ee", "komi.io", "pillar.io", "linkbio.co", "linkme.bio")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enriched", required=True)
    ap.add_argument("--linkinbio")
    ap.add_argument("--cache-dir", help="pull external_url/bio_links from cached profiles")
    ap.add_argument("--top", type=int, default=0, help="0 = all creators")
    args = ap.parse_args()

    with open(args.enriched) as fh:
        rows = json.load(fh)
    lib = {}
    if args.linkinbio and os.path.exists(args.linkinbio):
        with open(args.linkinbio) as fh:
            lib = json.load(fh)

    # a creator's own external_url is a valid contact path when no email exists
    site_from_profile = {}
    if args.cache_dir:
        import glob
        for p in glob.glob(os.path.join(args.cache_dir, "*instagram_profile*")):
            try:
                with open(p) as fh:
                    u = (json.load(fh).get("data") or {}).get("user") or {}
            except Exception:
                continue
            if not u.get("username"):
                continue
            urls = [u.get("external_url")] + [b.get("url") for b in (u.get("bio_links") or [])]
            for url in urls:
                if not url:
                    continue
                low = url.lower()
                if any(h in low for h in LIB_HOSTS) or any(s in low for s in SOCIAL):
                    continue
                site_from_profile.setdefault(u["username"], url)
                break

    # scope: top N by engagement rate (rows arrive already ranked)
    scope = {r["handle"] for r in (rows[:args.top] if args.top else rows)}

    for r in rows:
        if r["handle"] not in scope:
            r["contact"] = None
            continue
        L = lib.get(r["handle"], {})
        emails = list(dict.fromkeys(
            EMAIL.findall(r.get("bio") or "") + ([L["email"]] if L.get("email") else [])))
        website = L.get("website") or site_from_profile.get(r["handle"])
        agency = [e for e in emails if e.split("@")[-1].lower() in AGENCY_DOMAINS]

        channels = []
        if emails:
            channels.append("email")
        if L.get("booking"):
            channels.append("booking")
        if L.get("business_contact"):
            channels.append("business")
        if website:
            channels.append("website")
        if L.get("service"):
            channels.append("linkinbio")

        r["contact"] = {
            "emails": emails,
            "agency_email": agency,
            "agency_names": [AGENCY_DOMAINS[e.split("@")[-1].lower()] for e in agency],
            "booking": L.get("booking"),
            "business_contact": L.get("business_contact"),
            "business_contact_label": L.get("business_contact_label"),
            "website": website,
            "linkinbio": ({"service": L["service"], "resolved": bool(L.get("resolved")),
                           "link_count": L.get("links")} if L.get("service") else None),
            "channels": channels,
            "best": ("email" if emails else "booking" if L.get("booking")
                     else "business" if L.get("business_contact")
                     else "website" if website
                     else "linkinbio" if L.get("service") else "none"),
        }

    with open(args.enriched, "w") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)

    scoped = [r for r in rows if r["contact"]]
    best = collections.Counter(r["contact"]["best"] for r in scoped)
    with_ag = [r for r in scoped if r["contact"]["agency_email"]]
    none = [r["handle"] for r in scoped if r["contact"]["best"] == "none"]
    print(f"in scope           : {len(scoped)} of {len(rows)}")
    print(f"best path          : {dict(best)}")
    print(f"direct email       : {len([r for r in scoped if r['contact']['emails']])}")
    print(f"  agency/management: {len(with_ag)} -> "
          f"{[(r['handle'], r['contact']['agency_names'][0]) for r in with_ag]}")
    print(f"link-in-bio resolved: {len([r for r in scoped if r['contact']['linkinbio']])}")
    print(f"no contact path    : {len(none)} -> {none}")
    print(f"\nupdated {args.enriched}")


if __name__ == "__main__":
    sys.exit(main())
