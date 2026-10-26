"""G. Dai — G. Robotics' synthetic AI news presenter (an original character, never a real person; always labelled).

Head-and-shoulders anchor in a navy suit, drawn as soft-shaded vector art. Lip-sync picks a viseme per letter group
across each word's spoken time; blinks, small head moves and a brow lift on questions keep him alive.
svg() -> markup;  js(words, total) -> GSAP lines for the root timeline (words = [{"w","s","e"}] in video time).
"""
import re

SKIN, SKIN_SH, HAIR, SUIT, SUIT_HI, TIE = "#c68b62", "#a8714d", "#14100e", "#101a33", "#1d2b52", "#22d3ee"

MOUTHS = {
    "rest": ("M182 247 Q200 253 218 247", "none"),
    "closed": ("M180 248 Q200 250 220 248", "none"),
    "wide": ("M178 243 Q200 263 222 243 Q200 250 178 243 Z", "#5b1a1d"),
    "open": ("M185 240 Q200 270 215 240 Q200 236 185 240 Z", "#5b1a1d"),
    "round": ("M192 240 Q200 233 208 240 Q213 253 200 259 Q187 253 192 240 Z", "#5b1a1d"),
    "teeth": ("M181 243 L219 243 Q216 255 200 256 Q184 255 181 243 Z", "#f4f1ea"),
}
GROUPS = [("mbp", "closed"), ("fv", "teeth"), ("ouwq", "round"), ("aeiy", "wide")]


def _shape(ch):
    for letters, shape in GROUPS:
        if ch in letters:
            return shape
    return "open" if ch.isalpha() else None


def svg():
    mouths = "".join(
        f'<path id="gd-m-{k}" class="gd-m" d="{d}" fill="{f}" stroke="#7a3b33" stroke-width="3" stroke-linecap="round" '
        f'stroke-linejoin="round" opacity="{1 if k == "rest" else 0}"/>' for k, (d, f) in MOUTHS.items())
    return f'''<svg id="gd" viewBox="0 0 400 480" aria-hidden="true">
  <defs>
    <radialGradient id="gd-skin" cx="45%" cy="38%" r="70%"><stop offset="0" stop-color="#d79c72"/><stop offset="0.7" stop-color="{SKIN}"/><stop offset="1" stop-color="{SKIN_SH}"/></radialGradient>
    <linearGradient id="gd-suit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SUIT_HI}"/><stop offset="1" stop-color="{SUIT}"/></linearGradient>
    <linearGradient id="gd-hair" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2b211c"/><stop offset="1" stop-color="{HAIR}"/></linearGradient>
    <linearGradient id="gd-tie" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5eead4"/><stop offset="1" stop-color="#0891b2"/></linearGradient>
  </defs>
  <g id="gd-body">
    <path d="M40 480 C44 392 92 352 150 338 L250 338 C308 352 356 392 360 480 Z" fill="url(#gd-suit)"/>
    <path d="M168 336 L200 420 L232 336 Z" fill="#eef2f7"/>
    <path d="M190 346 L210 346 L216 360 L206 452 L200 462 L194 452 L184 360 Z" fill="url(#gd-tie)"/>
    <path d="M190 346 L210 346 L205 360 L195 360 Z" fill="#0e7490"/>
    <path d="M150 338 L200 470 L170 480 L120 362 Z" fill="#0b1328" opacity="0.85"/>
    <path d="M250 338 L200 470 L230 480 L280 362 Z" fill="#0b1328" opacity="0.85"/>
    <path d="M150 338 L176 336 L200 420 Z" fill="#dfe6ef"/><path d="M250 338 L224 336 L200 420 Z" fill="#dfe6ef"/>
    <circle cx="292" cy="392" r="8" fill="#f5c451"/>
  </g>
  <g id="gd-head">
    <path d="M176 300 L176 344 Q200 356 224 344 L224 300 Z" fill="{SKIN_SH}"/>
    <ellipse cx="124" cy="196" rx="13" ry="22" fill="{SKIN_SH}"/><ellipse cx="276" cy="196" rx="13" ry="22" fill="{SKIN_SH}"/>
    <path d="M126 170 C126 108 160 84 200 84 C240 84 274 108 274 170 C274 236 252 300 200 306 C148 300 126 236 126 170 Z" fill="url(#gd-skin)"/>
    <path d="M140 246 C150 286 176 304 200 306 C224 304 250 286 260 246 C246 270 226 284 200 286 C174 284 154 270 140 246 Z" fill="#3a2a22" opacity="0.18"/>
    <path d="M122 168 C114 98 162 62 210 66 C258 68 290 104 278 168 C272 140 262 122 246 112 C222 122 172 120 150 112 C136 124 128 142 122 168 Z" fill="url(#gd-hair)"/>
    <path d="M150 112 C170 94 214 90 246 112 C226 104 196 102 168 110 Z" fill="#3d3029" opacity="0.6"/>
    <g id="gd-brows"><path d="M156 160 Q172 150 188 158 M212 158 Q228 150 244 160" fill="none" stroke="#1d1512" stroke-width="7" stroke-linecap="round"/></g>
    <ellipse cx="172" cy="184" rx="13" ry="8" fill="#fbf8f3"/><ellipse cx="228" cy="184" rx="13" ry="8" fill="#fbf8f3"/>
    <circle cx="173" cy="184" r="6.5" fill="#3b2416"/><circle cx="229" cy="184" r="6.5" fill="#3b2416"/>
    <circle cx="175" cy="182" r="2" fill="#fff"/><circle cx="231" cy="182" r="2" fill="#fff"/>
    <rect class="gd-lid" x="157" y="174" width="30" height="20" rx="8" fill="{SKIN}"/>
    <rect class="gd-lid" x="213" y="174" width="30" height="20" rx="8" fill="{SKIN}"/>
    <path d="M158 178 Q172 172 187 178 M213 178 Q228 172 242 178" fill="none" stroke="#5a3a2a" stroke-width="2.5" stroke-linecap="round"/>
    <path d="M200 192 Q194 214 190 222 Q200 228 210 222" fill="none" stroke="{SKIN_SH}" stroke-width="3.5" stroke-linecap="round"/>
    {mouths}
  </g>
</svg>'''


