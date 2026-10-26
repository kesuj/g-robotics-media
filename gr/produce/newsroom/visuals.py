"""Motion-graphic kits for the story panel (940×560 SVG). Pure vector + GSAP, deterministic, no stock imagery.

kit(name, p, t0, d) -> (svg_markup, js_lines). `p` is a unique id prefix, t0/d the story's start and length.
Names: drs, ai, chip, space, drone, robot, phone, nepal, globe, ev, app, cyber, money.
"""
import json
import math
from pathlib import Path

NEPAL = json.loads((Path(__file__).parent / "assets" / "nepal.json").read_text(encoding="utf8"))
C1, C2, GOLD, RED, INK = "#22d3ee", "#a78bfa", "#f5c451", "#ff3b5c", "#e6edf7"


def _wrap(p, inner):
    return (f'<svg id="{p}" class="kit" viewBox="0 0 940 560" aria-hidden="true">'
            f'<defs><radialGradient id="{p}-glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{C1}" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="{C1}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="{p}-g1" x1="0" x2="1"><stop offset="0" stop-color="{C1}"/><stop offset="1" stop-color="{C2}"/></linearGradient></defs>'
            f'<circle cx="470" cy="280" r="300" fill="url(#{p}-glow)"/>{inner}</svg>')


def _draw(sel, t, dur=0.9, ease="power2.inOut"):
    return f'tl.fromTo("{sel}", {{ strokeDashoffset: 1600 }}, {{ strokeDashoffset: 0, duration: {dur}, ease: "{ease}" }}, {t:.2f});'


def drs(p, t0, d):
    # broadcast-style ball tracking: pitch in perspective, ball path, impact markers, stumps, verdict
    inner = f'''<path d="M330 540 L610 540 L540 120 L400 120 Z" fill="#1f3b2a" stroke="#3f7d55" stroke-width="3"/>
<path d="M352 470 L588 470 M392 200 L548 200" stroke="#e6edf7" stroke-width="3" opacity="0.7"/>
<g id="{p}-stumps"><rect x="452" y="88" width="8" height="70" rx="3" fill="{INK}"/><rect x="466" y="88" width="8" height="70" rx="3" fill="{INK}"/><rect x="480" y="88" width="8" height="70" rx="3" fill="{INK}"/>
<rect x="450" y="84" width="40" height="6" rx="3" fill="{GOLD}"/></g>
<path id="{p}-path" d="M420 560 C440 430 452 330 462 300 C470 260 468 200 470 130" fill="none" stroke="{GOLD}" stroke-width="16" stroke-linecap="round" stroke-dasharray="1600" opacity="0.9"/>
<circle id="{p}-pitch" cx="462" cy="300" r="20" fill="none" stroke="{C1}" stroke-width="6"/>
<circle id="{p}-impact" cx="468" cy="210" r="20" fill="none" stroke="{C2}" stroke-width="6"/>
<circle id="{p}-ball" cx="470" cy="130" r="14" fill="{RED}"/>
<g id="{p}-tags" font-family="Outfit" font-weight="800" font-size="26" letter-spacing="2">
<g id="{p}-t1"><rect x="560" y="280" width="250" height="52" rx="10" fill="#0b1328" stroke="{C1}" stroke-width="2"/><text x="580" y="315" fill="{C1}">PITCHING · IN LINE</text></g>
<g id="{p}-t2"><rect x="560" y="190" width="250" height="52" rx="10" fill="#0b1328" stroke="{C2}" stroke-width="2"/><text x="580" y="225" fill="{C2}">IMPACT · IN LINE</text></g>
<g id="{p}-t3"><rect x="560" y="100" width="250" height="52" rx="10" fill="{RED}"/><text x="580" y="135" fill="#fff">WICKETS · HITTING</text></g></g>
<text x="70" y="250" font-family="Space Mono" font-weight="700" font-size="22" fill="{C1}">3D BALL</text><text x="70" y="282" font-family="Space Mono" font-weight="700" font-size="22" fill="{C1}">TRACKING</text>
<text x="70" y="350" font-family="Space Mono" font-weight="700" font-size="22" fill="{C2}">EDGE</text><text x="70" y="382" font-family="Space Mono" font-weight="700" font-size="22" fill="{C2}">DETECTION</text>'''
    js = [_draw(f"#{p}-path", t0 + 0.4, 1.4, "power1.in"),
          f'tl.from("#{p}-pitch", {{ scale: 0, transformOrigin: "50% 50%", duration: 0.35, ease: "back.out(2)" }}, {t0 + 1.0:.2f});',
          f'tl.from("#{p}-impact", {{ scale: 0, transformOrigin: "50% 50%", duration: 0.35, ease: "back.out(2)" }}, {t0 + 1.4:.2f});',
          f'tl.from("#{p}-ball", {{ scale: 0, transformOrigin: "50% 50%", duration: 0.3 }}, {t0 + 1.75:.2f});',
          f'tl.from("#{p}-stumps", {{ y: -8, duration: 0.25, ease: "power3.out" }}, {t0 + 1.8:.2f});']
    for i, tt in enumerate((1.1, 1.5, 2.0)):
        js.append(f'tl.from("#{p}-t{i + 1}", {{ x: 60, opacity: 0, duration: 0.35, ease: "power3.out" }}, {t0 + tt:.2f});')
    js.append(f'tl.to("#{p}-t3", {{ opacity: 0.55, duration: 0.25, yoyo: true, repeat: 5 }}, {t0 + 2.5:.2f});')
    return _wrap(p, inner), js


