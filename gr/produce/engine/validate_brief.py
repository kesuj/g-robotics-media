"""Validates G. Robotics briefs: the engine's own schema checks plus the Instagram extras.

    python gr/produce/engine/validate_brief.py briefs/g20261027-01.json [...]

news/people/clip use validate_lanes.check; explain/mcq/eli5/myth/mistake use validate_v2.check_v2.
The engine validators expect YouTube-series ids (nNNN / epNNN); G. Robotics ids are gYYYYMMDD-NN, so those
id-format messages are ignored here.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_lanes  # noqa: E402
import validate_v2  # noqa: E402

LANES = {"news", "people", "clip"}
ID = re.compile(r"g\d{8}-\d{2}")


def check(path):
    ep = json.loads(open(path, encoding="utf8").read())
    fmt = ep.get("format", "explain")
    errs = validate_lanes.check(path) if fmt in LANES else (validate_v2.check_v2(path, ep.get("id")) or [])
    errs = [e for e in errs if "should be" not in e and "id " not in e[:4] and "filename" not in e]
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
    return errs


def main(paths):
    bad = 0
    for p in paths:
        errs = check(p)
        print(("PASS " if not errs else "FAIL ") + os.path.basename(p) + ("" if not errs else ": " + "; ".join(errs)))
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
