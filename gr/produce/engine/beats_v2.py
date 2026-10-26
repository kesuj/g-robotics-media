"""Extra beat types and per-format themes for Daily EE (imported by build.py).

Formats (episode "format"): explain (default), mcq, myth, eli5, mistake.
New beats: analogy, question, countdown, reveal, verdict, wrong.
"""
import html
import urllib.request
from pathlib import Path

esc = html.escape
EMOJI_DIR = None   # set by build.py to <project>/assets/emoji
TWEMOJI = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{}.svg"


def emoji_img(icon, cls):
    """Emoji as a Twemoji SVG file (the renderer has no colour-emoji font); downloaded once per project."""
    cp = "-".join(f"{ord(c):x}" for c in icon if ord(c) != 0xFE0F)
    out = Path(EMOJI_DIR) / f"{cp}.svg"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            out.write_bytes(urllib.request.urlopen(TWEMOJI.format(cp), timeout=30).read())
        except Exception:
            cp = "1f4a1"  # 💡 fallback
            out = Path(EMOJI_DIR) / f"{cp}.svg"
            if not out.exists():
                out.write_bytes(urllib.request.urlopen(TWEMOJI.format(cp), timeout=30).read())
    return f'<img class="{cls}" src="assets/emoji/{out.name}" alt="" />'

# Each format gets its own ground, grid, accent and label, so a week of videos doesn't look like one template.
THEMES = {
    "explain": {"label": "THEORY → NUMERICAL", "ground": "#ffffff", "grid": "#e3eaf4", "accent": "#ffd400", "accent_ink": "@ONHI@", "rule": "#b45309"},
    "mcq":     {"label": "NEC LICENSE EXAM Q", "ground": "#f1f6ff", "grid": "#d6e4ff", "accent": "#2563eb", "accent_ink": "#ffffff", "rule": "#1d4ed8"},
    "myth":    {"label": "TRUE OR FALSE?",      "ground": "#fff8f1", "grid": "#fde3cc", "accent": "#e11d48", "accent_ink": "#ffffff", "rule": "#be123c"},
    "eli5":    {"label": "EXPLAINED LIKE I'M 5", "ground": "#f0fdf4", "grid": "#ccefd8", "accent": "#16a34a", "accent_ink": "#ffffff", "rule": "#15803d"},
    "mistake": {"label": "COMMON EXAM MISTAKE", "ground": "#fafafa", "grid": "#e5e5e5", "accent": "#7c3aed", "accent_ink": "#ffffff", "rule": "#6d28d9"},
    "news":    {"label": "TECH & POWER NEWS",   "ground": "#fff7ed", "grid": "#fde2c4", "accent": "#dc2626", "accent_ink": "#ffffff", "rule": "#b91c1c"},
    "people":  {"label": "MINDS BEHIND IT",     "ground": "#f5f3ff", "grid": "#e0dbff", "accent": "#7c3aed", "accent_ink": "#ffffff", "rule": "#6d28d9"},
    "clip":    {"label": "DID YOU KNOW?",       "ground": "#ecfeff", "grid": "#c5f1f7", "accent": "#0891b2", "accent_ink": "#ffffff", "rule": "#0e7490"},
}


def theme(ep):
    return THEMES.get(ep.get("format", "explain"), THEMES["explain"])


def chip(text, th, extra=""):
    return f'<div class="k-chip" style="background:{th["accent"]};color:{th["accent_ink"]};{extra}">{esc(text)}</div>'


