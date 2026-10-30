"""Daily EE — turns one episode JSON into a rendered vertical YouTube Short.

    python build.py <episode.json> [--no-render]

Steps: equations (MathJax) → circuit (schemdraw) → voiceover with word timings (edge-tts South Asian English; Kokoro fallback)
→ HyperFrames project in build/<id>/ → check → render to out/<id>-<slug>.mp4 → out/<id>.youtube.json.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import beats_v2
import beats_v3
import mascot
import presenter
import sound
import styles
from beats_v2 import theme

ENGINE = Path(__file__).resolve().parent
# Work dirs: GR_WORK (default <repo>/work) holds build/ and out/; episodes come from anywhere.
ROOT = Path(os.environ.get("GR_WORK", ENGINE.parents[2] / "work"))
ENV = Path(os.environ["GR_ENV_FILE"]) if os.environ.get("GR_ENV_FILE") else None   # optional; cloud uses real env vars
_win_ff = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin"
FFMPEG_BIN = Path(shutil.which("ffmpeg")).parent if shutil.which("ffmpeg") else _win_ff
KOKORO_PY = os.environ.get("KOKORO_PYTHON", sys.executable)
HF = "hyperframes@0.8.198"
CONFIG = json.loads((ENGINE / "config.json").read_text(encoding="utf8"))

W, H = 1080, 1920
LEAD = 0.35      # silence before the first word
PAD = 0.45       # air after each beat's voice
MIN_BEAT = 2.2

esc = html.escape


def run(cmd, cwd=None, env=None):
    print("$", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, check=True, shell=(os.name == "nt" and str(cmd[0]) in ("npx", "node")))


def duration(path):
    out = subprocess.run([str(FFMPEG_BIN / "ffprobe"), "-v", "0", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


# ---------------------------------------------------------------- assets

def make_equations(ep, proj):
    jobs = []
    for i, b in enumerate(ep["beats"]):
        if b.get("latex"):
            st = styles.STYLES[STYLE]
            jobs.append({"tex": b["latex"], "out": str(proj / f"assets/eq/b{i:02d}.svg"), "color": st["onhi"] if b["type"] == "answer" else st["ink"], "beat": i})
    (proj / "assets/eq").mkdir(parents=True, exist_ok=True)
    jf = proj / "assets/eq/jobs.json"
    jf.write_text(json.dumps(jobs), encoding="utf8")
    run(["node", ENGINE / "tex2svg.mjs", jf])
    return {j["beat"]: j for j in json.loads(jf.read_text(encoding="utf8"))}


def make_circuit(ep, proj):
    for b in ep["beats"]:
        if b["type"] == "diagram" and b.get("circuit"):
            spec = proj / "assets/circuit.json"
            spec.write_text(json.dumps(b["circuit"]), encoding="utf8")
            out = proj / "assets/circuit.svg"
            st = styles.STYLES[STYLE]
            run([sys.executable, ENGINE / "circuit.py", spec, out, st["ink"], st["rule"]])
            svg = out.read_text(encoding="utf8")
            # inline-ready: drop the XML prolog and fixed pt size, keep the viewBox
            svg = re.sub(r"<\?xml[^>]*>", "", svg)
            svg = re.sub(r'\s(width|height)="[^"]*pt"', "", svg, count=2)
            return svg.replace("<svg ", '<svg id="dg-svg" ', 1)
    return ""


EDGE_VOICES = {"male": "en-US-AndrewMultilingualNeural", "female": "en-US-AvaMultilingualNeural"}
EDGE_PY = os.environ.get("EDGE_PYTHON", sys.executable)


def edge_voice(ep):
    """Natural English voice for this episode: brief "voice" (male | female | an en-IN/en-* edge voice name);
    the female presenter (maya) gets the female voice. Never a non-English voice — the channel is English only."""
    v = str(ep.get("voice") or ("female" if ep.get("presenter") == "maya" else "male"))
    v = EDGE_VOICES.get(v.lower(), v)
    return v if re.fullmatch(r"en-[A-Z]{2}-\w+Neural", v) else os.environ.get("GR_EDGE_VOICE", EDGE_VOICES["male"])


def voice_engine(chars):
    """config "voice": edge (South Asian English Microsoft neural voices, default, free) | kokoro | elevenlabs |
    auto (ElevenLabs while credits last, else edge). ElevenLabs is never called unless chosen explicitly."""
    pref = CONFIG.get("voice", "edge")
    if pref != "auto" or chars == 0:
        return pref if pref != "auto" else "edge"
    try:
        import urllib.request
        key = os.environ.get("ELEVENLABS_API_KEY") or next(l.split("=", 1)[1].strip() for l in ENV.read_text(encoding="utf8").splitlines() if l.startswith("ELEVENLABS_API_KEY="))
        req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key})
        sub = json.loads(urllib.request.urlopen(req, timeout=20).read())
        left = sub["character_limit"] - sub["character_count"]
        return "elevenlabs" if left >= chars * 1.1 else "edge"
    except Exception:
        return "edge"


def _drop(jobs):
    for j in jobs:  # one voice per episode: drop any half-made lines before the next engine
        Path(j["mp3"]).unlink(missing_ok=True)
        Path(j["words"]).unlink(missing_ok=True)


def make_voice(ep, proj):
    (proj / "assets/vo").mkdir(parents=True, exist_ok=True)
    voice = edge_voice(ep)
    jobs = [{"text": b["vo"], "mp3": str(proj / f"assets/vo/b{i:02d}.mp3"), "words": str(proj / f"assets/vo/b{i:02d}.json"), "voice": voice}
            for i, b in enumerate(ep["beats"])]
    jf = proj / "assets/vo/jobs.json"
    jf.write_text(json.dumps(jobs), encoding="utf8")
    engine = voice_engine(sum(len(j["text"]) for j in jobs if not Path(j["mp3"]).exists()))
    print("voice:", engine, voice if engine == "edge" else "")
    if engine == "elevenlabs":
        try:
            run(["node"] + ([f"--env-file={ENV}"] if ENV else []) + [ENGINE / "vo.mjs", jf])
        except subprocess.CalledProcessError:
            engine = "edge"
            _drop(jobs)
    if engine == "edge":
        try:
            run([EDGE_PY, ENGINE / "vo_edge.py", jf])
        except subprocess.CalledProcessError:
            engine = "kokoro"
            _drop(jobs)
    if engine == "kokoro":
        run([KOKORO_PY, ENGINE / "vo_kokoro.py", jf])
    out = []
    for j in jobs:
        out.append({"mp3": j["mp3"], "dur": duration(j["mp3"]), "words": json.loads(Path(j["words"]).read_text(encoding="utf8"))})
    return out


# ---------------------------------------------------------------- scene templates

FONTS = '''    #root { position: absolute; inset: 0; overflow: hidden; }
    .k-chip { display: inline-block; font-family: "Archivo Black"; font-size: 34px; letter-spacing: 0.08em; color: #111827; background: #ffd400; padding: 8px 20px 6px; border-radius: 10px; }
    .k-chip.cu { background: #b45309; color: #fff; }
    .k-h { font-family: "Archivo Black"; color: #111827; line-height: 1.04; letter-spacing: -0.01em; }
    .k-b { font-family: "Inter"; font-weight: 700; color: #111827; }
    .k-eq { display: block; }
    .k-eq svg { width: 100%; height: 100%; }
'''


def eq_box(svg_path, aspect, max_w, max_h):
    """Size an equation to fit max_w × max_h keeping its aspect; returns (w, h)."""
    w = max_w
    h = w / aspect
    if h > max_h:
        h = max_h
        w = h * aspect
    return round(w), round(h)


THEME = beats_v2.THEMES["explain"]
STYLE = "classic"
MASCOT = False
PRESENTER = None


def scene(cid, dur, body_css, body_html, script):
    chip_css = f'    .k-chip {{ background: {THEME["accent"]}; color: {THEME["accent_ink"]}; }}\n'
    return styles.skin(f'''<template>
  <style>
{FONTS}{chip_css}{body_css}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="{W}" data-height="{H}">
{body_html}
  </div>
  <script>
    (() => {{
      const tl = gsap.timeline({{ paused: true }});
{script}
      window.__timelines["{cid}"] = tl;
    }})();
  </script>
</template>
''', STYLE)


def words_html(text, cls):
    return " ".join(f'<span class="{cls}">{esc(w)}</span>' for w in text.split())


def cover_text(ep):
    """Frame 0 is the hook and the Reel's cover: the cover-thumbnail-brief text when the brief has one, else the title."""
    return ((ep.get("viral") or {}).get("cover_text") or ep["title"]).strip()