def ai(p, t0, d):
    layers = [[(250, 140 + 140 * i) for i in range(3)], [(470, 90 + 95 * i) for i in range(5)], [(690, 210 + 140 * i) for i in range(2)]]
    lines, nodes = [], []
    for a, b in zip(layers, layers[1:]):
        for x1, y1 in a:
            for x2, y2 in b:
                lines.append(f'<path class="{p}-ln" d="M{x1} {y1} L{x2} {y2}" stroke="url(#{p}-g1)" stroke-width="2.5" opacity="0.55" stroke-dasharray="1600"/>')
    for L in layers:
        for x, y in L:
            nodes.append(f'<circle class="{p}-nd" cx="{x}" cy="{y}" r="22" fill="#0b1328" stroke="{C1}" stroke-width="5"/>')
    inner = "".join(lines) + "".join(nodes) + f'<text x="790" y="290" font-family="Outfit" font-weight="800" font-size="72" fill="{GOLD}" id="{p}-ai">AI</text>'
    js = [f'tl.fromTo(".{p}-ln", {{ strokeDashoffset: 1600 }}, {{ strokeDashoffset: 0, duration: 1.2, stagger: 0.02, ease: "power2.out" }}, {t0 + 0.3:.2f});',
          f'tl.from(".{p}-nd", {{ scale: 0, transformOrigin: "50% 50%", duration: 0.4, stagger: 0.05, ease: "back.out(2)" }}, {t0 + 0.2:.2f});',
          f'tl.to(".{p}-nd", {{ fill: "{C1}", duration: 0.25, stagger: {{ each: 0.12, repeat: {max(1, int(d / 2))}, yoyo: true }} }}, {t0 + 1.4:.2f});',
          f'tl.from("#{p}-ai", {{ opacity: 0, x: 30, duration: 0.5 }}, {t0 + 1.2:.2f});']
    return _wrap(p, inner), js


