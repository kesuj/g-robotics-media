"""Code-drawn AI presenters — a free, unlimited avatar option (no GPU, no paid API).

Original characters (not real people), always labelled "AI PRESENTER". Lip-sync uses visemes picked from the
letters of each word spread across the word's spoken time; eyebrows lift on questions, the hand gestures on
emphasis (numbers, "!"), blinks every few seconds, a gentle idle sway.

Episode field: "presenter": "aarav" | "maya" | "dai"   (replaces the small mascot in the captions scene)
parts(words, total, persona) -> (css, html, js); words = [{"w", "s", "e"}] in video time.
Colours use off-by-one hexes so style skins leave the characters alone.
"""
import re

PERSONAS = {
    "aarav": {"name": "AARAV", "skin": "#c98e63", "hair": "#1b1411", "top": "#1e3a8b", "trim": "#ffd401", "glasses": True,
              "hair_path": "M44 96 C40 40 160 34 158 92 C150 70 126 62 100 64 C76 64 56 72 44 96 Z"},
    "maya": {"name": "MAYA", "skin": "#b97a54", "hair": "#2a1810", "top": "#0f7f7b", "trim": "#f6c445", "glasses": False,
             "hair_path": "M40 118 C30 40 170 36 160 118 C162 70 140 56 100 58 C60 56 40 72 40 118 Z M38 110 C30 170 50 200 56 206 L60 120 Z M162 110 C170 170 150 200 144 206 L140 120 Z",
             "earrings": True},
    "dai": {"name": "BIJULI DAI", "skin": "#f2c79c", "hair": "#ffd401", "top": "#2563ec", "trim": "#ffd401", "glasses": False,
            "hair_path": "M38 82 C40 34 160 34 162 82 Z", "hardhat": True},
}

# viseme groups → mouth path (in a 200×250 head space, centred at 100,148)
MOUTHS = {
    "rest": "M84 148 Q100 154 116 148",
    "closed": "M82 148 L118 148",
    "wide": "M80 142 Q100 162 120 142 Q100 150 80 142 Z",
    "open": "M84 140 Q100 168 116 140 Q100 136 84 140 Z",
    "round": "M92 140 Q100 132 108 140 Q112 152 100 158 Q88 152 92 140 Z",
    "teeth": "M82 144 L118 144 L116 152 L84 152 Z",
}
SHAPE_OF = [("mbp", "closed"), ("fv", "teeth"), ("ouw", "round"), ("aei", "wide"), ("", "open")]


def _shape(ch):
    ch = ch.lower()
    for letters, shape in SHAPE_OF:
        if letters and ch in letters:
            return shape
    return "open" if ch.isalpha() else None


def _svg(p):
    hair = f'<path d="{p["hair_path"]}" fill="{p["hair"]}" stroke="#111828" stroke-width="5" stroke-linejoin="round"/>'
    hat = ('<rect x="28" y="78" width="144" height="14" rx="7" fill="#ffd401" stroke="#111828" stroke-width="5"/>'
           '<rect x="92" y="40" width="16" height="40" rx="5" fill="#f5b801" stroke="#111828" stroke-width="4"/>') if p.get("hardhat") else ""
    glasses = ('<g fill="none" stroke="#111828" stroke-width="4"><rect x="62" y="102" width="32" height="22" rx="8"/>'
               '<rect x="106" y="102" width="32" height="22" rx="8"/><path d="M94 112 H106"/></g>') if p.get("glasses") else ""
    ear = ('<circle cx="46" cy="138" r="5" fill="#f6c445" stroke="#111828" stroke-width="2"/>'
           '<circle cx="154" cy="138" r="5" fill="#f6c445" stroke="#111828" stroke-width="2"/>') if p.get("earrings") else ""
    mouths = "".join(f'<path id="pr-m-{k}" class="pr-m" d="{d}" fill="#7f1d1e" stroke="#111828" stroke-width="4" '
                     f'stroke-linejoin="round" opacity="{1 if k == "rest" else 0}"/>' for k, d in MOUTHS.items())
    return f'''    <svg id="pr" viewBox="0 0 260 300" aria-hidden="true">
      <g id="pr-body">
        <path d="M48 300 C48 230 76 214 120 214 C164 214 192 230 192 300 Z" fill="{p["top"]}" stroke="#111828" stroke-width="5"/>
        <path d="M120 222 L108 250 H122 L114 276 L136 240 H122 L130 222 Z" fill="{p["trim"]}" stroke="#111828" stroke-width="3" stroke-linejoin="round"/>
        <g id="pr-arm"><path d="M186 250 C214 236 226 206 220 184" fill="none" stroke="{p["top"]}" stroke-width="22" stroke-linecap="round"/>
          <path d="M186 250 C214 236 226 206 220 184" fill="none" stroke="#111828" stroke-width="3" stroke-linecap="round" opacity="0.35"/>
          <circle cx="220" cy="178" r="14" fill="{p["skin"]}" stroke="#111828" stroke-width="4"/></g>
      </g>
      <g id="pr-head" transform="translate(20 0)">
        <rect x="86" y="160" width="28" height="30" fill="{p["skin"]}" stroke="#111828" stroke-width="5"/>
        <circle cx="47" cy="120" r="11" fill="{p["skin"]}" stroke="#111828" stroke-width="5"/>
        <circle cx="153" cy="120" r="11" fill="{p["skin"]}" stroke="#111828" stroke-width="5"/>
        <circle cx="100" cy="114" r="56" fill="{p["skin"]}" stroke="#111828" stroke-width="5"/>
        {hair}{hat}{ear}
        <g id="pr-brows"><path d="M64 96 Q78 88 90 96 M110 96 Q122 88 136 96" fill="none" stroke="#111828" stroke-width="5" stroke-linecap="round"/></g>
        <circle cx="78" cy="114" r="7" fill="#111828"/><circle cx="122" cy="114" r="7" fill="#111828"/>
        <rect class="pr-lid" x="66" y="104" width="24" height="20" fill="{p["skin"]}"/>
        <rect class="pr-lid" x="110" y="104" width="24" height="20" fill="{p["skin"]}"/>
        {glasses}
        <path d="M100 118 Q96 132 104 134" fill="none" stroke="#111828" stroke-width="3" stroke-linecap="round"/>
        {mouths}
      </g>
    </svg>
    <div id="pr-tag">AI PRESENTER · {p["name"]}</div>'''