def beat_hook(cid, b, dur, ep):
    num = ep["id"].replace("ep", "#") if CONFIG.get("show_id", True) else ep.get("series", "")
    css = '''    #hk-num { position: absolute; left: 80px; right: 80px; top: 300px; font-family: "Archivo Black"; font-size: @NUMPX@px; color: #b45309; white-space: nowrap; }
    #hk-title { position: absolute; left: 80px; right: 80px; top: 380px; font-size: 112px; }
    #hk-title .w { display: inline-block; }
    #hk-mark { position: absolute; left: 70px; top: 0; height: 0; background: #ffd400; }
    #hk-line { position: absolute; left: 80px; right: 270px; top: 930px; font-size: 54px; }
    #hk-bolt { position: absolute; right: 70px; top: 760px; width: 160px; height: 220px; }'''
    label = " · ".join(x for x in (num, ep.get("category", "")) if x)
    if len(label) > 30 and num:
        label = num                       # long series names: one line, no category
    css = css.replace("@NUMPX@", str(min(46, int(920 / (0.62 * max(1, len(label)))))))   # always one line
    body = f'''    <div id="hk-num">{esc(label)}</div>
    <div id="hk-title" class="k-h">{words_html(cover_text(ep), "w")}</div>
    <div id="hk-line" class="k-b">{esc(b.get("text", ""))}</div>
    <svg id="hk-bolt" viewBox="0 0 80 110"><path d="M48 2 L8 62 H36 L28 108 L72 42 H44 Z" fill="#ffd400" stroke="#111827" stroke-width="4" stroke-linejoin="round"/></svg>'''
    js = f'''      tl.fromTo("#hk-title", {{ scale: 1.1, transformOrigin: "0% 0%" }}, {{ scale: 1, duration: 0.35, ease: "power4.out" }}, 0);
      tl.fromTo("#hk-title .w", {{ y: 10 }}, {{ y: 0, duration: 0.3, ease: "power3.out", stagger: 0.05 }}, 0);
      tl.to("#hk-title", {{ scale: 1.035, duration: {dur:.2f}, ease: "none", transformOrigin: "0% 0%" }}, 0.4);
      tl.fromTo("#hk-bolt", {{ scale: 0, rotation: -20 }}, {{ scale: 1, rotation: 0, duration: 0.4, ease: "back.out(2.2)" }}, 0.4);
      tl.fromTo("#hk-line", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25 }}, Math.min(1.2, {dur:.2f} * 0.45));'''
    return scene(cid, dur, css, body, js)