def chip(p, t0, d):
    traces = []
    for i in range(6):
        y = 150 + i * 52
        traces.append(f'<path class="{p}-tr" d="M120 {y} L260 {y} L300 {y + 20} L370 {y + 20}" fill="none" stroke="{C1}" stroke-width="4" stroke-dasharray="1600"/>')
        traces.append(f'<path class="{p}-tr" d="M820 {y} L680 {y} L640 {y - 20} L570 {y - 20}" fill="none" stroke="{C2}" stroke-width="4" stroke-dasharray="1600"/>')
    pins = "".join(f'<rect x="{392 + i * 30}" y="96" width="12" height="40" rx="3" fill="{GOLD}"/><rect x="{392 + i * 30}" y="424" width="12" height="40" rx="3" fill="{GOLD}"/>' for i in range(6))
    inner = "".join(traces) + pins + f'''<rect id="{p}-die" x="370" y="130" width="200" height="300" rx="18" fill="#0f172a" stroke="url(#{p}-g1)" stroke-width="6"/>
<rect x="400" y="170" width="140" height="220" rx="10" fill="none" stroke="{C1}" stroke-width="2" opacity="0.5"/>
<text x="470" y="300" text-anchor="middle" font-family="Space Mono" font-size="34" font-weight="700" fill="{INK}">CHIP</text>'''
    js = [f'tl.from("#{p}-die", {{ scale: 0.6, opacity: 0, transformOrigin: "50% 50%", duration: 0.6, ease: "back.out(1.6)" }}, {t0 + 0.2:.2f});',
          f'tl.fromTo(".{p}-tr", {{ strokeDashoffset: 1600 }}, {{ strokeDashoffset: 0, duration: 1.1, stagger: 0.06, ease: "power2.out" }}, {t0 + 0.6:.2f});',
          f'tl.to(".{p}-tr", {{ opacity: 0.35, duration: 0.3, stagger: {{ each: 0.08, repeat: {max(1, int(d / 1.5))}, yoyo: true }} }}, {t0 + 1.8:.2f});']
    return _wrap(p, inner), js


def space(p, t0, d):
    stars = "".join(f'<circle cx="{(i * 137) % 900 + 20}" cy="{(i * 71) % 520 + 20}" r="{1.5 + (i % 3)}" fill="#fff" opacity="{0.3 + (i % 5) / 10}"/>' for i in range(40))
    inner = stars + f'''<circle cx="330" cy="330" r="130" fill="#1e3a8a"/><path d="M220 290 C280 260 360 330 440 300" stroke="{C1}" stroke-width="10" fill="none" opacity="0.5"/>
<ellipse cx="330" cy="330" rx="230" ry="60" fill="none" stroke="{GOLD}" stroke-width="4" opacity="0.7" transform="rotate(-18 330 330)"/>
<path id="{p}-arc" d="M300 520 C420 420 560 260 760 90" fill="none" stroke="{C1}" stroke-width="5" stroke-dasharray="1600" stroke-linecap="round"/>
<g id="{p}-rk"><path d="M0 -34 C14 -18 14 18 10 30 L-10 30 C-14 18 -14 -18 0 -34 Z" fill="{INK}"/><path d="M-10 18 L-22 34 L-10 30 Z M10 18 L22 34 L10 30 Z" fill="{RED}"/>
<path d="M-7 32 L0 58 L7 32 Z" fill="{GOLD}"/></g>'''
    js = [_draw(f"#{p}-arc", t0 + 0.3, 2.2, "power1.inOut"),
          f'tl.fromTo("#{p}-rk", {{ x: 300, y: 520, rotation: 40 }}, {{ x: 760, y: 90, rotation: 52, duration: 2.2, ease: "power1.inOut" }}, {t0 + 0.3:.2f});']
    return _wrap(p, inner), js