def beat_analogy(scene, cid, b, dur, ep):
    """Everyday thing = electrical thing, one row per pair, with a big emoji. The ELI5 workhorse."""
    th = theme(ep)
    pairs = b.get("pairs", [])[:3]
    css = f'''    #an2-chip {{ position: absolute; left: 80px; top: 300px; }}
    #an2-h {{ position: absolute; left: 80px; right: 80px; top: 380px; font-size: 70px; }}
    .an2-r {{ position: absolute; left: 60px; right: 60px; height: 190px; display: flex; align-items: center; gap: 22px; background: #ffffff; border: 5px solid #111827; border-radius: 26px; box-shadow: 8px 8px 0 {th["accent"]}; padding: 0 26px; }}
    .an2-r .e {{ flex: none; width: 120px; height: 120px; }}
    .an2-r .l {{ flex: 1; font-family: "Inter"; font-weight: 800; font-size: 46px; color: #111827; line-height: 1.1; }}
    .an2-r .eq {{ font-family: "Archivo Black"; font-size: 64px; color: {th["rule"]}; }}
    .an2-r .m {{ flex: 1; text-align: right; font-family: "Archivo Black"; font-size: 50px; color: {th["rule"]}; line-height: 1.05; }}'''
    rows = "\n".join(
        f'    <div id="an2-r{k}" class="an2-r" style="top: {560 + k * 220}px">{emoji_img(p.get("icon", "💡"), "e")}<div class="l">{esc(p["thing"])}</div><div class="eq">=</div><div class="m">{esc(p["maps"])}</div></div>'
        for k, p in enumerate(pairs))
    body = f'''    <div id="an2-chip">{chip("THINK OF IT LIKE…", th)}</div>
    <div id="an2-h" class="k-h">{esc(b.get("text", ""))}</div>
{rows}'''
    js = ['      tl.fromTo("#an2-h", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.25, ease: "power3.out" }, 0.05);']
    for k in range(len(pairs)):
        at = 0.35 + (dur * 0.55) * k / max(1, len(pairs))
        js.append(f'      tl.fromTo("#an2-r{k}", {{ opacity: 0, x: {-900 if k % 2 == 0 else 900}, rotation: {-3 if k % 2 == 0 else 3} }}, {{ opacity: 1, x: 0, rotation: 0, duration: 0.4, ease: "back.out(1.4)" }}, {at:.2f});')
        js.append(f'      tl.fromTo("#an2-r{k} .e", {{ scale: 0.3 }}, {{ scale: 1, duration: 0.35, ease: "back.out(2.5)" }}, {at + 0.15:.2f});')
    return scene(cid, dur, css, body, "\n".join(js))


def _options(b, th, prefix, reveal=False):
    out = []
    for k, opt in enumerate(b.get("options", [])[:4]):
        letter = "ABCD"[k]
        right = reveal and letter == b.get("correct")
        bg = "#16a34a" if right else "#ffffff"
        ink = "#ffffff" if right else "#111827"
        out.append(f'    <div id="{prefix}{k}" class="q-o" style="top: {640 + k * 116}px; background: {bg}; color: {ink};"><b style="background:{"#ffffff" if right else th["accent"]};color:{"#16a34a" if right else th["accent_ink"]}">{letter}</b><span>{esc(opt)}</span></div>')
    return "\n".join(out)


Q_CSS = '''    .q-o { position: absolute; left: 70px; right: 70px; height: 100px; display: flex; align-items: center; gap: 26px; border: 4px solid #111827; border-radius: 20px; padding: 0 24px; font-family: "Inter"; font-weight: 800; font-size: 46px; }
    .q-o b { flex: none; width: 70px; height: 70px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-family: "Archivo Black"; font-weight: 400; font-size: 40px; }'''


def beat_question(scene, cid, b, dur, ep):
    th = theme(ep)
    css = f'''    #qq-chip {{ position: absolute; left: 80px; top: 300px; }}
    #qq-q {{ position: absolute; left: 80px; right: 80px; top: 380px; font-size: 60px; line-height: 1.12; }}
{Q_CSS}'''
    body = f'''    <div id="qq-chip">{chip(b.get("tag", "EXAM QUESTION"), th)}</div>
    <div id="qq-q" class="k-h">{esc(b["question"])}</div>
{_options(b, th, "qq-o")}'''
    js = ['      tl.fromTo("#qq-q", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }, 0.05);']
    for k in range(len(b.get("options", [])[:4])):
        js.append(f'      tl.fromTo("#qq-o{k}", {{ opacity: 0, x: 80 }}, {{ opacity: 1, x: 0, duration: 0.25, ease: "power3.out" }}, {dur * (0.45 + 0.1 * k):.2f});')
    return scene(cid, dur, css, body, "\n".join(js))