def beat_concept(cid, b, dur, ep):
    pts = b.get("points", [])
    css = '''    #cc-chip { position: absolute; left: 80px; top: 300px; }
    #cc-h { position: absolute; left: 80px; right: 80px; top: 390px; font-size: 84px; }
    .cc-p { position: absolute; left: 80px; right: 80px; font-size: 54px; display: flex; gap: 26px; align-items: center; }
    .cc-p i { flex: none; width: 34px; height: 34px; background: #ffd400; border: 4px solid #111827; border-radius: 6px; }'''
    rows = "\n".join(f'    <div id="cc-p{k}" class="cc-p k-b" style="top: {720 + k * 120}px"><i></i><span>{esc(p)}</span></div>' for k, p in enumerate(pts))
    body = f'''    <div id="cc-chip" class="k-chip">{esc(b.get("tag", "THE IDEA"))}</div>
    <div id="cc-h" class="k-h">{esc(b.get("text", ""))}</div>
{rows}'''
    js = ['      tl.fromTo("#cc-h", { opacity: 0, filter: "blur(8px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.25, ease: "power2.out" }, 0.05);']
    for k in range(len(pts)):
        at = dur * (0.3 + 0.55 * k / max(1, len(pts)))
        js.append(f'      tl.fromTo("#cc-p{k}", {{ opacity: 0, x: -60 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: "power3.out" }}, {at:.2f});')
    return scene(cid, dur, css, body, "\n".join(js))


def beat_diagram(cid, b, dur, ep, circuit_svg):
    css = '''    #dg-chip { position: absolute; left: 80px; top: 300px; }
    #dg-cap { position: absolute; left: 80px; right: 80px; top: 380px; font-size: 62px; }
    #dg-box { position: absolute; left: 60px; right: 60px; top: 520px; height: 600px; display: flex; align-items: center; justify-content: center; }
    #dg-svg { width: 100%; height: 100%; overflow: visible; }'''
    body = f'''    <div id="dg-chip" class="k-chip">CIRCUIT</div>
    <div id="dg-cap" class="k-h">{esc(b.get("caption", ""))}</div>
    <div id="dg-box">{circuit_svg}</div>'''
    js = f'''      const paths = document.querySelectorAll("#dg-svg path, #dg-svg circle, #dg-svg polyline, #dg-svg line, #dg-svg polygon");
      paths.forEach((p) => {{ p.setAttribute("pathLength", "1"); p.style.strokeDasharray = "1"; }});
      const texts = document.querySelectorAll("#dg-svg text");
      const draw = {{ u: 0 }};
      const paint = () => paths.forEach((p, i) => {{ const k = Math.min(1, Math.max(0, draw.u * paths.length - i * 0.6) / 1.2); p.style.strokeDashoffset = String(1 - k); p.style.fillOpacity = String(k); }});
      tl.fromTo(draw, {{ u: 0 }}, {{ u: 1, duration: Math.min(2.2, {dur:.2f} * 0.6), ease: "power1.inOut", onUpdate: paint }}, 0.1);
      tl.fromTo(texts, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, stagger: 0.08 }}, Math.min(1.6, {dur:.2f} * 0.45));
      tl.fromTo("#dg-cap", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power3.out" }}, 0.05);
      paint();'''
    return scene(cid, dur, css, body, js)