def drone(p, t0, d):
    grid = "".join(f'<path d="M{100 + i * 74} 40 L{100 + i * 74} 520" stroke="{C1}" stroke-width="1" opacity="0.18"/>' for i in range(11)) + \
        "".join(f'<path d="M100 {40 + i * 60} L840 {40 + i * 60}" stroke="{C1}" stroke-width="1" opacity="0.18"/>' for i in range(9))
    props = "".join(f'<g class="{p}-pr" transform="translate({x} {y})"><circle r="58" fill="none" stroke="{C1}" stroke-width="3" opacity="0.4"/>'
                    f'<path d="M-52 0 L52 0" stroke="{INK}" stroke-width="7" stroke-linecap="round"/></g>' for x, y in ((360, 170), (580, 170), (360, 390), (580, 390)))
    inner = grid + f'''<g id="{p}-dr"><path d="M360 170 L580 390 M580 170 L360 390" stroke="#334155" stroke-width="18" stroke-linecap="round"/>
<rect x="420" y="230" width="100" height="100" rx="22" fill="#0f172a" stroke="url(#{p}-g1)" stroke-width="5"/><circle cx="470" cy="280" r="16" fill="{RED}"/>{props}</g>
<rect id="{p}-scan" x="100" y="40" width="740" height="8" fill="{C1}" opacity="0.55"/>'''
    js = [f'tl.from("#{p}-dr", {{ scale: 0.4, opacity: 0, transformOrigin: "50% 50%", duration: 0.7, ease: "back.out(1.5)" }}, {t0 + 0.2:.2f});',
          f'tl.to(".{p}-pr path", {{ rotation: {int(d * 900)}, transformOrigin: "50% 50%", duration: {d:.2f}, ease: "none" }}, {t0:.2f});',
          f'tl.fromTo("#{p}-scan", {{ y: 0 }}, {{ y: 470, duration: 1.6, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(d / 1.6))} }}, {t0 + 0.5:.2f});',
          f'tl.to("#{p}-dr", {{ y: -14, duration: 1.2, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(d / 1.2))} }}, {t0 + 0.9:.2f});']
    return _wrap(p, inner), js


def robot(p, t0, d):
    inner = f'''<rect x="300" y="470" width="200" height="40" rx="10" fill="#334155"/>
<g id="{p}-a1" transform="translate(400 470)"><rect x="-22" y="-200" width="44" height="200" rx="20" fill="#1e293b" stroke="{C1}" stroke-width="4"/>
<g id="{p}-a2" transform="translate(0 -190)"><circle r="26" fill="{GOLD}"/><rect x="-18" y="-170" width="36" height="170" rx="16" fill="#1e293b" stroke="{C2}" stroke-width="4"/>
<g transform="translate(0 -170)"><circle r="18" fill="{GOLD}"/><path d="M-26 -10 L-40 -50 M26 -10 L40 -50" stroke="{INK}" stroke-width="10" stroke-linecap="round"/></g></g></g>
<rect id="{p}-box" x="600" y="400" width="110" height="80" rx="10" fill="{C1}" opacity="0.9"/>'''
    js = [f'tl.fromTo("#{p}-a1", {{ rotation: -25 }}, {{ rotation: 18, transformOrigin: "50% 100%", svgOrigin: "400 470", duration: 1.4, ease: "power2.inOut", yoyo: true, repeat: {max(1, int(d / 1.4))} }}, {t0 + 0.2:.2f});',
          f'tl.fromTo("#{p}-a2", {{ rotation: 30 }}, {{ rotation: -35, svgOrigin: "400 280", duration: 1.4, ease: "power2.inOut", yoyo: true, repeat: {max(1, int(d / 1.4))} }}, {t0 + 0.2:.2f});',
          f'tl.from("#{p}-box", {{ y: -200, opacity: 0, duration: 0.6, ease: "bounce.out" }}, {t0 + 0.5:.2f});']
    return _wrap(p, inner), js


