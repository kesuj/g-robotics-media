"""Validator for lane episodes (lanes/news, lanes/people, lanes/clip) — see lanes/SCHEMA.md.

    python validate_lanes.py [files...]      (default: every lanes/*/*.json)
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = {
    "news": r"hook headline (stat )?concept (timeline )?tip outro",
    "people": r"hook profile (timeline )?(quote )?concept tip outro",
    "clip": r"hook (stat|concept) outro",
}
PREFIX = {"news": "n", "people": "p", "clip": "c"}
WORDS = {"news": (110, 170), "people": (110, 170), "clip": (40, 75)}
FIELDS = {"hook": {"text"}, "headline": {"text", "source", "date"}, "stat": {"number", "unit", "text"},
          "concept": {"text", "points"}, "timeline": {"events"}, "profile": {"name", "role", "icon", "known_for"},
          "quote": {"quote", "by"}, "tip": {"text"}, "outro": {"text"}}
LIMITS = {("hook", "text"): 8, ("headline", "text"): 12, ("stat", "unit"): 5, ("stat", "text"): 12, ("concept", "text"): 9,
          ("profile", "role"): 7, ("quote", "quote"): 22, ("tip", "text"): 14}
STYLES = {"classic", "blueprint", "neon", "notebook", "chalkboard", "sunset", "newsroom"}
W = lambda s: len(str(s).split())


def check(path):
    errs = []
    e = errs.append
    try:
        ep = json.load(open(path, encoding="utf8"))
    except Exception as x:
        return [f"bad JSON: {x}"]
    fmt = ep.get("format")
    if fmt not in RECIPES:
        return [f"format {fmt!r} not one of {list(RECIPES)}"]
    for k in ("id", "slug", "title", "category", "date", "description", "sources", "tags", "beats"):
        if not ep.get(k):
            e(f"missing {k}")
    name = os.path.basename(path)
    if not re.fullmatch(rf"{PREFIX[fmt]}\d{{3}}", ep.get("id", "")):
        e(f"id {ep.get('id')!r} should be {PREFIX[fmt]}NNN")
    if name != f"{ep.get('id')}-{ep.get('slug')}.json":
        e(f"filename should be {ep.get('id')}-{ep.get('slug')}.json")
    if len(ep.get("title", "")) > 60:
        e("title > 60 chars")
    if ep.get("style") and ep["style"] not in STYLES:
        e(f"unknown style {ep['style']}")
    srcs = ep.get("sources", [])
    if len(srcs) < (3 if fmt == "news" else 2) or not all(str(u).startswith("http") for u in srcs):
        e("not enough source URLs")
    beats = ep.get("beats", [])
    seq = " ".join(b.get("type", "?") for b in beats)
    if not re.fullmatch(RECIPES[fmt], seq):
        e(f"beat order '{seq}' doesn't match {RECIPES[fmt]}")
    total = 0
    for i, b in enumerate(beats):
        t = b.get("type")
        vo = b.get("vo", "")
        if not vo:
            e(f"beat {i} {t}: no vo")
        if re.search(r"\d", vo):
            e(f"beat {i} {t}: digits in vo")
        if re.search(r"[%$€£°Ω=+/<>&#@]", vo):
            e(f"beat {i} {t}: symbol in vo")
        total += W(vo)
        for f in FIELDS.get(t, set()) - set(b):
            e(f"beat {i} {t}: missing {f}")
        for (bt, f), n in LIMITS.items():
            if bt == t and W(b.get(f, "")) > n:
                e(f"beat {i} {t}.{f} > {n} words")
        if t == "stat" and not isinstance(b.get("number"), (int, float)):
            e(f"beat {i} stat.number must be a JSON number")
        if t == "concept" and not 2 <= len(b.get("points", [])) <= 3:
            e(f"beat {i} concept needs 2-3 points")
        if t == "timeline" and not 2 <= len(b.get("events", [])) <= 4:
            e(f"beat {i} timeline needs 2-4 events")
        if t == "profile" and len(b.get("icon", "")) > 3:
            e(f"beat {i} profile.icon must be one emoji")
        if t == "outro" and b.get("text") != "Daily EE":
            e("outro text must be 'Daily EE'")
    lo, hi = WORDS[fmt]
    if not lo <= total <= hi:
        e(f"total vo words {total} outside {lo}-{hi}")
    return errs


def main(paths):
    paths = paths or sorted(glob.glob(os.path.join(ROOT, "lanes", "*", "*.json")))
    bad = 0
    for p in paths:
        errs = check(p)
        if errs:
            bad += 1
            print(f"FAIL {os.path.basename(p)}")
            for x in errs:
                print("   -", x)
    print(f"{len(paths) - bad}/{len(paths)} lane episodes OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