def beat_formula(cid, b, dur, ep, eq):
    w, h = eq_box(None, eq["aspect"], 920, 260)
    terms = b.get("terms", [])
    css = f'''    #fm-chip {{ position: absolute; left: 80px; top: 300px; }}
    #fm-eq {{ position: absolute; left: {(W - w) // 2}px; top: {420 + (260 - h) // 2}px; width: {w}px; height: {h}px; }}
    #fm-mark {{ position: absolute; left: 60px; right: 60px; top: 400px; height: 300px; background: #fff7c2; border-radius: 22px; transform-origin: 0 50%; }}
    .fm-t {{ position: absolute; left: 100px; right: 80px; font-size: 48px; display: flex; gap: 22px; }}
    .fm-t b {{ font-family: "Archivo Black"; font-weight: 400; min-width: 110px; color: #b45309; }}'''
    rows = "\n".join(f'    <div id="fm-t{k}" class="fm-t k-b" style="top: {760 + k * 92}px"><b>{esc(t["sym"])}</b><span>{esc(t["meaning"])}</span></div>' for k, t in enumerate(terms[:4]))
    body = f'''    <div id="fm-chip" class="k-chip">FORMULA</div>
    <div id="fm-mark"></div>
    <img id="fm-eq" class="k-eq" src="assets/eq/{Path(eq["out"]).name}" alt="" />
{rows}'''
    js = ['      tl.fromTo("#fm-mark", { scaleX: 0 }, { scaleX: 1, duration: 0.35, ease: "power3.inOut" }, 0.05);',
          '      tl.fromTo("#fm-eq", { opacity: 0, scale: 1.15 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power4.out" }, 0.3);']
    for k in range(len(terms[:4])):
        at = dur * (0.35 + 0.5 * k / max(1, len(terms[:4])))
        js.append(f'      tl.fromTo("#fm-t{k}", {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power3.out" }}, {at:.2f});')
    return scene(cid, dur, css, body, "\n".join(js))


def beat_given(cid, b, dur, ep):
    items = b.get("items", [])[:5]
    css = '''    #gv-chip { position: absolute; left: 80px; top: 300px; }
    .gv-r { position: absolute; left: 80px; right: 80px; height: 96px; display: flex; align-items: center; border-bottom: 3px dashed #c9d4e3; font-size: 56px; }
    .gv-r b { font-family: "Archivo Black"; font-weight: 400; width: 220px; color: @COOL@; }
    #gv-find { position: absolute; left: 80px; right: 80px; top: 900px; padding: 22px 28px; background: #ffd400; border: 5px solid #111827; border-radius: 18px; font-size: 52px; color: @ONHI@; }
    #gv-find small { font-family: "Archivo Black"; font-size: 34px; letter-spacing: 0.08em; display: block; margin-bottom: 6px; }'''
    rows = "\n".join(f'    <div id="gv-r{k}" class="gv-r k-b" style="top: {400 + k * 104}px"><b>{esc(it["sym"])}</b><span>= {esc(it["value"])}</span></div>' for k, it in enumerate(items))
    body = f'''    <div id="gv-chip" class="k-chip">GIVEN</div>
{rows}
    <div id="gv-find" class="k-b"><small>FIND</small>{esc(b.get("find", ""))}</div>'''
    js = []
    for k in range(len(items)):
        at = 0.1 + (dur * 0.45) * k / max(1, len(items))
        js.append(f'      tl.fromTo("#gv-r{k}", {{ opacity: 0, x: 60 }}, {{ opacity: 1, x: 0, duration: 0.25, ease: "power3.out" }}, {at:.2f});')
    js.append(f'      tl.fromTo("#gv-find", {{ opacity: 0, scale: 0.85 }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.8)" }}, {dur * 0.58:.2f});')
    return scene(cid, dur, css, body, "\n".join(js))


def beat_step(cid, b, dur, ep, eq, k, n, prev_eq):
    w, h = eq_box(None, eq["aspect"], 940, 300)
    prev = ""
    pcss = ""
    if prev_eq:
        pw, ph = eq_box(None, prev_eq["aspect"], 760, 120)
        pcss = f"    #st-prev {{ position: absolute; left: {(W - pw) // 2}px; top: {400 + (120 - ph) // 2}px; width: {pw}px; height: {ph}px; opacity: 0.35; }}\n"
        prev = f'    <img id="st-prev" class="k-eq" src="assets/eq/{Path(prev_eq["out"]).name}" alt="" />'
    css = f'''    #st-chip {{ position: absolute; left: 80px; top: 300px; }}
{pcss}    #st-arrow {{ position: absolute; left: 510px; top: 560px; width: 60px; height: 70px; }}
    #st-eq {{ position: absolute; left: {(W - w) // 2}px; top: {660 + (300 - h) // 2}px; width: {w}px; height: {h}px; }}'''
    body = f'''    <div id="st-chip" class="k-chip">STEP {k} / {n}</div>
{prev}
    <svg id="st-arrow" viewBox="0 0 60 70"><path d="M30 4 V56 M10 38 L30 62 L50 38" fill="none" stroke="#b45309" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/></svg>
    <img id="st-eq" class="k-eq" src="assets/eq/{Path(eq["out"]).name}" alt="" />'''
    js = '''      tl.fromTo("#st-arrow", { opacity: 0, y: -30 }, { opacity: 1, y: 0, duration: 0.25, ease: "power3.out" }, 0.1);
      tl.fromTo("#st-eq", { opacity: 0, clipPath: "inset(0% 100% 0% 0%)" }, { opacity: 1, clipPath: "inset(0% 0% 0% 0%)", duration: 0.6, ease: "power2.inOut" }, 0.3);'''
    return scene(cid, dur, css, body, js)