CSS = '''#gd-head, #gd-brows { transform-box: fill-box; }
#gd-head { transform-origin: 50% 95%; }
#gd-brows { transform-origin: 50% 100%; }
.gd-lid { transform-box: fill-box; transform-origin: 50% 0%; }'''


def js(words, total, start=0.0):
    out = ['tl.set(".gd-lid", { scaleY: 0 }, 0);',
           f'tl.fromTo("#gd-head", {{ rotation: -1.6 }}, {{ rotation: 1.6, duration: 2.2, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(total / 2.2) - 1)} }}, {start:.2f});']

    def show(shape, t):
        out.append(f'tl.set(".gd-m", {{ opacity: 0 }}, {t:.3f}); tl.set("#gd-m-{shape}", {{ opacity: 1 }}, {t:.3f});')

    for w in words:
        shapes = []
        for c in re.sub(r"[^a-z]", "", w["w"].lower()):
            s = _shape(c)
            if s and (not shapes or shapes[-1] != s):
                shapes.append(s)
        shapes = shapes[:4] or ["open"]
        dur = max(0.08, w["e"] - w["s"])
        for k, s in enumerate(shapes):
            show(s, w["s"] + dur * k / len(shapes))
        show("rest", w["e"])
        if w["w"].endswith("?") or w["w"].endswith("!"):
            out.append(f'tl.to("#gd-brows", {{ y: -5, duration: 0.12, yoyo: true, repeat: 1, repeatDelay: 0.45 }}, {w["s"]:.3f});')
    t = start + 1.7
    while t < total - 0.4:
        out.append(f'tl.to(".gd-lid", {{ scaleY: 1, duration: 0.06, yoyo: true, repeat: 1 }}, {t:.2f});')
        t += 3.1 if int(t * 10) % 2 else 2.6
    return "\n".join(out)