CSS = '''    #pr { position: absolute; left: 10px; top: 1300px; width: 330px; height: 381px; transform-origin: 40% 100%; }
    #pr-tag { position: absolute; left: 30px; top: 1684px; width: 290px; text-align: center; font-family: "Archivo Black"; font-size: 20px; letter-spacing: 0.06em; color: #111828; background: #ffd401; border: 3px solid #111828; border-radius: 10px; padding: 3px 0; }
    #pr-head, #pr-arm, #pr-brows { transform-box: fill-box; }
    #pr-head { transform-origin: 50% 90%; }
    #pr-arm { transform-origin: 0% 100%; }
    #pr-brows { transform-origin: 50% 100%; }
    .pr-lid { transform-box: fill-box; transform-origin: 50% 0%; }'''


def parts(words, total, persona="aarav"):
    p = PERSONAS.get(persona, PERSONAS["aarav"])
    js = ['      tl.set(".pr-lid", { scaleY: 0 }, 0);',
          '      tl.set("#pr-arm", { rotation: -75 }, 0);',   # resting: arm down at the side
          '      tl.fromTo("#pr", { y: 420, rotation: -6 }, { y: 0, rotation: 0, duration: 0.55, ease: "back.out(1.6)" }, 0.1);',
          f'      tl.fromTo("#pr-head", {{ rotation: -2 }}, {{ rotation: 2, duration: 1.6, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(total / 1.6) - 1)} }}, 0.7);']

    def show(shape, t):
        js.append(f'      tl.set(".pr-m", {{ opacity: 0 }}, {t:.3f});')
        js.append(f'      tl.set("#pr-m-{shape}", {{ opacity: 1 }}, {t:.3f});')

    last_end = 0
    for w in words:
        letters = [c for c in re.sub(r"[^A-Za-z]", "", w["w"])]
        shapes = []
        for c in letters:
            s = _shape(c)
            if s and (not shapes or shapes[-1] != s):
                shapes.append(s)
        shapes = shapes[:4] or ["open"]
        dur = max(0.08, w["e"] - w["s"])
        for k, s in enumerate(shapes):
            show(s, w["s"] + dur * k / len(shapes))
        show("rest", w["e"])
        if w["w"].endswith("?"):
            js.append(f'      tl.to("#pr-brows", {{ y: -6, duration: 0.12, yoyo: true, repeat: 1, repeatDelay: 0.5 }}, {w["s"]:.3f});')
        if re.search(r"\d|!$", w["w"]) and w["s"] - last_end > 1.2:
            js.append(f'      tl.fromTo("#pr-arm", {{ rotation: -75 }}, {{ rotation: 0, duration: 0.22, ease: "power2.out", yoyo: true, repeat: 1, repeatDelay: 0.5 }}, {w["s"]:.3f});')
            last_end = w["s"]
    t = 2.1
    while t < total - 0.5:
        js.append(f'      tl.to(".pr-lid", {{ scaleY: 1, duration: 0.06, yoyo: true, repeat: 1 }}, {t:.2f});')
        t += 3.3 if int(t * 10) % 2 else 2.7
    return CSS, _svg(p), "\n".join(js)