def beat_answer(cid, b, dur, ep, eq):
    w, h = eq_box(None, eq["aspect"], 860, 240)
    css = f'''    #an-chip {{ position: absolute; left: 80px; top: 300px; }}
    #an-box {{ position: absolute; left: 60px; right: 60px; top: 460px; height: 360px; background: #ffd400; border: 6px solid #111827; border-radius: 28px; box-shadow: 14px 14px 0 #111827; }}
    #an-eq {{ position: absolute; left: {(W - w) // 2}px; top: {460 + (360 - h) // 2}px; width: {w}px; height: {h}px; }}
    #an-note {{ position: absolute; left: 80px; right: 80px; top: 920px; font-size: 58px; text-align: center; }}'''
    body = f'''    <div id="an-chip" class="k-chip cu">ANSWER</div>
    <div id="an-box"></div>
    <img id="an-eq" class="k-eq" src="assets/eq/{Path(eq["out"]).name}" alt="" />
    <div id="an-note" class="k-b">{esc(b.get("note", ""))}</div>'''
    js = '''      tl.fromTo("#an-box", { scale: 0.6, opacity: 0, rotation: -3 }, { scale: 1, opacity: 1, rotation: 0, duration: 0.4, ease: "back.out(1.7)" }, 0.05);
      tl.fromTo("#an-eq", { opacity: 0, scale: 1.3 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power4.out" }, 0.3);
      tl.fromTo("#an-note", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.25, ease: "power3.out" }, 0.8);'''
    return scene(cid, dur, css, body, js)


def beat_tip(cid, b, dur, ep):
    css = '''    #tp-chip { position: absolute; left: 80px; top: 300px; }
    #tp-bulb { position: absolute; left: 80px; top: 420px; width: 150px; height: 190px; }
    #tp-text { position: absolute; left: 80px; right: 80px; top: 660px; font-size: 72px; }'''
    body = f'''    <div id="tp-chip" class="k-chip">{esc(b.get("tag", "PRO TIP"))}</div>
    <svg id="tp-bulb" viewBox="0 0 75 95"><path d="M37 4 C17 4 6 19 6 34 C6 47 15 54 20 62 V72 H54 V62 C59 54 68 47 68 34 C68 19 57 4 37 4 Z" fill="#ffd400" stroke="#111827" stroke-width="5" stroke-linejoin="round"/><path d="M24 80 H50 M28 89 H46" stroke="#111827" stroke-width="5" stroke-linecap="round"/></svg>
    <div id="tp-text" class="k-h">{words_html(b.get("text", ""), "w")}</div>'''
    js = '''      tl.fromTo("#tp-bulb", { scale: 0, rotation: 15 }, { scale: 1, rotation: 0, duration: 0.4, ease: "back.out(2)" }, 0.05);
      tl.fromTo("#tp-text .w", { opacity: 0.12 }, { opacity: 1, duration: 0.12, stagger: 0.09 }, 0.3);'''
    return scene(cid, dur, css, body, js)


def beat_outro(cid, b, dur, ep):
    css = '''    #ot-bolt { position: absolute; left: 440px; top: 330px; width: 200px; height: 275px; }
    #ot-name { position: absolute; left: 0; right: 0; top: 640px; text-align: center; font-size: 130px; }
    #ot-sub { position: absolute; left: 80px; right: 80px; top: 800px; text-align: center; font-size: 54px; }
    #ot-sub-btn { position: absolute; left: 290px; top: 940px; width: 500px; height: 120px; background: #e11d2e; color: #fff; border-radius: 60px; font-family: "Archivo Black"; font-size: 54px; display: flex; align-items: center; justify-content: center; letter-spacing: 0.04em; }
    #ot-brand { position: absolute; left: 0; right: 0; top: 1090px; display: flex; justify-content: center; align-items: center; gap: 16px; font-family: "Inter"; font-weight: 700; font-size: 38px; color: #111827; }
    #ot-brand img { width: 56px; height: 56px; border-radius: 12px; }'''
    body = f'''    <svg id="ot-bolt" viewBox="0 0 80 110"><path d="M48 2 L8 62 H36 L28 108 L72 42 H44 Z" fill="#ffd400" stroke="#111827" stroke-width="4" stroke-linejoin="round"/></svg>
    <div id="ot-name" class="k-h">{esc(CONFIG["channel"])}</div>
    <div id="ot-sub" class="k-b">{esc(CONFIG["lane_taglines"].get(ep.get("format"), CONFIG["tagline"]))}</div>
    <div id="ot-sub-btn">{esc(CONFIG.get("cta", "SUBSCRIBE"))}</div>
    <div id="ot-brand"><img src="assets/img/logo.png" alt="" />{esc(CONFIG["brand"])}</div>'''
    js = '''      tl.fromTo("#ot-bolt", { scale: 0, rotation: -25 }, { scale: 1, rotation: 0, duration: 0.45, ease: "back.out(2.2)" }, 0.05);
      tl.fromTo("#ot-name", { opacity: 0, scale: 1.3 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power4.out" }, 0.25);
      tl.fromTo("#ot-sub", { opacity: 0 }, { opacity: 1, duration: 0.25 }, 0.6);
      tl.fromTo("#ot-sub-btn", { scale: 0 }, { scale: 1, duration: 0.35, ease: "back.out(2)" }, 0.9);
      tl.fromTo("#ot-brand", { opacity: 0 }, { opacity: 1, duration: 0.3 }, 1.2);'''
    return scene(cid, dur, css, body, js)