def phone(p, t0, d):
    bars = "".join(f'<rect class="{p}-ui" x="405" y="{150 + i * 64}" width="{130 - (i % 3) * 25}" height="40" rx="10" fill="{[C1, C2, GOLD][i % 3]}" opacity="0.85"/>' for i in range(5))
    inner = f'''<rect id="{p}-ph" x="370" y="60" width="200" height="440" rx="36" fill="#0f172a" stroke="url(#{p}-g1)" stroke-width="7"/>
<rect x="440" y="78" width="60" height="12" rx="6" fill="#334155"/>{bars}
<circle id="{p}-ring" cx="470" cy="280" r="250" fill="none" stroke="{C1}" stroke-width="3" opacity="0.4"/>'''
    js = [f'tl.from("#{p}-ph", {{ y: 80, rotation: -8, opacity: 0, transformOrigin: "50% 50%", duration: 0.7, ease: "power3.out" }}, {t0 + 0.2:.2f});',
          f'tl.from(".{p}-ui", {{ scaleX: 0, transformOrigin: "0% 50%", duration: 0.45, stagger: 0.12, ease: "power3.out" }}, {t0 + 0.7:.2f});',
          f'tl.fromTo("#{p}-ring", {{ scale: 0.4, opacity: 0.7 }}, {{ scale: 1.1, opacity: 0, transformOrigin: "50% 50%", duration: 1.6, ease: "power1.out", repeat: {max(1, int(d / 1.6))} }}, {t0 + 0.8:.2f});']
    return _wrap(p, inner), js


def nepal(p, t0, d):
    bw, bh = NEPAL["nepalBox"]
    s = min(800 / bw, 420 / bh)
    tx, ty = 470 - bw * s / 2, 290 - bh * s / 2
    kx, ky = NEPAL["ktmDot"]
    inner = f'''<g transform="translate({tx:.1f} {ty:.1f}) scale({s:.3f})">
<path id="{p}-np" d="{NEPAL["nepal"]}" fill="#13203f" stroke="{GOLD}" stroke-width="{3 / s:.2f}" stroke-dasharray="4000" stroke-linejoin="round"/>
<circle id="{p}-pulse" cx="{kx}" cy="{ky}" r="{18 / s:.1f}" fill="none" stroke="{RED}" stroke-width="{4 / s:.2f}"/>
<circle cx="{kx}" cy="{ky}" r="{9 / s:.1f}" fill="{RED}"/></g>
<text x="470" y="535" text-anchor="middle" font-family="Space Mono" font-size="24" fill="{INK}" opacity="0.75">NEPAL</text>'''
    js = [f'tl.fromTo("#{p}-np", {{ strokeDashoffset: 4000 }}, {{ strokeDashoffset: 0, duration: 1.6, ease: "power2.inOut" }}, {t0 + 0.2:.2f});',
          f'tl.from("#{p}-np", {{ fillOpacity: 0, duration: 0.8 }}, {t0 + 1.2:.2f});',
          f'tl.fromTo("#{p}-pulse", {{ scale: 0.5, opacity: 1 }}, {{ scale: 3, opacity: 0, transformOrigin: "50% 50%", duration: 1.3, ease: "power1.out", repeat: {max(1, int(d / 1.3))} }}, {t0 + 1.4:.2f});']
    return _wrap(p, inner), js


def globe(p, t0, d):
    mer = "".join(f'<ellipse class="{p}-m" cx="470" cy="280" rx="{abs(220 * math.cos(math.radians(a))):.1f}" ry="220" fill="none" stroke="{C1}" stroke-width="2.5" opacity="0.6"/>' for a in range(0, 180, 30))
    par = "".join(f'<ellipse cx="470" cy="{280 + y}" rx="{math.sqrt(max(0, 220 ** 2 - y ** 2)):.1f}" ry="{18 * (1 - abs(y) / 230):.1f}" fill="none" stroke="{C2}" stroke-width="2" opacity="0.5"/>' for y in (-150, -75, 0, 75, 150))
    inner = f'<circle cx="470" cy="280" r="220" fill="#0b1735" stroke="url(#{p}-g1)" stroke-width="5"/>' + f'<g id="{p}-gl">{mer}</g>' + par + \
        "".join(f'<circle class="{p}-pt" cx="{x}" cy="{y}" r="9" fill="{GOLD}"/>' for x, y in ((380, 200), (560, 230), (470, 330), (610, 360), (330, 360)))
    js = [f'tl.from("#{p}-gl", {{ scaleX: 0.2, transformOrigin: "50% 50%", duration: 0.9, ease: "power3.out" }}, {t0 + 0.2:.2f});',
          f'tl.to(".{p}-m", {{ attr: {{ rx: 200 }}, duration: 2.4, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(d / 2.4))}, stagger: 0.1 }}, {t0 + 1:.2f});',
          f'tl.from(".{p}-pt", {{ scale: 0, transformOrigin: "50% 50%", duration: 0.35, stagger: 0.18, ease: "back.out(3)" }}, {t0 + 0.9:.2f});']
    return _wrap(p, inner), js


