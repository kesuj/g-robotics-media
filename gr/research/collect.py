"""Collects candidate stories from the feeds in config/sources.json into state/research/candidates.jsonl.

    python -m gr.research.collect [--max-age-days 7]

Each row: id (hash of url), title, url, source, tier, topics, published (ISO, UTC), collected, summary.
Collection only — scoring, verification and angle-writing happen in the editorial step, which must cite
tier-1/2 sources for any claim (tier 3 = discovery only).
"""
import datetime as dt
import hashlib
import json
import re
import sys

import feedparser

from gr.state import ROOT, STATE, audit

SEEN = STATE / "research" / "candidates.jsonl"
UA = "G-Robotics-research-bot/1.0 (+https://gnepal.org)"
# Stories about deaths, attacks, war or disasters are flagged and never auto-produced (human review only).
SENSITIVE_STEMS = ("kill", "death", "attack", "bomb", "militar", "weapon", "terror", "crash", "flood", "earthquake",
                   "disaster", "victim", "injur", "lawsuit", "scandal", "protest", "election", "mourn", "condolence",
                   "houthi", "missile")
SENSITIVE_WORDS = ("war", "wars", "dead", "died", "dies", "strike", "strikes")   # whole words only ("warehouse" is fine)
SENSITIVE = re.compile("(?<![a-z])(" + "|".join(SENSITIVE_STEMS) + ")[a-z]*|(?<![a-z])(" + "|".join(SENSITIVE_WORDS)
                       + ")(?![a-z])", re.I)
TAGS = re.compile("<[^>]+>")
SPACES = re.compile("[ \t\r\n]+")


def is_sensitive(text):
    return bool(SENSITIVE.search(text or ""))


def _when(entry):
    for k in ("published_parsed", "updated_parsed"):
        t = entry.get(k)
        if t:
            return dt.datetime(*t[:6], tzinfo=dt.timezone.utc)
    return None


def _clean(html):
    return SPACES.sub(" ", TAGS.sub(" ", html or "")).strip()[:600]


def main(max_age_days=7):
    feeds = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf8"))["feeds"]
    seen = set()
    if SEEN.exists():
        for line in SEEN.read_text(encoding="utf8").splitlines():
            try:
                seen.add(json.loads(line)["id"])
            except Exception:
                pass
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_age_days)
    new, errors = 0, []
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    with SEEN.open("a", encoding="utf8") as out:
        for f in feeds:
            d = feedparser.parse(f["url"], agent=UA)
            if d.get("bozo") and not d.entries:
                errors.append(f["name"])
                continue
            for e in d.entries[:40]:
                url = e.get("link")
                if not url:
                    continue
                cid = hashlib.sha1(url.encode()).hexdigest()[:16]
                when = _when(e)
                if cid in seen or (when and when < cutoff):
                    continue
                seen.add(cid)
                row = {"id": cid, "title": _clean(e.get("title")), "url": url, "source": f["name"], "tier": f["tier"],
                       "topics": f["topics"], "published": when.isoformat() if when else None,
                       "collected": dt.datetime.now(dt.timezone.utc).isoformat(), "summary": _clean(e.get("summary")),
                       "status": "new"}
                row["sensitive"] = is_sensitive(row["title"] + " " + row["summary"])
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                new += 1
    audit("research.collect", new=new, feed_errors=errors)
    print(f"collected {new} new candidates; feeds with errors: {errors or 'none'}")


if __name__ == "__main__":
    main(int(sys.argv[sys.argv.index("--max-age-days") + 1]) if "--max-age-days" in sys.argv else 7)