# ---------------------------------------------------------------- chrome + captions

def chrome(total, ep):
    th = theme(ep)
    ground = styles.STYLES[STYLE]["ground"] or f'background-color: {th["ground"]}; background-image: linear-gradient({th["grid"]} 2px, transparent 2px), linear-gradient(90deg, {th["grid"]} 2px, transparent 2px); background-size: 60px 60px;'
    css = f'''    #ch-grid {{ position: absolute; inset: 0; {ground} }}
    #ch-top {{ position: absolute; left: 80px; right: 80px; top: 196px; display: flex; justify-content: space-between; align-items: center; font-family: "Archivo Black"; font-size: 32px; color: #111827; letter-spacing: 0.06em; }}
    #ch-top span {{ color: {th["rule"] if STYLE == "classic" else "#b45309"}; }}
    #ch-bar {{ position: absolute; left: 80px; right: 80px; top: 1338px; height: 10px; background: {th["grid"]}; border-radius: 5px; overflow: hidden; }}
    #ch-fill {{ position: absolute; left: 0; top: 0; bottom: 0; width: 100%; background: {th["rule"]}; transform-origin: 0 50%; }}'''
    body = f'''    <div id="ch-grid"></div>
    <div id="ch-top"><div>⚡ {esc(CONFIG["channel"].upper())} · {esc(th["label"])}</div><span>{esc(ep["id"].replace("ep", "#") if CONFIG.get("show_id", True) else ep.get("date", ""))}</span></div>
    <div id="ch-bar"><div id="ch-fill"></div></div>'''
    js = f'''      tl.fromTo("#ch-fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {total:.2f}, ease: "none" }}, 0);
      tl.fromTo("#ch-grid", {{ backgroundPositionY: 0 }}, {{ backgroundPositionY: 120, duration: {total:.2f}, ease: "none" }}, 0);''' if STYLE in ("classic", "blueprint", "neon") else f'''      tl.fromTo("#ch-fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {total:.2f}, ease: "none" }}, 0);'''
    return scene("chrome", total, css, body, js)


def captions(beats, starts, voices):
    groups = []
    for bi, v in enumerate(voices):
        cur = []
        for w in v["words"]:
            word = re.sub(r"\[[^\]]*\]", "", w["w"]).strip()
            if not word:
                continue
            cur.append({"w": word, "s": starts[bi] + w["s"], "e": starts[bi] + w["e"]})
            if len(cur) >= 3 or re.search(r"[.,!?;:]$", word):
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
    css = '''    .cp-g { position: absolute; left: 60px; right: 60px; top: 1170px; text-align: center; font-family: "Inter"; font-weight: 900; font-size: 60px; line-height: 1.15; color: #111827; }
    .cp-w { display: inline-block; padding: 0 10px; border-radius: 10px; }'''
    rows, js = [], []
    for gi, g in enumerate(groups):
        s = g[0]["s"] - 0.05
        e = groups[gi + 1][0]["s"] - 0.05 if gi + 1 < len(groups) and groups[gi + 1][0]["s"] - g[-1]["e"] < 0.6 else g[-1]["e"] + 0.25
        spans = " ".join(f'<span id="cp{gi}w{k}" class="cp-w">{esc(w["w"])}</span>' for k, w in enumerate(g))
        rows.append(f'    <div id="cp{gi}" class="cp-g clip" data-start="{s:.3f}" data-duration="{max(0.2, e - s):.3f}" data-track-index="1">{spans}</div>')
        for k, w in enumerate(g):
            js.append(f'      tl.fromTo("#cp{gi}w{k}", {{ backgroundColor: "rgba(255,212,0,0)" }}, {{ backgroundColor: "rgba(255,212,0,1)", color: "@ONHI@", duration: 0.06, immediateRender: false }}, {w["s"]:.3f});')
            js.append(f'      tl.to("#cp{gi}w{k}", {{ backgroundColor: "rgba(255,212,0,0)", color: "#111827", duration: 0.06 }}, {max(w["e"], w["s"] + 0.12):.3f});')
    total = starts[-1] + voices[-1]["dur"] + 1
    if PRESENTER:
        mcss, mhtml, mjs = presenter.parts([w for g in groups for w in g], total, PRESENTER)
        css += "\n" + mcss
        rows.append(mhtml)
        js.append(mjs)
    elif MASCOT:
        mcss, mhtml, mjs = mascot.parts([w for g in groups for w in g], total)
        css += "\n" + mcss
        rows.append(mhtml)
        js.append(mjs)
    return scene("captions", total, css, "\n".join(rows), "\n".join(js))


