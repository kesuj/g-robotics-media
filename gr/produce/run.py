"""Render every new brief in briefs/, QA it, host it, and put it in the queue as qa_passed.

    python -m gr.produce.run [--limit 4]

A brief = an episode JSON in the engine schema (docs/EPISODE-SCHEMA.md) plus "caption", "hashtags" and "viral".
Briefs that fail the viral QA (gr/qa/viral.py: weak hook / retention) are failed before rendering — no retries, the
editor must rewrite them. Failed renders/QA are retried up to 2 times, then moved to failed (never published).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from gr.qa import viral
from gr.qa.check import check_caption, check_video
from gr.state import ROOT, audit, now, queue, set_status

ENGINE = ROOT / "gr" / "produce" / "engine"
WORK = Path(os.environ.get("GR_WORK", ROOT / "work"))
RENDERS = ROOT / "renders"
COVER_OFFSET_MS = 900     # engine Reels: frame 0 is the cover text; by 0.9 s the punch-in has settled


def caption_text(ep):
    tags = " ".join("#" + t.lstrip("#").replace(" ", "") for t in ep.get("hashtags", [])[:8])
    body = ep.get("caption") or ep["title"]
    src = ep.get("sources") or []
    credit = ("\n\nSources: " + ", ".join(sorted({s.split("/")[2].replace("www.", "") for s in src if "://" in s}))) if src else ""
    return f"{body}{credit}\n\n{tags}".strip()


def render(brief):
    r = subprocess.run([sys.executable, str(ENGINE / "build.py"), str(brief)], cwd=ENGINE, capture_output=True, text=True,
                       env=dict(os.environ, GR_WORK=str(WORK)))
    if r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr)[-1500:])
    ep = json.loads(Path(brief).read_text(encoding="utf8"))
    outs = sorted((WORK / "out").glob(f"{ep['id']}-*.mp4"), key=lambda p: p.stat().st_mtime)
    if not outs:
        raise RuntimeError("render produced no mp4")
    return outs[-1]


def render_news(brief):
    """Tech News with G. Dai episodes use the newsroom template (gr/produce/newsroom)."""
    r = subprocess.run([sys.executable, "-m", "gr.produce.newsroom.build_news", str(brief)], cwd=ROOT, capture_output=True,
                       text=True, env=dict(os.environ, GR_WORK=str(WORK)))
    if r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr)[-1500:])
    ep = json.loads(Path(brief).read_text(encoding="utf8"))
    mp4 = WORK / "out" / f"{ep['id']}.mp4"
    if not mp4.exists():
        raise RuntimeError("news render produced no mp4")
    return mp4


def normalize(src, dest, target=-14.0):
    """Loudness-normalise to Instagram-friendly -14 LUFS / -1.5 dBTP (two-pass loudnorm), video copied untouched."""
    probe = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-i", str(src), "-af",
                            f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    af = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "copy", "-af", af,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(dest)], check=True)


def main(limit=4):
    RENDERS.mkdir(exist_ok=True)
    made = 0
    with queue() as q:
        news = sorted((ROOT / "briefs" / "news").glob("news-*.json"), reverse=True)[:2]   # newest episodes first
        for brief in news + sorted((ROOT / "briefs").glob("*.json")):
            if made >= limit:
                break
            ep = json.loads(brief.read_text(encoding="utf8"))
            iid = ep["id"]
            it = q["items"].get(iid)
            if it and it["status"] not in ("briefed",):
                continue
            if not it:
                is_news = brief.parent.name == "news"
                q["items"][iid] = it = {"id": iid, "title": ep["title"], "kind": "news" if is_news else ep.get("format", "explain"),
                                        "brief": brief.relative_to(ROOT).as_posix(), "created": now().isoformat(), "news_date": ep.get("date"),
                                        "status": "briefed", "retries": 0, "format": "gdai_news" if is_news else ep.get("format"),
                                        "style": ep.get("style"), "series": "Tech News with G. Dai" if is_news else ep.get("series")}
                if is_news:   # hold for the evening news slot (18:00 NPT); priority over everything else that day
                    it["not_before"] = f"{ep['date']}T17:30:00+05:45"
                    it["priority"] = 1
                set_status(q, iid, "briefed")
            if it.get("kind") != "news":
                weak = viral.check(ep)
                if weak:
                    set_status(q, iid, "failed", note="viral QA: " + "; ".join(weak)[:380])
                    continue
            try:
                mp4 = render_news(brief) if it.get("kind") == "news" else render(brief)
                dest = RENDERS / f"{iid}.mp4"
                normalize(mp4, dest)
                set_status(q, iid, "rendered", video_file=dest.relative_to(ROOT).as_posix())
                cap = caption_text(ep)
                cap_file = ROOT / "state" / "captions" / f"{iid}.txt"   # committed, so the publish job has it
                cap_file.parent.mkdir(parents=True, exist_ok=True)
                cap_file.write_text(cap, encoding="utf8")
                ok, problems, facts = check_video(dest)
                cok, cprob = check_caption(cap)
                if not (ok and cok):
                    raise RuntimeError("QA: " + "; ".join(problems + cprob))
                url = None
                if os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY"):
                    from gr.publish import hosting     # cloud: keep the file in the release so later jobs can fetch it
                    url = hosting.upload(dest, f"{iid}.mp4")
                extra = {"cover_offset_ms": COVER_OFFSET_MS} if it.get("kind") != "news" else {}
                set_status(q, iid, "qa_passed", caption_file=cap_file.relative_to(ROOT).as_posix(), qa=facts, video_url=url, **extra)
                made += 1
            except Exception as e:  # noqa: BLE001 — any failure keeps the item out of the publish queue
                it["retries"] = it.get("retries", 0) + 1
                set_status(q, iid, "failed" if it["retries"] >= 3 else "briefed", note=str(e)[:400])
    audit("produce.run", made=made)
    print(f"produced {made} Reel(s)")


if __name__ == "__main__":
    main(int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 4)