def ev(p, t0, d):
    inner = f'''<rect x="260" y="170" width="400" height="220" rx="30" fill="#0f172a" stroke="url(#{p}-g1)" stroke-width="7"/>
<rect x="660" y="235" width="34" height="90" rx="8" fill="{C1}"/>
<rect id="{p}-fill" x="280" y="190" width="360" height="180" rx="18" fill="{C1}" opacity="0.85"/>
<path d="M480 205 L430 290 L470 290 L450 360 L520 260 L478 260 L500 205 Z" fill="{GOLD}"/>'''
    js = [f'tl.fromTo("#{p}-fill", {{ scaleX: 0.05 }}, {{ scaleX: 1, transformOrigin: "0% 50%", duration: 2.2, ease: "power2.out" }}, {t0 + 0.3:.2f});']
    return _wrap(p, inner), js


def app(p, t0, d):
    cards = "".join(f'<g class="{p}-c" transform="translate({180 + i * 200} {150 + (i % 2) * 60})"><rect width="170" height="230" rx="24" fill="#0f172a" stroke="{[C1, C2, GOLD, RED][i]}" stroke-width="5"/>'
                    f'<rect x="24" y="30" width="60" height="60" rx="16" fill="{[C1, C2, GOLD, RED][i]}"/><rect x="24" y="120" width="120" height="14" rx="7" fill="#334155"/>'
                    f'<rect x="24" y="150" width="90" height="14" rx="7" fill="#334155"/></g>' for i in range(3))
    js = [f'tl.from(".{p}-c", {{ y: 120, opacity: 0, duration: 0.6, stagger: 0.15, ease: "power3.out" }}, {t0 + 0.2:.2f});',
          f'tl.to(".{p}-c", {{ y: "-=16", duration: 1.3, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(d / 1.3))}, stagger: 0.2 }}, {t0 + 1.2:.2f});']
    return _wrap(p, cards), js


def cyber(p, t0, d):
    inner = f'''<path id="{p}-sh" d="M470 70 L640 130 L640 280 C640 380 560 450 470 490 C380 450 300 380 300 280 L300 130 Z" fill="#0f172a" stroke="url(#{p}-g1)" stroke-width="7" stroke-dasharray="1600"/>
<rect x="420" y="260" width="100" height="90" rx="14" fill="{GOLD}"/><path d="M440 262 L440 230 C440 196 500 196 500 230 L500 262" fill="none" stroke="{GOLD}" stroke-width="14"/>'''
    js = [_draw(f"#{p}-sh", t0 + 0.2, 1.3)]
    return _wrap(p, inner), js


KITS = {"drs": drs, "cricket": drs, "ai": ai, "chip": chip, "space": space, "drone": drone, "robot": robot, "phone": phone,
        "gadget": phone, "nepal": nepal, "globe": globe, "ev": ev, "energy": ev, "app": app, "startup": app, "cyber": cyber,
        "internet": globe}


def kit(name, p, t0, d):
    return KITS.get(name, globe)(p, t0, d)