# ---------------------------------------------------------------- sound

PAYOFF = ("answer", "reveal", "verdict", "stat", "headline", "profile")


def sound_design(ep, proj, starts, voices, total):
    """Music bed ducked under the voice + sub-boom hits on the hook claim, the payoff (with a riser into it) and the CTA.
    Falls back to the old fixed-level bed if the stem cannot be made."""
    types = [b["type"] for b in ep["beats"]]
    pay = next((i for i, t in enumerate(types) if t in PAYOFF and i > 0), max(1, len(types) - 2))
    hits = [starts[0] + 0.05, starts[pay] - 0.05] + ([starts[-1] - 0.05] if types[-1] == "outro" and len(types) > 2 else [])
    try:
        sound.mix(proj / "assets/music/bed.mp3", proj / "assets/music/mix.wav", total, sound.speech_spans(starts, voices),
                  hits=hits, rises=[starts[pay] - 0.05], ffmpeg=str(FFMPEG_BIN / "ffmpeg"))
        return f'      <audio id="music" data-timeline-role="music" class="clip" src="assets/music/mix.wav" data-start="0" data-duration="{total}" data-track-index="7" data-volume="1"></audio>'
    except Exception as e:  # noqa: BLE001 — a plain bed is better than no Reel
        print("sound design failed, plain bed:", e)
        return f'      <audio id="music" data-timeline-role="music" class="clip" src="assets/music/bed.mp3" data-start="0" data-duration="{total}" data-media-start="2" data-track-index="7" data-volume="0.1" data-fade-out="1.5"></audio>'


# ---------------------------------------------------------------- assemble

