"""Validate a news-episode JSON (docs/NEWS-EPISODE-SCHEMA.md).   python -m gr.produce.newsroom.validate_news <file>..."""
import json
import re
import sys
from pathlib import Path

from gr.produce.newsroom.visuals import KITS


def problems(ep):
    out = []
    for k in ("id", "episode", "date", "title", "intro", "stories", "outro", "caption", "hashtags"):
        if k not in ep:
            out.append(f"missing {k}")
    if out:
        return out
    if not re.fullmatch(r"news-\d{8}", ep["id"]):
        out.append("id must be news-YYYYMMDD")
    if not isinstance(ep["episode"], int) or ep["episode"] < 1:
        out.append("episode must be a positive int")
    n = len(ep["stories"])
    if not 5 <= n <= 8:
        out.append(f"{n} stories (need 5–8)")
    if not sum(1 for s in ep["stories"] if s.get("region") == "NEPAL"):
        out.append("no NEPAL story")
    for i, s in enumerate(ep["stories"], 1):
        for k in ("tag", "region", "headline", "kit", "vo", "source", "urls"):
            if not s.get(k):
                out.append(f"story {i}: missing {k}")
        if s.get("region") not in ("NEPAL", "WORLD"):
            out.append(f"story {i}: region must be NEPAL or WORLD")
        if len(s.get("headline", "")) > 42:
            out.append(f"story {i}: headline > 42 chars")
        if s.get("kit") and s["kit"] not in KITS:
            out.append(f"story {i}: unknown kit {s['kit']}")
        wc = len(s.get("vo", "").split())
        if not 15 <= wc <= 45:
            out.append(f"story {i}: vo has {wc} words (aim 22–38)")
        if re.search(r"\d", s.get("vo", "")):
            out.append(f"story {i}: digits in vo — spell numbers out")
        st = s.get("stat")
        if st is not None and not isinstance(st.get("value"), (int, float)):
            out.append(f"story {i}: stat.value must be a number")
        if not all(str(u).startswith("http") for u in s.get("urls", [])):
            out.append(f"story {i}: urls must be links")
    for k in ("intro", "outro"):
        if re.search(r"\d", ep[k]):
            out.append(f"{k}: digits — spell numbers out")
    if len(ep["caption"]) > 900:
        out.append("caption > 900 chars")
    if "AI-generated" not in ep["caption"]:
        out.append("caption must say G. Dai is AI-generated")
    if not 4 <= len(ep["hashtags"]) <= 8:
        out.append("need 4–8 hashtags")
    texts = [ep["title"], ep["intro"], ep["outro"], ep["caption"], *map(str, ep["hashtags"])]
    texts += [str(s.get(k, "")) for s in ep["stories"] for k in ("tag", "headline", "vo")]
    if any(re.search(r"[ऀ-ॿ]", t) for t in texts):
        out.append("English only: Devanagari text found")
    if len(ep["caption"].split("\n")[0]) > 125:
        out.append("caption first line > 125 chars — it gets cut before 'more'")
    for i, s in enumerate(ep["stories"], 1):
        first = re.split(r"(?<=[.!?])\s+", s.get("vo", "").strip())[0]
        if len(first.split()) > 14:
            out.append(f"story {i}: opening sentence {len(first.split())} words — hook first, ≤ 14 words")
    return out


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        p = problems(json.loads(Path(f).read_text(encoding="utf8")))
        print(f, "OK" if not p else "FAIL\n  " + "\n  ".join(p))
        bad += bool(p)
    sys.exit(1 if bad else 0)
