"""Viral QA for a brief — rejects weak hooks and leaky retention before anything is rendered.

    python -m gr.qa.viral briefs/<file>.json [...]

Deterministic checks only (no model call). Two levels:
  every brief   hook lands fast (first sentence ≤ 12 words, hook VO ≤ 18), no throat-clearing opener, short on-screen
                hook, English only (no Devanagari), no generic sign-off as the only CTA.
  strict        (briefs with a "viral" block — every brief the editor writes now, see docs/prompts/editor.md):
                goal/emotion/angle, ≥ 2 distinct hook variants incl. the one used, self-scores ≥ 7 each and ≥ 8 average,
                an open loop paid off in the second half, re-hook lines actually spoken, cover text 2–5 words,
                one CTA with a reason, caption first line ≤ 125 chars.
"""
import json
import re
import sys

GOALS = {"save", "share", "follow", "comment"}
SCORES = ("scroll_stop", "curiosity", "clarity", "specificity", "audience_fit")
WEAK_OPENERS = re.compile(r"^\W*(today\b|in this (video|reel)|hi\b|hello\b|hey\b|welcome\b|namaste\b|let'?s (talk|learn|look)|"
                          r"so,|so today|did you know|have you ever wondered|this video|here is a video|ever wondered)", re.I)
GENERIC_CTA = {"follow for a daily dose of engineering.", "follow for tech and power news every day.",
               "follow for one license-exam concept every day.", "follow for more.", "like and subscribe."}
ASK = re.compile(r"\b(follow|save|share|send|comment|tag|bookmark)\b", re.I)
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def _sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def check(ep, strict=None):
    """Returns a list of problems (empty = pass). strict defaults to: the brief has a "viral" block."""
    errs = []
    e = errs.append
    beats = ep.get("beats") or []
    strict = bool(ep.get("viral")) if strict is None else strict
    if any(DEVANAGARI.search(s) for s in _strings({k: v for k, v in ep.items() if k != "sources"})):
        e("English only: Devanagari text found (VO, on-screen text and caption must be English)")
    if not beats or beats[0].get("type") != "hook":
        return errs + ["first beat must be the hook"]
    hook = beats[0]
    vo = hook.get("vo", "")
    first = (_sentences(vo) or [""])[0]
    if len(first.split()) > 12:
        e(f"hook: first sentence is {len(first.split())} words — the claim must land in ~1.5 s (≤ 12)")
    if len(vo.split()) > 18:
        e(f"hook vo is {len(vo.split())} words (≤ 18)")
    if WEAK_OPENERS.match(vo):
        e(f"hook opens with throat-clearing ({vo.split()[0]!r}…) — open on the claim, the result or the stakes")
    if len(str(hook.get("text", "")).split()) > 8:
        e("hook on-screen text > 8 words")
    out = beats[-1] if beats[-1].get("type") == "outro" else None
    if strict and out and out.get("vo", "").strip().lower() in GENERIC_CTA:
        e("outro is the generic sign-off — write one CTA with a reason (cta-writer)")
    if not strict:
        return errs

    v = ep.get("viral")
    if not isinstance(v, dict):
        return errs + ['"viral" block missing (docs/prompts/editor.md: goal, hook_variants, hook_scores, open_loop, cover_text, cta…)']
    if v.get("goal") not in GOALS:
        e(f"viral.goal must be one of {sorted(GOALS)}")
    for k in ("emotion", "angle", "open_loop"):
        if not str(v.get(k, "")).strip():
            e(f"viral.{k} missing")
    hv = v.get("hook_variants") or []
    vos = [str(h.get("vo", "")).strip().lower() for h in hv if isinstance(h, dict)]
    if len(set(vos)) < 2:
        e("viral.hook_variants: give at least 2 genuinely different hooks (ab-hook-tester)")
    if vo.strip().lower() not in vos:
        e("viral.hook_variants must include the hook actually used in beat 0")
    sc = v.get("hook_scores") or {}
    vals = [sc.get(k) for k in SCORES]
    if any(not isinstance(x, (int, float)) for x in vals):
        e(f"viral.hook_scores needs {', '.join(SCORES)} (1–10)")
    else:
        if min(vals) < 7 or sum(vals) / len(vals) < 8:
            e(f"hook too weak: scores {dict(zip(SCORES, vals))} (each ≥ 7, average ≥ 8) — rewrite it")
    pb = v.get("payoff_beat")
    if not isinstance(pb, int) or not 0 < pb < len(beats):
        e("viral.payoff_beat must be the index of the beat that pays off the open loop")
    elif pb < len(beats) // 2:
        e(f"payoff at beat {pb} of {len(beats)} — withhold it to the second half or viewers leave once the loop closes")
    spoken = " ".join(b.get("vo", "") for b in beats[1:]).lower()
    rh = v.get("rehooks") or []
    if len(beats) > 4 and not rh:
        e("viral.rehooks: add at least one spoken micro re-hook (\"but here's the part…\") for Reels over 4 beats")
    for r in rh:
        if str(r).strip().lower().rstrip(".!?…") not in spoken:
            e(f"re-hook {r!r} is not spoken in any beat vo")
    ct = str(v.get("cover_text", "")).split()
    if not 2 <= len(ct) <= 5 or len(v.get("cover_text", "")) > 30:
        e("viral.cover_text: 2–5 words, ≤ 30 characters (cover-thumbnail-brief)")
    cta = v.get("cta") or {}
    if cta.get("type") not in GOALS:
        e(f"viral.cta.type must be one of {sorted(GOALS)}")
    if out:
        ov = out.get("vo", "")
        if not ASK.search(ov) or len(ov.split()) > 24:
            e("outro vo must be ONE clear ask (follow / save / share / comment) with its reason, ≤ 24 words")
    cap = (ep.get("caption") or "").split("\n")[0]
    if len(cap) > 125:
        e("caption first line > 125 chars — it gets cut before 'more'")
    if len(str(v.get("first_comment", ""))) > 300:
        e("viral.first_comment > 300 chars")
    return errs


def main(paths):
    sys.stdout.reconfigure(encoding="utf-8")   # messages use ≤ / – on Windows consoles too
    bad = 0
    for p in paths:
        errs = check(json.loads(open(p, encoding="utf8").read()))
        print(("PASS " if not errs else "FAIL ") + p + ("" if not errs else ": " + "; ".join(errs)))
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
