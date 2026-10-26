"""Visual styles (skins) for Daily EE, independent of the content format.

A style recolours and re-fonts every generated scene: build.py writes scenes with the classic
colours/fonts, then skin() swaps them for the style's. Episodes pick a style with "style": "<name>",
otherwise it rotates by episode number so consecutive videos never look alike.
"""
import re
import zlib

# ink = text/lines on the ground, card = boxes that hold ink text, hi = highlight fill,
# onhi = ink on a highlight fill, rule = secondary accent, soft = faint highlight band, line = dividers/tracks
STYLES = {
    "classic": {"ground": None, "ink": "#111827", "card": "#ffffff", "hi": "#ffd400", "onhi": "#111827", "rule": "#b45309",
                "soft": "#fff7c2", "line": "#c9d4e3", "cool": "#2563eb", "head": '"Archivo Black"', "headw": 400, "body": '"Inter"'},
    "blueprint": {"ground": "background-color: #0d3b8c; background-image: linear-gradient(rgba(255,255,255,0.16) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.16) 2px, transparent 2px), linear-gradient(rgba(255,255,255,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.07) 1px, transparent 1px); background-size: 120px 120px, 120px 120px, 24px 24px, 24px 24px;",
                  "ink": "#eef4ff", "card": "#11479f", "hi": "#ffd84d", "onhi": "#0b1f44", "rule": "#7dd3fc",
                  "soft": "rgba(255,216,77,0.16)", "line": "#4a7bd0", "cool": "#93c5fd", "head": '"JetBrains Mono"', "headw": 800, "body": '"IBM Plex Mono"'},
    "chalkboard": {"ground": "background-color: #1f3a2e; background-image: radial-gradient(ellipse at 30% 20%, rgba(255,255,255,0.08), transparent 60%), radial-gradient(ellipse at 80% 85%, rgba(255,255,255,0.06), transparent 55%), repeating-linear-gradient(115deg, rgba(255,255,255,0.025) 0 3px, transparent 3px 9px); box-shadow: inset 0 0 0 26px #6b4423, inset 0 0 0 32px #4a2e17;",
                   "ink": "#f4f1e8", "card": "#2a4a3b", "hi": "#ffe066", "onhi": "#1f2a22", "rule": "#ff9f7a",
                   "soft": "rgba(255,224,102,0.14)", "line": "#5d7f6e", "cool": "#9ad1ff", "head": '"Oswald"', "headw": 700, "body": '"Nunito"'},
    "neon": {"ground": "background-color: #0a0a14; background-image: radial-gradient(circle at 15% 10%, rgba(34,211,238,0.22), transparent 45%), radial-gradient(circle at 90% 90%, rgba(244,114,182,0.22), transparent 45%), linear-gradient(rgba(167,139,250,0.08) 2px, transparent 2px), linear-gradient(90deg, rgba(167,139,250,0.08) 2px, transparent 2px); background-size: auto, auto, 80px 80px, 80px 80px;",
             "ink": "#f5f7ff", "card": "#161629", "hi": "#22d3ee", "onhi": "#031018", "rule": "#f472b6",
             "soft": "rgba(34,211,238,0.14)", "line": "#34345a", "cool": "#a78bfa", "head": '"Montserrat"', "headw": 900, "body": '"Inter"'},
    "notebook": {"ground": "background-color: #fffdf6; background-image: linear-gradient(90deg, transparent 118px, #f87171 118px, #f87171 122px, transparent 122px), repeating-linear-gradient(#fffdf6 0 58px, #bfdbfe 58px 60px);",
                 "ink": "#1e293b", "card": "#ffffff", "hi": "#86efac", "onhi": "#052e16", "rule": "#dc2626",
                 "soft": "#fef9c3", "line": "#cbd5e1", "cool": "#2563eb", "head": '"Poppins"', "headw": 800, "body": '"Nunito"'},
    "newsroom": {"ground": "background-color: #f4efe6; background-image: repeating-linear-gradient(0deg, rgba(0,0,0,0.035) 0 1px, transparent 1px 6px);",
                 "ink": "#1a1a1a", "card": "#fffaf0", "hi": "#ff5a36", "onhi": "#ffffff", "rule": "#b91c1c",
                 "soft": "#ffe8de", "line": "#d6cfc2", "cool": "#1d4ed8", "head": '"Playfair Display"', "headw": 900, "body": '"Inter"'},
    "sunset": {"ground": "background-color: #2b1055; background-image: linear-gradient(180deg, #2b1055 0%, #7b2869 55%, #d1495b 100%);",
               "ink": "#fff7ed", "card": "#3b1a66", "hi": "#ffb703", "onhi": "#2b1055", "rule": "#ffd6a5",
               "soft": "rgba(255,183,3,0.16)", "line": "#8a4b9c", "cool": "#bde0fe", "head": '"Outfit"', "headw": 900, "body": '"Outfit"'},
}

ROTATION = ["classic", "blueprint", "neon", "notebook", "chalkboard", "sunset"]
DARK = {"blueprint", "chalkboard", "neon", "sunset"}


# lanes with their own look rotate through a shorter list
FORMAT_ROTATION = {"news": ["newsroom", "neon", "newsroom", "blueprint"], "people": ["sunset", "newsroom", "neon", "chalkboard"],
                   "clip": ["neon", "notebook", "sunset", "blueprint", "chalkboard"]}


def pick(ep):
    if ep.get("style") in STYLES:
        return ep["style"]
    n = re.sub(r"\D", "", ep.get("id", "")) or str(zlib.crc32(ep.get("id", "").encode()))
    rot = FORMAT_ROTATION.get(ep.get("format"), ROTATION)
    return rot[int(n) % len(rot)]


def rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def skin(src, name):
    """Swap the classic palette and fonts in a generated scene for style `name`."""
    s = STYLES[name]
    src = src.replace("@ONHI@", s["onhi"]).replace("@COOL@", s["cool"]).replace("@CARD@", s["card"])
    if name == "classic":
        return src
    r, g, b = rgb(s["hi"])
    src = re.sub(r"rgba\(255,\s*212,\s*0,\s*([\d.]+)\)", lambda m: f"rgba({r},{g},{b},{m.group(1)})", src)
    src = re.sub(r"background:\s*#ffffff", f"background: {s['card']}", src)
    for old, new in (("#111827", s["ink"]), ("#ffd400", s["hi"]), ("#b45309", s["rule"]), ("#B45309", s["rule"]),
                     ("#fff7c2", s["soft"]), ("#c9d4e3", s["line"]), ("#e5e7eb", s["line"])):
        src = src.replace(old, new)
    src = re.sub(r'font-family:\s*"Archivo Black"(;\s*font-weight:\s*400)?', f"font-family: {s['head']}; font-weight: {s['headw']}", src)
    src = src.replace('"Inter"', s["body"])
    return src


def base(name):
    """Plain page colour behind everything (the ground's background-color)."""
    g = STYLES[name]["ground"] or "background-color: #ffffff;"
    m = re.search(r"background-color:\s*(#[0-9a-fA-F]{6})", g)
    return m.group(1) if m else "#ffffff"