def beat_countdown(scene, cid, b, dur, ep):
    th = theme(ep)
    n = 3
    css = f'''    #cd-t {{ position: absolute; left: 0; right: 0; top: 340px; text-align: center; font-size: 66px; }}
    .cd-n {{ position: absolute; left: 0; right: 0; top: 520px; text-align: center; font-family: "Archivo Black"; font-size: 420px; line-height: 1; color: {th["rule"]}; opacity: 0; }}
    #cd-ring {{ position: absolute; left: 290px; top: 470px; width: 500px; height: 500px; }}
    #cd-sub {{ position: absolute; left: 80px; right: 80px; top: 1030px; text-align: center; font-size: 46px; }}'''
    nums = "\n".join(f'    <div id="cd-n{k}" class="cd-n">{n - k}</div>' for k in range(n))
    body = f'''    <div id="cd-t" class="k-h">{esc(b.get("text", "Lock your answer!"))}</div>
    <svg id="cd-ring" viewBox="0 0 100 100"><circle cx="50" cy="50" r="44" fill="none" stroke="#e5e7eb" stroke-width="7"/><circle id="cd-arc" cx="50" cy="50" r="44" fill="none" stroke="{th["accent"]}" stroke-width="7" stroke-linecap="round" transform="rotate(-90 50 50)" pathLength="1" stroke-dasharray="1"/></svg>
{nums}
    <div id="cd-sub" class="k-b">{esc(b.get("sub", "Comment A, B, C or D ↓").replace("👇", "↓"))}</div>'''
    step = (dur - 0.3) / n
    js = [f'      tl.fromTo("#cd-arc", {{ strokeDashoffset: 0 }}, {{ strokeDashoffset: 1, duration: {dur - 0.3:.2f}, ease: "none" }}, 0.1);']
    for k in range(n):
        js.append(f'      tl.fromTo("#cd-n{k}", {{ opacity: 1, scale: 1.4 }}, {{ opacity: 1, scale: 1, duration: 0.25, ease: "power4.out", immediateRender: false }}, {0.1 + k * step:.2f});')
        js.append(f'      tl.to("#cd-n{k}", {{ opacity: 0, duration: 0.1 }}, {0.1 + (k + 1) * step - 0.1:.2f});')
    return scene(cid, dur, css, body, "\n".join(js))


def beat_reveal(scene, cid, b, dur, ep):
    th = theme(ep)
    css = f'''    #rv-chip {{ position: absolute; left: 80px; top: 300px; }}
    #rv-q {{ position: absolute; left: 80px; right: 80px; top: 380px; font-size: 48px; line-height: 1.12; opacity: 0.55; }}
    #rv-stamp {{ position: absolute; right: 70px; top: 520px; font-family: "Archivo Black"; font-size: 60px; color: #16a34a; border: 8px solid #16a34a; border-radius: 18px; padding: 4px 22px; transform: rotate(-8deg); background: #ffffff; }}
{Q_CSS}'''
    body = f'''    <div id="rv-chip">{chip("ANSWER", th)}</div>
    <div id="rv-q" class="k-h">{esc(b["question"])}</div>
{_options(b, th, "rv-o", reveal=True)}
    <div id="rv-stamp">{esc(b.get("correct", "?"))} ✓</div>'''
    k = "ABCD".index(b.get("correct", "A"))
    js = f'''      tl.fromTo("#rv-o{k}", {{ scale: 1 }}, {{ keyframes: [{{ scale: 1.06, duration: 0.15 }}, {{ scale: 1, duration: 0.2 }}] }}, 0.15);
      tl.fromTo("#rv-stamp", {{ scale: 3, opacity: 0, rotation: -25 }}, {{ scale: 1, opacity: 1, rotation: -8, duration: 0.3, ease: "power4.out" }}, 0.35);'''
    return scene(cid, dur, css, body, js)


