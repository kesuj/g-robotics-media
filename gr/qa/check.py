"""Automated pre-publication QA for a rendered Reel. Returns (ok, problems, facts).

    python -m gr.qa.check <video.mp4> [--caption caption.txt]

Technical checks: container/codec/size/fps/duration/audio, blank or frozen opening, silence, loudness,
file size. Caption checks: length and hashtag count. Limits live in config/platform.json so they can be
updated when Instagram changes its specs (verify against current docs; don't hard-code assumptions here).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIMITS = json.loads((ROOT / "config" / "platform.json").read_text(encoding="utf8"))["instagram_reels"]


def _ff(name):
    return shutil.which(name) or name


def probe(path):
    out = subprocess.run([_ff("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _filter_log(path, vf=None, af=None, seconds=None):
    cmd = [_ff("ffmpeg"), "-hide_banner", "-nostats"]
    if seconds:
        cmd += ["-t", str(seconds)]
    cmd += ["-i", str(path)]
    if vf:
        cmd += ["-vf", vf, "-an"]
    if af:
        cmd += ["-af", af, "-vn"]
    cmd += ["-f", "null", "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stderr


def check_video(path):
    problems, facts = [], {}
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return False, ["file missing or empty"], facts
    try:
        info = probe(path)
    except subprocess.CalledProcessError:
        return False, ["ffprobe could not read the file (corrupt or incomplete)"], facts
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0))
    size_mb = path.stat().st_size / 1e6
    facts.update(duration=round(dur, 2), size_mb=round(size_mb, 1))
    if not v:
        return False, ["no video stream"], facts
    w, h = int(v["width"]), int(v["height"])
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den or 1)
    facts.update(width=w, height=h, fps=round(fps, 2), vcodec=v["codec_name"], acodec=a["codec_name"] if a else None)
    L = LIMITS
    if (w, h) != tuple(L["resolution"]):
        problems.append(f"resolution {w}x{h}, expected {L['resolution'][0]}x{L['resolution'][1]}")
    if v["codec_name"] not in L["video_codecs"]:
        problems.append(f"video codec {v['codec_name']} not in {L['video_codecs']}")
    if v.get("pix_fmt") not in L["pix_fmts"]:
        problems.append(f"pixel format {v.get('pix_fmt')} not in {L['pix_fmts']}")
    if not (L["fps_min"] <= fps <= L["fps_max"]):
        problems.append(f"fps {fps:.2f} outside {L['fps_min']}–{L['fps_max']}")
    if not (L["duration_min_s"] <= dur <= L["duration_max_s"]):
        problems.append(f"duration {dur:.1f}s outside {L['duration_min_s']}–{L['duration_max_s']}s")
    if size_mb > L["max_size_mb"]:
        problems.append(f"file {size_mb:.0f} MB over {L['max_size_mb']} MB")
    if v.get("color_transfer") in ("arib-std-b67", "smpte2084"):
        problems.append(f"HDR transfer {v['color_transfer']} — render SDR")
    if not a:
        problems.append("no audio stream")
    elif a["codec_name"] not in L["audio_codecs"]:
        problems.append(f"audio codec {a['codec_name']} not in {L['audio_codecs']}")

    # opening must not be black or frozen (thumbnail + hook)
    log = _filter_log(path, vf="blackdetect=d=0.3:pix_th=0.08", seconds=3)
    if re.search(r"black_start:0(\.0+)?\b", log):
        problems.append("opens on black")
    log = _filter_log(path, vf="freezedetect=n=0.002:d=1.5", seconds=3)
    if "freeze_start: 0" in log:
        problems.append("opening frame frozen for 1.5 s+")
    # long silence anywhere (narrated Reels should not go quiet for > 2.5 s)
    if a:
        log = _filter_log(path, af=f"silencedetect=n=-45dB:d={L['max_silence_s']}")
        sil = re.findall(r"silence_duration: ([\d.]+)", log)
        if sil:
            problems.append(f"{len(sil)} silent gap(s) over {L['max_silence_s']} s")
        log = _filter_log(path, af="ebur128=peak=true")
        m = list(re.finditer(r"I:\s+(-?[\d.]+) LUFS", log))
        m = m[-1] if m else None   # the Summary block at the end, not a momentary reading
        pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", log)
        if m:
            lufs = float(m.group(1))
            facts["lufs"] = lufs
            if not (L["lufs_min"] <= lufs <= L["lufs_max"]):
                problems.append(f"loudness {lufs} LUFS outside {L['lufs_min']}…{L['lufs_max']}")
        if pk and float(pk[-1]) > -0.5:
            problems.append(f"true peak {pk[-1]} dBFS (clipping risk)")
    return not problems, problems, facts


def check_caption(text):
    problems = []
    L = LIMITS
    if len(text) > L["caption_max_chars"]:
        problems.append(f"caption {len(text)} chars over {L['caption_max_chars']}")
    tags = re.findall(r"#\w+", text)
    if len(tags) > L["hashtags_max"]:
        problems.append(f"{len(tags)} hashtags over {L['hashtags_max']}")
    if re.search(r"(sk-|ghp_|EAA[A-Za-z0-9]{20}|IGQ[A-Za-z0-9]{20})", text):
        problems.append("caption looks like it contains a token")
    return not problems, problems


if __name__ == "__main__":
    ok, probs, facts = check_video(sys.argv[1])
    if "--caption" in sys.argv:
        cok, cp = check_caption(Path(sys.argv[sys.argv.index("--caption") + 1]).read_text(encoding="utf8"))
        ok, probs = ok and cok, probs + cp
    print(json.dumps({"ok": ok, "problems": probs, "facts": facts}, indent=1))
    sys.exit(0 if ok else 1)
