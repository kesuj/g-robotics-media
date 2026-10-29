"""Validates G. Robotics briefs: the engine's own schema checks plus the Instagram extras.

    python gr/produce/engine/validate_brief.py briefs/g20261027-01.json [...]

news/people/clip use validate_lanes.check; explain/mcq/eli5/myth/mistake use validate_v2.check_v2.
The engine validators expect YouTube-series ids (nNNN / epNNN); G. Robotics ids are gYYYYMMDD-NN, so those
id-format messages are ignored here. The engine's fixed Daily-EE outro line is not required: G. Robotics outros carry a
CTA written per Reel. Every brief must also pass the viral QA (gr/qa/viral.py, strict: hook variants + scores, open
loop paid off late, re-hooks, cover text, one CTA, English only).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import validate_lanes  # noqa: E402
import validate_v2  # noqa: E402
from gr.qa import viral  # noqa: E402

LANES = {"news", "people", "clip"}
ID = re.compile(r"g\d{8}-\d{2}")


def check(path):
    ep = json.loads(open(path, encoding="utf8").read())
    fmt = ep.get("format", "explain")
    errs = validate_lanes.check(path) if fmt in LANES else (validate_v2.check_v2(path, ep.get("id")) or [])
    errs = [e for e in errs if "should be" not in e and "id " not in e[:4] and "filename" not in e and e != "outro"]
    if not ID.fullmatch(ep.get("id", "")):
        errs.append(f"id {ep.get('id')!r} should be gYYYYMMDD-NN")
    cap = ep.get("caption", "")
    if not cap or len(cap) > 600:
        errs.append("caption missing or over 600 chars")
    tags = ep.get("hashtags", [])
    if not (3 <= len(tags) <= 8):
        errs.append("hashtags: give 3–8")
    if not ep.get("sources") and fmt in LANES:
        errs.append("news/people briefs need sources")
    errs += viral.check(ep, strict=True)
    return errs


def main(paths):
    sys.stdout.reconfigure(encoding="utf-8")   # messages use ≤ / – on Windows consoles too
    bad = 0
    for p in paths:
        errs = check(p)
        print(("PASS " if not errs else "FAIL ") + os.path.basename(p) + ("" if not errs else ": " + "; ".join(errs)))
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