def beat_verdict(scene, cid, b, dur, ep):
    th = theme(ep)
    ok = str(b.get("verdict", "false")).lower() == "true"
    col = "#16a34a" if ok else "#e11d48"
    css = f'''    #vd-chip {{ position: absolute; left: 80px; top: 300px; }}
    #vd-claim {{ position: absolute; left: 80px; right: 80px; top: 390px; font-size: 64px; line-height: 1.1; }}
    #vd-stamp {{ position: absolute; left: 160px; top: 690px; width: 760px; text-align: center; font-family: "Archivo Black"; font-size: 170px; color: {col}; border: 14px solid {col}; border-radius: 30px; transform: rotate(-7deg); background: #ffffff; }}
    #vd-why {{ position: absolute; left: 80px; right: 80px; top: 1015px; text-align: center; font-size: 48px; }}'''
    body = f'''    <div id="vd-chip">{chip("THE CLAIM", th)}</div>
    <div id="vd-claim" class="k-h">“{esc(b["claim"])}”</div>
    <div id="vd-stamp">{"TRUE" if ok else "FALSE"}</div>
    <div id="vd-why" class="k-b">{esc(b.get("text", ""))}</div>'''
    js = f'''      tl.fromTo("#vd-claim", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25 }}, 0.05);
      tl.fromTo("#vd-stamp", {{ scale: 3.5, opacity: 0, rotation: 15 }}, {{ scale: 1, opacity: 1, rotation: -7, duration: 0.3, ease: "power4.out" }}, {min(1.4, dur * 0.4):.2f});
      tl.fromTo("#vd-why", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.25 }}, {min(2.0, dur * 0.6):.2f});'''
    return scene(cid, dur, css, body, js)


def beat_wrong(scene, cid, b, dur, ep, eq, eq_box):
    """A wrong method, struck through in red — the 'common mistake' beat."""
    w, h = eq_box(None, eq["aspect"], 900, 260) if eq else (0, 0)
    eq_html = f'<img id="wr-eq" class="k-eq" src="assets/eq/{eq["out"].replace(chr(92), "/").split("/")[-1]}" alt="" />' if eq else ""
    css = f'''    #wr-chip {{ position: absolute; left: 80px; top: 300px; }}
    #wr-t {{ position: absolute; left: 80px; right: 80px; top: 380px; font-size: 60px; }}
    #wr-eq {{ position: absolute; left: {(1080 - w) // 2}px; top: {600 + (260 - h) // 2}px; width: {w}px; height: {h}px; opacity: 0.8; }}
    #wr-x {{ position: absolute; left: 90px; top: 560px; width: 900px; height: 340px; }}
    #wr-why {{ position: absolute; left: 80px; right: 80px; top: 960px; font-size: 50px; color: #be123c; }}'''
    body = f'''    <div id="wr-chip"><div class="k-chip" style="background:#e11d48;color:#fff">✗ WRONG WAY</div></div>
    <div id="wr-t" class="k-h">{esc(b.get("text", ""))}</div>
    {eq_html}
    <svg id="wr-x" viewBox="0 0 900 340"><path id="wr-l1" d="M40 40 L860 300" stroke="#e11d48" stroke-width="22" stroke-linecap="round" pathLength="1" stroke-dasharray="1"/><path id="wr-l2" d="M860 40 L40 300" stroke="#e11d48" stroke-width="22" stroke-linecap="round" pathLength="1" stroke-dasharray="1"/></svg>
    <div id="wr-why" class="k-b">{esc(b.get("why", ""))}</div>'''
    js = f'''      tl.fromTo("#wr-t", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25 }}, 0.05);
      tl.fromTo("#wr-l1", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 0.2, ease: "power2.in" }}, {dur * 0.45:.2f});
      tl.fromTo("#wr-l2", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 0.2, ease: "power2.in" }}, {dur * 0.45 + 0.15:.2f});
      tl.fromTo("#wr-why", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.25 }}, {dur * 0.55:.2f});'''
    return scene(cid, dur, css, body, js)
