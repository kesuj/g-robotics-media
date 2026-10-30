"""Tech News with G. Dai — one news-episode JSON → premium vertical Reel (HyperFrames).

    python -m gr.produce.newsroom.build_news <episode.json> [--no-render]

Episode fields: id, episode (int), date (YYYY-MM-DD), intro (VO), stories [{tag, region NEPAL|WORLD, headline, kit,
vo, source, stat?: {value, prefix?, suffix?, label}}], outro (VO). See docs/NEWS-EPISODE-SCHEMA.md.
Voice: edge-tts en-US-AndrewMultilingualNeural (natural male). GDAI_CLONE=1 uses the OmniVoice clone of assets/voice/gdai_ref.wav
(subprocess in OMNIVOICE_PYTHON) instead, falling back to edge-tts.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from gr.produce.newsroom import gdai, music, visuals

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
WORK = Path(os.environ.get("GR_WORK", REPO / "work")).resolve()
HF = "hyperframes@0.8.198"
W, H = 1080, 1920
GAP_AFTER = 0.55          # air after each segment's voice
LEAD = 0.5                # silence before the intro line
esc = html.escape
FF = shutil.which("ffmpeg") or "ffmpeg"
FP = shutil.which("ffprobe") or "ffprobe"

PALETTE = {"bg0": "#05070f", "bg1": "#0b1430", "ink": "#eef3fb", "mute": "#94a3b8", "c1": "#22d3ee", "c2": "#a78bfa",
           "gold": "#f5c451", "red": "#ff3b5c", "glass": "rgba(17,27,56,0.62)"}


def run(cmd, cwd=None, env=None):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, check=True, shell=(os.name == "nt" and str(cmd[0]) in ("npx", "node")))


def dur(path):
    return float(subprocess.run([FP, "-v", "0", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout.strip())


def ordinal_words(n):
    return {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth",
            10: "tenth"}.get(n, f"number {n}")


# ---------------------------------------------------------------- voice

def make_voice(ep, proj):
    vo = proj / "assets/vo"
    vo.mkdir(parents=True, exist_ok=True)
    segs = [("intro", ep["intro"])] + [(f"s{i}", s["vo"]) for i, s in enumerate(ep["stories"])] + [("outro", ep["outro"])]
    job = {"ref_wav": str(REPO / "assets/voice/gdai_ref.wav"),
           "ref_text": (REPO / "assets/voice/gdai_ref.txt").read_text(encoding="utf8").strip(),
           "segments": [{"id": k, "text": t, "out": str(vo / f"{k}.wav")} for k, t in segs],
           "words_out": str(vo / "words.json")}
    (vo / "job.json").write_text(json.dumps(job, indent=1), encoding="utf8")
    py = os.environ.get("OMNIVOICE_PYTHON")
    if not py:
        cand = Path(os.environ.get("APPDATA", "")) / "VoiceStudio/runtime/project/.venv/Scripts/python.exe"
        py = str(cand) if cand.exists() else sys.executable
    if os.environ.get("GDAI_FAKE") and not (vo / "words.json").exists():   # layout drafts: silence at speaking pace
        fake = {}
        for k, t in segs:
            ws = t.split()
            fake[k] = [{"w": w, "s": round(0.36 * i, 3), "e": round(0.36 * i + 0.3, 3)} for i, w in enumerate(ws)]
            run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{0.36 * len(ws) + 0.2:.2f}", vo / f"{k}.wav"])
        (vo / "words.json").write_text(json.dumps(fake), encoding="utf8")
    if not (vo / "words.json").exists() and not os.environ.get("GDAI_CLONE"):
        edge_fallback(segs, vo)
    if not (vo / "words.json").exists():
        try:
            run([py, HERE / "voice.py", vo / "job.json"])
        except subprocess.CalledProcessError:
            edge_fallback(segs, vo)
    words = json.loads((vo / "words.json").read_text(encoding="utf8"))
    out = []
    for k, _ in segs:
        wav = vo / f"{k}.wav"
        mp3 = vo / f"{k}.mp3"
        if not mp3.exists():   # gentle broadcast polish: high-pass, presence, compression, −16 LUFS per segment
            run([FF, "-v", "error", "-y", "-i", wav, "-af",
                 "highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,acompressor=threshold=-20dB:ratio=3:attack=8:release=120,"
                 "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "44100", "-b:a", "192k", mp3])
        out.append({"id": k, "file": f"assets/vo/{k}.mp3", "dur": dur(mp3), "words": words[k]})
    return out


def edge_fallback(segs, vo):
    """OmniVoice failed: speak G. Dai's lines with Microsoft's natural male neural voice (edge-tts, free),
    keeping the same files (segment wav + words.json) so the rest of the build is unchanged."""
    edge = REPO / "gr/produce/engine/vo_edge.py"
    jobs = [{"text": t, "mp3": str(vo / f"{k}.edge.mp3"), "words": str(vo / f"{k}.edge.json"),
             "voice": os.environ.get("GDAI_EDGE_VOICE", "en-US-AndrewMultilingualNeural")} for k, t in segs]
    (vo / "edge-jobs.json").write_text(json.dumps(jobs, indent=1), encoding="utf8")
    run([os.environ.get("EDGE_PYTHON", sys.executable), edge, vo / "edge-jobs.json"])
    words = {}
    for (k, _), j in zip(segs, jobs):
        run([FF, "-v", "error", "-y", "-i", j["mp3"], "-ar", "24000", "-ac", "1", vo / f"{k}.wav"])
        words[k] = json.loads(Path(j["words"]).read_text(encoding="utf8"))
    (vo / "words.json").write_text(json.dumps(words, indent=1), encoding="utf8")
    print("voice: edge fallback", jobs[0]["voice"], flush=True)


# ---------------------------------------------------------------- pieces

def chunks(words, max_words=4):
    cur, outs = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.,!?;:]$", w["w"]):
            outs.append(cur)
            cur = []
    if cur:
        outs.append(cur)
    return outs


def captions_html(segments, starts):
    divs, js = [], []
    n = 0
    for seg, st in zip(segments, starts):
        cs = chunks(seg["words"])
        for ci, ch in enumerate(cs):
            s = st + ch[0]["s"]
            e = st + (cs[ci + 1][0]["s"] if ci + 1 < len(cs) else ch[-1]["e"] + 0.35)
            spans = "".join(f'<span id="cw{n}-{k}">{esc(w["w"])}</span> ' for k, w in enumerate(ch))
            divs.append(f'<div id="cap{n}" class="clip cap" data-start="{s:.3f}" data-duration="{max(0.2, e - s):.3f}" data-track-index="9"><p>{spans}</p></div>')
            js.append(f'tl.from("#cap{n} p", {{ y: 18, opacity: 0, duration: 0.16, ease: "power2.out" }}, {s:.3f});')
            for k, w in enumerate(ch):
                js.append(f'tl.set("#cw{n}-{k}", {{ color: "{PALETTE["gold"]}" }}, {st + w["s"]:.3f});')
            n += 1
    return "\n".join(divs), "\n".join(js)


def intro_html(ep, s, d):
    date = dt.date.fromisoformat(ep["date"]).strftime("%d %b %Y").upper()
    rows = "".join(f'<div class="ro" id="ro{i}"><b>{i + 1:02d}</b><span>{esc(st["headline"])}</span><i class="{st["region"].lower()}">{esc(st["region"])}</i></div>'
                   for i, st in enumerate(ep["stories"]))
    body = f'''<div id="intro" class="clip scene" data-start="{s:.3f}" data-duration="{d:.3f}" data-track-index="4">
  <div id="in-kicker">G. ROBOTICS PRESENTS</div>
  <div id="in-title"><span>TECH</span><span>NEWS</span></div>
  <div id="in-with">with <b>G. Dai</b></div>
  <div id="in-meta">EPISODE {ep["episode"]:02d} · {date}</div>
  <div id="in-rundown"><div id="in-rh">TODAY'S TOP {len(ep["stories"])}</div>{rows}</div>
</div>'''
    js = [f'tl.from("#in-kicker", {{ opacity: 0, x: -50, duration: 0.7, ease: "power3.out" }}, {s + 0.1:.2f});',
          f'tl.from("#in-title span", {{ yPercent: 110, opacity: 0, duration: 0.7, stagger: 0.12, ease: "expo.out" }}, {s + 0.2:.2f});',
          f'tl.from("#in-with", {{ opacity: 0, x: -40, duration: 0.5, ease: "power3.out" }}, {s + 0.6:.2f});',
          f'tl.from("#in-meta", {{ opacity: 0, duration: 0.5 }}, {s + 0.8:.2f});',
          f'tl.to("#in-kicker", {{ opacity: 0, duration: 0.3 }}, {s + 2.2:.2f});',
          f'tl.to("#in-title, #in-with", {{ y: -60, scale: 0.8, transformOrigin: "0% 0%", duration: 0.6, ease: "power3.inOut" }}, {s + 2.3:.2f});',
          f'tl.to("#in-meta", {{ opacity: 0, duration: 0.3 }}, {s + 2.3:.2f});',
          f'tl.from("#in-rh", {{ opacity: 0, x: -30, duration: 0.4 }}, {s + 2.5:.2f});',
          f'tl.from(".ro", {{ x: -80, opacity: 0, duration: 0.45, stagger: {min(0.35, (d - 3.2) / max(1, len(ep["stories"]))):.2f}, ease: "power3.out" }}, {s + 2.7:.2f});']
    return body, js


def story_html(i, st, n_total, s, d):
    p = f"k{i}"
    svg, kjs = visuals.kit(st.get("kit", "globe"), p, s, d)
    stat = st.get("stat")
    stat_html, stat_js = "", []
    if stat:
        val = stat["value"]
        dec = 0 if float(val) == int(float(val)) else 1
        stat_html = (f'<div class="stat" id="st{i}"><div class="sv"><small>{esc(stat.get("prefix", ""))}</small><span id="sn{i}">0</span>'
                     f'<small>{esc(stat.get("suffix", ""))}</small></div><div class="sl">{esc(stat.get("label", ""))}</div></div>')
        stat_js = [f'tl.from("#st{i}", {{ y: 40, opacity: 0, duration: 0.5, ease: "power3.out" }}, {s + 1.2:.2f});',
                   f'(() => {{ const o = {{ v: 0 }}; tl.to(o, {{ v: {float(val)}, duration: 1.4, ease: "power2.out", onUpdate: () => {{ document.getElementById("sn{i}").textContent = o.v.toLocaleString("en-US", {{ minimumFractionDigits: {dec}, maximumFractionDigits: {dec} }}); }} }}, {s + 1.3:.2f}); }})();']
    region = st.get("region", "WORLD").upper()
    body = f'''<div id="story{i}" class="clip scene" data-start="{s:.3f}" data-duration="{d:.3f}" data-track-index="4">
  <div class="snum" id="sn-big{i}">{i + 1:02d}<em>/{n_total:02d}</em></div>
  <div class="tagrow" id="tr{i}"><span class="region {region.lower()}">{esc(region)}</span><span class="tag">{esc(st["tag"].upper())}</span></div>
  <h1 class="hl" id="hl{i}">{esc(st["headline"])}</h1>
  <div class="panel" id="pn{i}">{svg}<div class="sweep" id="sw{i}"></div>{stat_html}</div>
  <div class="src" id="src{i}">SOURCE · {esc(st.get("source", "").upper())}</div>
</div>'''
    js = [f'tl.from("#sn-big{i}", {{ x: -60, opacity: 0, duration: 0.5, ease: "expo.out" }}, {s + 0.05:.2f});',
          f'tl.from("#tr{i} span", {{ y: 20, opacity: 0, duration: 0.35, stagger: 0.08, ease: "power3.out" }}, {s + 0.12:.2f});',
          f'tl.from("#hl{i}", {{ y: 50, opacity: 0, clipPath: "inset(0 0 100% 0)", duration: 0.6, ease: "expo.out" }}, {s + 0.2:.2f});',
          f'tl.from("#pn{i}", {{ y: 60, opacity: 0, scale: 0.96, duration: 0.6, ease: "expo.out" }}, {s + 0.3:.2f});',
          f'tl.fromTo("#sw{i}", {{ xPercent: -120 }}, {{ xPercent: 220, duration: 1.1, ease: "power2.inOut" }}, {s + 0.45:.2f});',
          f'tl.from("#src{i}", {{ opacity: 0, duration: 0.4 }}, {s + 0.9:.2f});',
          f'tl.to("#pn{i}", {{ y: -10, duration: {max(1.0, d - 1.5):.2f}, ease: "sine.inOut" }}, {s + 1.0:.2f});',
          f'tl.set("#seg{i} i", {{ scaleX: 0 }}, 0);',
          f'tl.to("#seg{i} i", {{ scaleX: 1, duration: {d:.2f}, ease: "none" }}, {s:.2f});']
    return body, js + stat_js + kjs


def outro_html(ep, s, d):
    body = f'''<div id="outro" class="clip scene" data-start="{s:.3f}" data-duration="{d:.3f}" data-track-index="4">
  <div id="ou-k">THAT'S THE BRIEF</div>
  <div id="ou-t">See you tomorrow<br/>with more tech news.</div>
  <div id="ou-btn"><span>FOLLOW</span> @grobotics071</div>
  <div id="ou-s">Save · Share with a friend who loves tech</div>
</div>'''
    js = [f'tl.from("#ou-k", {{ opacity: 0, x: -50, duration: 0.6 }}, {s + 0.1:.2f});',
          f'tl.from("#ou-t", {{ y: 40, opacity: 0, duration: 0.6, ease: "expo.out" }}, {s + 0.25:.2f});',
          f'tl.from("#ou-btn", {{ scale: 0.6, opacity: 0, duration: 0.5, ease: "back.out(2)" }}, {s + 0.6:.2f});',
          f'tl.to("#ou-btn", {{ scale: 1.06, duration: 0.45, yoyo: true, repeat: {max(1, int((d - 1.2) / 0.45))}, ease: "sine.inOut" }}, {s + 1.2:.2f});',
          f'tl.from("#ou-s", {{ opacity: 0, duration: 0.5 }}, {s + 1.0:.2f});']
    return body, js


CSS = '''@font-face { font-family: "Outfit"; font-weight: 600; src: url("assets/fonts/outfit-latin-600-normal.woff2") format("woff2"); }
@font-face { font-family: "Outfit"; font-weight: 800; src: url("assets/fonts/outfit-latin-800-normal.woff2") format("woff2"); }
@font-face { font-family: "Outfit"; font-weight: 900; src: url("assets/fonts/outfit-latin-900-normal.woff2") format("woff2"); }
@font-face { font-family: "Space Mono"; font-weight: 700; src: url("assets/fonts/space-mono-latin-700-normal.woff2") format("woff2"); }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1080px; height: 1920px; overflow: hidden; background: {bg0}; }
#root { position: relative; width: 100%; height: 100%; font-family: Inter, sans-serif; color: {ink}; overflow: hidden; }
#bg { position: absolute; inset: 0; background: radial-gradient(1200px 900px at 20% 10%, #13235a 0%, transparent 60%),
      radial-gradient(1000px 900px at 90% 70%, #2a1452 0%, transparent 60%), linear-gradient(180deg, {bg1}, {bg0}); }
#grid { position: absolute; inset: -200px; background-image: linear-gradient(rgba(34,211,238,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(34,211,238,0.07) 1px, transparent 1px); background-size: 60px 60px; }
.orb { position: absolute; width: 700px; height: 700px; border-radius: 50%; filter: blur(80px); opacity: 0.35; }
#orb1 { left: -200px; top: 300px; background: #0e7490; } #orb2 { right: -260px; top: 900px; background: #6d28d9; }
#hdr { position: absolute; left: 48px; right: 48px; top: 56px; height: 92px; display: flex; align-items: center; gap: 18px; }
#logo { width: 84px; height: 84px; border-radius: 22px; background: linear-gradient(135deg, {gold}, #e59e1c); color: #101a33;
        font: 900 46px Outfit; display: grid; place-items: center; box-shadow: 0 10px 40px rgba(245,196,81,0.35); }
#brand { display: flex; flex-direction: column; gap: 4px; }
#brand b { font: 800 34px Outfit; letter-spacing: 0.06em; }
#brand span { font: 700 20px "Space Mono"; color: {c1}; letter-spacing: 0.22em; }
#hdr-r { margin-left: auto; text-align: right; font: 700 22px "Space Mono"; color: {mute}; line-height: 1.35; }
#hdr-r b { color: {ink}; }
#segs { position: absolute; left: 48px; right: 48px; top: 166px; display: flex; gap: 10px; }
#segs div { flex: 1; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.14); overflow: hidden; }
#segs i { display: block; height: 100%; background: linear-gradient(90deg, {c1}, {c2}); transform-origin: 0 50%; }
#tick { position: absolute; left: 0; right: 0; top: 196px; height: 58px; background: rgba(5,9,22,0.75); border-top: 1px solid rgba(34,211,238,0.25);
        border-bottom: 1px solid rgba(34,211,238,0.25); overflow: hidden; }
#tick-l { position: absolute; left: 0; top: 0; bottom: 0; width: 170px; background: {red}; z-index: 2; display: grid; place-items: center;
          font: 800 24px Outfit; letter-spacing: 0.14em; color: #fff; }
#tick-t { position: absolute; left: 190px; top: 12px; white-space: nowrap; font: 600 26px Inter; color: {ink}; }
#tick-t b { color: {gold}; margin: 0 22px; }
.scene { position: absolute; inset: 0; }
.snum { position: absolute; left: 56px; top: 292px; font: 900 120px Outfit; line-height: 1; background: linear-gradient(180deg, {c1}, {c2}); -webkit-background-clip: text; background-clip: text; color: transparent; }
.snum em { font-style: normal; font-size: 40px; color: {mute}; -webkit-text-fill-color: {mute}; margin-left: 10px; }
.tagrow { position: absolute; left: 300px; top: 318px; display: flex; gap: 12px; }
.tagrow span { font: 800 24px Outfit; letter-spacing: 0.12em; padding: 10px 18px; border-radius: 12px; }
.region.nepal { background: {red}; color: #fff; } .region.world { background: {c1}; color: #05202a; }
.tag { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.2); color: {ink}; }
.hl { position: absolute; left: 56px; right: 70px; top: 440px; font: 800 64px/1.08 Outfit; letter-spacing: -0.01em; text-wrap: balance; }
.panel { position: absolute; left: 56px; right: 84px; top: 690px; height: 520px; border-radius: 34px; background: {glass};
         border: 1px solid rgba(148,163,184,0.25); overflow: hidden; box-shadow: 0 30px 80px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.08); }
.kit { position: absolute; inset: 0; width: 100%; height: 100%; }
.sweep { position: absolute; top: 0; bottom: 0; width: 40%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.14), transparent); }
.stat { position: absolute; right: 24px; bottom: 24px; padding: 16px 24px; border-radius: 22px; background: rgba(5,9,22,0.82);
        border: 1px solid rgba(245,196,81,0.5); min-width: 260px; }
.sv { font: 900 64px Outfit; color: {gold}; line-height: 1; } .sv small { font-size: 34px; margin: 0 4px; }
.sl { font: 600 22px Inter; color: {mute}; margin-top: 6px; max-width: 340px; }
.src { position: absolute; left: 60px; top: 1226px; font: 700 20px "Space Mono"; color: {mute}; letter-spacing: 0.08em; }
#gd-card { position: absolute; left: 40px; top: 1268px; width: 360px; height: 420px; border-radius: 34px; overflow: hidden;
           background: radial-gradient(400px 300px at 50% 30%, #1e3a8a, #0b1328 70%); border: 1px solid rgba(34,211,238,0.35);
           box-shadow: 0 24px 70px rgba(0,0,0,0.5); }
#gd-card svg { position: absolute; left: -20px; top: 10px; width: 400px; height: 480px; }
#gd-plate { position: absolute; left: 40px; top: 1640px; width: 360px; padding: 10px 18px; border-radius: 0 0 22px 22px;
            background: linear-gradient(90deg, {gold}, #e59e1c); color: #101a33; }
#gd-plate b { font: 900 30px Outfit; letter-spacing: 0.04em; } #gd-plate span { display: block; font: 700 16px "Space Mono"; letter-spacing: 0.12em; }
.cap { position: absolute; left: 430px; right: 110px; top: 1300px; height: 300px; display: flex; align-items: center; }
.cap p { font: 800 50px/1.18 Outfit; color: {ink}; text-shadow: 0 4px 20px rgba(0,0,0,0.6); }
#intro #in-kicker { position: absolute; left: 60px; top: 300px; font: 700 24px "Space Mono"; letter-spacing: 0.3em; color: {c1}; }
#in-title { position: absolute; left: 52px; top: 340px; font: 900 190px/0.9 Outfit; letter-spacing: -0.02em; overflow: hidden; }
#in-title span { display: block; } #in-title span:last-child { background: linear-gradient(90deg, {c1}, {c2}); -webkit-background-clip: text; color: transparent; }
#in-with { position: absolute; left: 60px; top: 700px; font: 600 54px Outfit; } #in-with b { color: {gold}; }
#in-meta { position: absolute; left: 60px; top: 780px; font: 700 24px "Space Mono"; color: {mute}; letter-spacing: 0.14em; }
#in-rundown { position: absolute; left: 56px; right: 84px; top: 770px; }
#in-rh { font: 800 26px Outfit; letter-spacing: 0.18em; color: {gold}; margin-bottom: 14px; }
.ro { display: flex; align-items: center; gap: 16px; padding: 8px 16px; margin-bottom: 6px; border-radius: 18px; background: {glass};
      border: 1px solid rgba(148,163,184,0.2); }
.ro b { font: 900 34px Outfit; color: {c1}; width: 52px; } .ro span { flex: 1; font: 700 25px/1.2 Inter; }
.ro i { font: 800 16px Outfit; font-style: normal; letter-spacing: 0.12em; padding: 6px 10px; border-radius: 8px; }
.ro i.nepal { background: {red}; } .ro i.world { background: {c1}; color: #05202a; }
#ou-k { position: absolute; left: 60px; top: 380px; font: 800 30px "Space Mono"; color: {c1}; letter-spacing: 0.2em; }
#ou-t { position: absolute; left: 56px; top: 440px; font: 900 96px/1.02 Outfit; }
#ou-btn { position: absolute; left: 60px; top: 760px; padding: 26px 40px; border-radius: 26px; background: linear-gradient(90deg, {gold}, #e59e1c);
          color: #101a33; font: 800 44px Outfit; transform-origin: 30% 50%; } #ou-btn span { font-weight: 900; margin-right: 8px; }
#ou-s { position: absolute; left: 60px; top: 920px; font: 600 30px Inter; color: {mute}; }
#ai-note { position: absolute; left: 44px; top: 1730px; font: 700 16px "Space Mono"; color: #a8b3c7; letter-spacing: 0.06em; }'''


def build(ep_path, render=True):
    ep = json.loads(Path(ep_path).read_text(encoding="utf8"))
    proj = WORK / "news-build" / ep["id"]
    (proj / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copytree(HERE / "assets/fonts", proj / "assets/fonts", dirs_exist_ok=True)
    segs = make_voice(ep, proj)

    starts, t = [], LEAD
    for sg in segs:
        starts.append(t)
        t += sg["dur"] + GAP_AFTER
    total = round(t + 0.6, 2)
    n = len(ep["stories"])
    # scene windows: intro from 0, each story from its voice start - 0.25, outro until the end
    bounds = [0.0] + [max(0.0, starts[k] - 0.25) for k in range(1, len(segs))] + [total]
    speech = [(st + sg["words"][0]["s"], st + sg["words"][-1]["e"]) for sg, st in zip(segs, starts) if sg["words"]]
    music.bed(proj / "assets/bed.wav", total, hits=bounds[1:-1], speech=speech)

    scenes, js = [], []
    b, j = intro_html(ep, bounds[0], bounds[1] - bounds[0])
    scenes.append(b); js += j
    for i, st in enumerate(ep["stories"]):
        s, e = bounds[i + 1], bounds[i + 2]
        b, j = story_html(i, st, n, s, e - s)
        scenes.append(b); js += j
    b, j = outro_html(ep, bounds[-2], total - bounds[-2])
    scenes.append(b); js += j

    cap_html, cap_js = captions_html(segs, starts)
    all_words = [{"w": w["w"], "s": st + w["s"], "e": st + w["e"]} for sg, st in zip(segs, starts) for w in sg["words"]]
    date = dt.date.fromisoformat(ep["date"]).strftime("%d %b %Y").upper()
    ticker = "".join(f'<b>◆</b>{esc(st["headline"])}' for st in ep["stories"]) * 2
    seg_bars = "".join(f'<div id="seg{i}"><i></i></div>' for i in range(n))
    audio = "\n".join(f'<audio id="vo-{sg["id"]}" class="clip" src="{sg["file"]}" data-start="{st:.3f}" data-duration="{sg["dur"]:.3f}" data-track-index="20" data-volume="1"></audio>'
                      for sg, st in zip(segs, starts))
    tick_px = 60 * total
    script = "\n".join(js) + "\n" + cap_js + "\n" + gdai.js(all_words, total) + f'''
tl.to("#grid", {{ x: 60, y: 60, duration: {total}, ease: "none" }}, 0);
tl.to("#orb1", {{ x: 260, y: -180, duration: {total}, ease: "sine.inOut" }}, 0);
tl.to("#orb2", {{ x: -240, y: 200, duration: {total}, ease: "sine.inOut" }}, 0);
tl.fromTo("#tick-t", {{ x: 0 }}, {{ x: -{tick_px:.0f}, duration: {total}, ease: "none" }}, 0);
tl.from("#hdr", {{ y: -40, opacity: 0, duration: 0.6, ease: "expo.out" }}, 0.05);
tl.from("#gd-card, #gd-plate", {{ y: 80, opacity: 0, duration: 0.7, ease: "expo.out", stagger: 0.1 }}, 0.3);'''
    css = CSS
    for k, v in PALETTE.items():
        css = css.replace("{" + k + "}", v)
    css += "\n" + gdai.CSS
    index = f'''<!doctype html>
<html lang="en" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
{css}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}" data-layout-allow-overflow data-layout-allow-overlap>
<div id="bg"></div><div id="grid"></div><div id="orb1" class="orb"></div><div id="orb2" class="orb"></div>
<div id="hdr"><div id="logo">G.</div><div id="brand"><b>G. ROBOTICS</b><span>TECH NEWS · DAILY</span></div>
<div id="hdr-r"><b>EP {ep["episode"]:02d}</b><br/>{date}</div></div>
<div id="segs">{seg_bars}</div>
<div id="tick" data-layout-allow-overlap><div id="tick-l">LATEST</div><div id="tick-t">{ticker}</div></div>
{chr(10).join(scenes)}
<div id="gd-card">{gdai.svg()}</div>
<div id="gd-plate"><b>G. DAI</b><span>AI NEWS PRESENTER</span></div>
<div id="ai-note">G. Dai is an AI-generated presenter · Voice: AI</div>
{cap_html}
{audio}
<audio id="music" class="clip" src="assets/bed.wav" data-start="0" data-duration="{total}" data-track-index="21" data-volume="0.14"></audio>
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{script}
window.__timelines["main"] = tl;
</script>
</body>
</html>'''
    (proj / "index.html").write_text(index, encoding="utf8")
    print(f"built {proj} · {total}s · {n} stories", flush=True)
    try:
        run(["npx", "--yes", HF, "check"], cwd=proj)
    except subprocess.CalledProcessError:   # layout lint is advisory for daily automation; the QA gate still checks the mp4
        print("hyperframes check reported issues; rendering anyway", flush=True)
    if not render:
        return proj
    out = WORK / "out"
    out.mkdir(parents=True, exist_ok=True)
    mp4 = out / f"{ep['id']}.mp4"
    tmp = out / f"{ep['id']}.new-{os.getpid()}.mp4"
    run(["npx", "--yes", HF, "render", "-q", "delivery", "--sdr", "--quiet", "-o", tmp], cwd=proj)
    os.replace(tmp, mp4)
    print("rendered", mp4, flush=True)
    return mp4


if __name__ == "__main__":
    build(sys.argv[1], render="--no-render" not in sys.argv)