def build(ep_path, render=True):
    ep = json.loads(Path(ep_path).read_text(encoding="utf8"))
    global THEME, STYLE, MASCOT, PRESENTER
    THEME = theme(ep)
    STYLE = styles.pick(ep)
    MASCOT = ep.get("mascot", int(re.sub(r"\D", "", ep["id"]) or 0) % 2 == 1)
    PRESENTER = ep.get("presenter")
    print("style:", STYLE, f"· presenter {PRESENTER}" if PRESENTER else ("· mascot" if MASCOT else ""))
    beats_v2.EMOJI_DIR = ROOT / "build" / ep["id"] / "assets" / "emoji"
    proj = ROOT / "build" / ep["id"]
    if proj.exists():
        shutil.rmtree(proj / "compositions", ignore_errors=True)
    shutil.copytree(ENGINE / "template", proj, dirs_exist_ok=True)
    (proj / "compositions").mkdir(exist_ok=True)
    (proj / "package.json").write_text(json.dumps({"name": f"ee-{ep['id']}", "private": True, "type": "module"}, indent=1))
    (proj / "meta.json").write_text(json.dumps({"id": f"ee-{ep['id']}", "name": ep["title"]}))

    eqs = make_equations(ep, proj)
    circuit_svg = make_circuit(ep, proj)
    voices = make_voice(ep, proj)

    starts, durs, t = [], [], LEAD
    for v in voices:
        d = max(MIN_BEAT, v["dur"] + PAD)
        starts.append(t)
        durs.append(d)
        t += d
    total = round(t + 0.4, 2)

    steps = [i for i, b in enumerate(ep["beats"]) if b["type"] == "step"]
    hosts, audio = [], []
    prev_eq = None
    for i, b in enumerate(ep["beats"]):
        cid = f"b{i:02d}-{b['type']}"
        d = durs[i]
        ty = b["type"]
        if ty == "hook": src = beat_hook(cid, b, d, ep)
        elif ty == "concept": src = beat_concept(cid, b, d, ep)
        elif ty == "diagram": src = beat_diagram(cid, b, d, ep, circuit_svg)
        elif ty == "formula": src = beat_formula(cid, b, d, ep, eqs[i])
        elif ty == "given": src = beat_given(cid, b, d, ep)
        elif ty == "step":
            src = beat_step(cid, b, d, ep, eqs[i], steps.index(i) + 1, len(steps), prev_eq)
            prev_eq = eqs[i]
        elif ty == "answer": src = beat_answer(cid, b, d, ep, eqs[i])
        elif ty == "tip": src = beat_tip(cid, b, d, ep)
        elif ty == "outro": src = beat_outro(cid, b, d, ep)
        elif ty == "analogy": src = beats_v2.beat_analogy(scene, cid, b, d, ep)
        elif ty == "question": src = beats_v2.beat_question(scene, cid, b, d, ep)
        elif ty == "countdown": src = beats_v2.beat_countdown(scene, cid, b, d, ep)
        elif ty == "reveal": src = beats_v2.beat_reveal(scene, cid, b, d, ep)
        elif ty == "verdict": src = beats_v2.beat_verdict(scene, cid, b, d, ep)
        elif ty == "wrong": src = beats_v2.beat_wrong(scene, cid, b, d, ep, eqs.get(i), eq_box)
        elif ty in beats_v3.BEATS: src = beats_v3.BEATS[ty](scene, cid, b, d, ep)
        else: raise SystemExit(f"unknown beat type {ty}")
        (proj / f"compositions/{cid}.html").write_text(src, encoding="utf8")
        hs = 0 if i == 0 else starts[i]
        hd = d + (starts[0] if i == 0 else 0)
        hosts.append(f'      <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" data-start="{hs:.3f}" data-duration="{hd:.3f}" data-track-index="2" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>')
        audio.append(f'      <audio id="vo{i:02d}" class="clip" src="assets/vo/b{i:02d}.mp3" data-start="{starts[i]:.3f}" data-duration="{voices[i]["dur"]:.3f}" data-track-index="5" data-volume="1"></audio>')
        if i > 0:
            snd = "pop" if ty in ("step", "answer", "given") else "whoosh"
            audio.append(f'      <audio id="sfx{i:02d}" class="clip" src="assets/sfx/{snd}.mp3" data-start="{max(0, starts[i] - 0.12):.3f}" data-duration="0.9" data-track-index="6" data-volume="0.22"></audio>')

    (proj / "compositions/chrome.html").write_text(chrome(total, ep), encoding="utf8")
    (proj / "compositions/captions.html").write_text(captions(ep["beats"], starts, voices), encoding="utf8")
    music = sound_design(ep, proj, starts, voices, total)

    index = f'''<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: {styles.base(STYLE)}; }}
      #root {{ position: relative; width: 100%; height: 100%; }}
      #captions {{ z-index: 20; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
      <div id="chrome" data-composition-id="chrome" data-composition-src="compositions/chrome.html" data-start="0" data-duration="{total}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}"></div>
{chr(10).join(hosts)}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{total}" data-track-index="3" data-track-kind="captions" data-width="{W}" data-height="{H}"></div>
{chr(10).join(audio)}
{music}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
'''
    (proj / "index.html").write_text(index, encoding="utf8")
    print(f"built {proj} · {total}s · {len(ep['beats'])} beats")

    env = dict(os.environ, PATH=f"{FFMPEG_BIN}{os.pathsep}{os.environ['PATH']}")
    run(["npx", "--yes", HF, "check"], cwd=proj, env=env)
    if not render:
        return proj
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    mp4 = out / f"{ep['id']}-{ep['slug']}.mp4"
    # Render to a fresh name, then swap it in. If the old file is open in a player (Windows locks it),
    # keep the fresh name instead of failing.
    tmp = out / f"{ep['id']}-{ep['slug']}.new-{os.getpid()}.mp4"
    run(["npx", "--yes", HF, "render", "-q", "delivery", "--sdr", "--quiet", "-o", tmp], cwd=proj, env=env)
    try:
        os.replace(tmp, mp4)
    except PermissionError:
        print(f"{mp4.name} is locked (open in a player?); keeping {tmp.name}")
        mp4 = tmp
    write_youtube_meta(ep, out, total)
    print("rendered", mp4)
    return mp4


def write_youtube_meta(ep, out, total):
    if ep.get("description"):  # news / people / clip lanes write their own description and sources
        lines = [ep["title"], "", ep["description"], ""]
        if ep.get("sources"):
            lines += ["Sources:"] + [f"• {u}" for u in ep["sources"]] + [""]
        lines.append(CONFIG.get("lane_footer", CONFIG["description_footer"]))
        meta = {"title": f"{ep['title']} #shorts"[:100], "description": "\n".join(lines),
                "tags": (ep.get("tags", []) + CONFIG["tags"])[:30], "categoryId": "28" if ep.get("format") == "news" else "27",
                "privacyStatus": "private", "duration": total}
        (out / f"{ep['id']}.youtube.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf8")
        return
    beats = {b["type"]: b for b in ep["beats"]}
    given = beats.get("given", {})
    lines = [ep["title"], "",
             beats.get("concept", {}).get("text", ""), "",
             "Worked example: " + given.get("find", ""),
             "Answer: " + beats.get("answer", {}).get("note", ""), "",
             "Pro tip: " + beats.get("tip", {}).get("text", ""), "",
             CONFIG["description_footer"]]
    meta = {
        "title": f"{ep['title']} #shorts"[:100],
        "description": "\n".join(lines),
        "tags": CONFIG["tags"] + [ep.get("category", "").lower()],
        "categoryId": "27",
        "privacyStatus": "private",
        "duration": total,
    }
    (out / f"{ep['id']}.youtube.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(args[0], render="--no-render" not in sys.argv)
