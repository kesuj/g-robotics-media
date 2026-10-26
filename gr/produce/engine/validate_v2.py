"""Validator for Daily EE v2 episodes (ep031+), plus the legacy check for ep001-ep030.

v2 checks: keys, id/slug/filename, format rotation, beat recipe per format, every beat's
fields and hard text limits, single-emoji icons, no digits / raw symbols / AC-DC-EMF tokens
in VO, MCQ options/correct letter, question == reveal, balanced LaTeX braces, closed
circuits, total VO words 120-180, outro text, AEEE syllabus code.

Legacy: copies engine/validate_episodes.py (byte-for-byte, unmodified) and ep001-ep030 +
INDEX.md into a temp tree and runs it there, because that script expects exactly 30 files.
"""
import glob, json, os, re, shutil, subprocess, sys, tempfile, unicodedata
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "episodes")
ELEM = {"SourceV","SourceSin","Battery","Resistor","Capacitor","Inductor","Lamp","Switch","Fuse","Diode",
        "LED","Ground","Line","Dot","Motor","Transformer","Meter_V","Meter_A","Heater"}
DIRS = {"up", "down", "left", "right"}
ROTATION = ["explain", "mcq", "eli5", "myth", "mistake", "mcq"]
OUTRO_VO, OUTRO_TEXT = "Follow for one license-exam concept every day.", "Daily EE"
# Sub-chapter codes exactly as printed in the NEC AEEE syllabus (Ghq9etVLdy220920011235.pdf)
AEEE_CODES = {
    "AExE0101": 1, "AExE0102": 1, "AExE0103": 1, "AElE0104": 1, "AEEE0105": 1, "AEEE0106": 1,
    **{f"AEEE020{i}": 2 for i in range(1, 7)},
    "AExE0201": 3, "AExE0202": 3, "AExE0203": 3, "AExE0204": 3, "AExE0205": 3, "AEEE0306": 3,
    **{f"AEEE040{i}": 4 for i in range(1, 7)},
    "AElE0401": 5, **{f"AEEE050{i}": 5 for i in range(2, 7)},
    **{f"AEEE060{i}": 6 for i in range(1, 7)},
    **{f"AEEE070{i}": 7 for i in range(1, 7)},
    **{f"AEEE080{i}": 8 for i in range(1, 7)},
    **{f"AEEE090{i}": 9 for i in range(1, 7)},
    **{f"AALL100{i}": 10 for i in range(1, 7)},
}
RECIPES = {
    "explain": r"hook analogy concept (diagram )?formula given (step ){2,3}answer tip outro",
    "mcq":     r"hook question countdown reveal analogy (formula )?(step ){0,4}tip outro",
    "eli5":    r"hook analogy concept formula given step answer outro",
    "myth":    r"hook verdict analogy concept (formula )?tip outro",
    "mistake": r"hook wrong concept given (step ){1,3}answer tip outro",
}
FIELDS = {
    "hook": {"vo", "text"}, "analogy": {"vo", "text", "pairs"}, "concept": {"vo", "text", "points"},
    "diagram": {"vo", "caption", "circuit"}, "formula": {"vo", "latex", "terms"},
    "given": {"vo", "items", "find"}, "step": {"vo", "latex"}, "answer": {"vo", "latex", "note"},
    "tip": {"vo", "text"}, "question": {"vo", "question", "options", "correct"},
    "countdown": {"vo", "text", "sub"}, "reveal": {"vo", "question", "options", "correct"},
    "verdict": {"vo", "claim", "verdict", "text"}, "wrong": {"vo", "text", "latex", "why"},
    "outro": {"vo", "text"},
}
OPTIONAL = {"question": {"tag"}}
W = lambda s: len(s.split())
VO_BAD_TOKENS = re.compile(r"\b(AC|DC|EMF|RMS|NPV|IRR|ADC|BJT|FIR|IIR|SNR|MUX)\b")
VO_BAD_CHARS = set("%Ω°µ×÷=+/^_\\{}<>≈√πΦφηθ≥≤→·")


def braces_ok(s):
    s2 = s.replace("\\{", "").replace("\\}", ""); d = 0
    for c in s2:
        d += (c == "{") - (c == "}")
        if d < 0: return False
    return d == 0 and len(re.findall(r"\\left(?![a-zA-Z])", s)) == len(re.findall(r"\\right(?![a-zA-Z])", s))


def is_emoji_cp(c):
    o = ord(c)
    return (0x1F000 <= o <= 0x1FAFF) or (0x2190 <= o <= 0x2BFF) or o in (0x3030, 0x303D, 0x3297, 0x3299)


def single_emoji(s):
    core = [c for c in s if ord(c) != 0xFE0F]
    return len(core) == 1 and is_emoji_cp(core[0])


def has_emoji(s):
    return any(is_emoji_cp(c) for c in s)


def check_v2(fp, expected_id):
    errs = []
    name = os.path.basename(fp)
    try:
        e = json.load(open(fp, encoding="utf-8"))
    except Exception as ex:
        return [f"JSON: {ex}"], 0, None
    if set(e) != {"id", "slug", "format", "title", "category", "syllabus", "beats"}:
        errs.append(f"keys {sorted(e)}")
        return errs, 0, e
    if e["id"] != expected_id or name != f"{e['id']}-{e['slug']}.json":
        errs.append("id/slug/filename mismatch")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", e["slug"]): errs.append("slug format")
    n = int(e["id"][2:])
    if e["format"] != ROTATION[(n - 31) % 6]: errs.append(f"format {e['format']} breaks rotation (want {ROTATION[(n - 31) % 6]})")
    if len(e["title"]) > 48: errs.append(f"title {len(e['title'])} chars")
    if not e["category"] or W(e["category"]) > 2: errs.append("category")
    m = re.match(r"(\w{8}) — \S", e["syllabus"])
    if not m or m.group(1) not in AEEE_CODES: errs.append(f"syllabus code not in AEEE list: {e['syllabus']!r}")
    b = e["beats"]
    types = " ".join(x.get("type", "?") for x in b)
    if e["format"] in RECIPES and not re.fullmatch(RECIPES[e["format"]], types):
        errs.append(f"beat order for {e['format']}: {types}")
    if types.split().count("step") > 4: errs.append("more than 4 steps")
    qbeat = rbeat = None
    for x in b:
        t = x.get("type")
        if t not in FIELDS: errs.append(f"unknown beat type {t}"); continue
        extra = set(x) - {"type"} - FIELDS[t] - OPTIONAL.get(t, set())
        missing = FIELDS[t] - set(x)
        if missing or extra: errs.append(f"{t}: missing {sorted(missing)} extra {sorted(extra)}"); continue
        vo = x["vo"]
        if not isinstance(vo, str) or not vo.strip(): errs.append(f"{t}: empty vo")
        if re.search(r"\d", vo): errs.append(f"{t}: digits in vo")
        if VO_BAD_TOKENS.search(vo): errs.append(f"{t}: unspelled acronym in vo {VO_BAD_TOKENS.findall(vo)}")
        bad = sorted({c for c in vo if c in VO_BAD_CHARS})
        if bad: errs.append(f"{t}: symbols in vo {bad}")
        if "latex" in x and (not x["latex"] or not braces_ok(x["latex"])): errs.append(f"{t}: bad/unbalanced latex")
        if t == "hook" and W(x["text"]) > 7: errs.append("hook text >7 words")
        if t == "analogy":
            if W(x["text"]) > 8: errs.append("analogy text >8 words")
            p = x["pairs"]
            need = (3, 3) if e["format"] == "eli5" else (1, 3)
            if not (isinstance(p, list) and need[0] <= len(p) <= need[1]): errs.append(f"analogy pairs count {len(p)}")
            for pr in p:
                if set(pr) != {"icon", "thing", "maps"}: errs.append(f"pair keys {sorted(pr)}"); continue
                if not single_emoji(pr["icon"]): errs.append(f"icon not single emoji {pr['icon']!r}")
                if W(pr["thing"]) > 6: errs.append(f"pair thing >6 words: {pr['thing']}")
                if W(pr["maps"]) > 3: errs.append(f"pair maps >3 words: {pr['maps']}")
        if t == "concept":
            if W(x["text"]) > 10: errs.append("concept text >10 words")
            if not 2 <= len(x["points"]) <= 3 or any(W(pt) > 6 for pt in x["points"]): errs.append("concept points")
        if t == "diagram":
            if W(x["caption"]) > 8: errs.append("caption >8 words")
            c = x["circuit"]
            if not 4 <= len(c) <= 9: errs.append("circuit length")
            ok = all(isinstance(el, list) and len(el) == 3 and el[0] in ELEM and el[1] in DIRS and isinstance(el[2], str) for el in c)
            if not ok: errs.append("bad circuit element")
            else:
                dx = sum({"right": 1, "left": -1}.get(el[1], 0) for el in c if el[0] not in ("Dot", "Ground"))
                dy = sum({"up": 1, "down": -1}.get(el[1], 0) for el in c if el[0] not in ("Dot", "Ground"))
                if dx or dy: errs.append(f"circuit loop not closed dx={dx} dy={dy}")
        if t == "formula":
            if not x["terms"] or len(x["terms"]) > 4 or any(set(tm) != {"sym", "meaning"} for tm in x["terms"]): errs.append("formula terms")
        if t == "given":
            if not x["items"] or len(x["items"]) > 5 or any(set(it) != {"sym", "value"} for it in x["items"]): errs.append("given items")
            if not x["find"] or W(x["find"]) > 8: errs.append("given find >8 words")
        if t == "answer" and W(x["note"]) > 8: errs.append("answer note >8 words")
        if t == "tip" and W(x["text"]) > 16: errs.append("tip text >16 words")
        if t in ("question", "reveal"):
            if len(x["question"]) > 90: errs.append(f"{t} question {len(x['question'])} chars")
            o = x["options"]
            if not (isinstance(o, list) and len(o) == 4) or any(not s or len(s) > 32 for s in o) or len(set(o)) != 4:
                errs.append(f"{t} options")
            if x["correct"] not in ("A", "B", "C", "D"): errs.append(f"{t} correct letter")
            if t == "question": qbeat = x
            else: rbeat = x
        if t == "countdown":
            if W(x["text"]) > 4: errs.append("countdown text >4 words")
            if len(x["sub"]) > 28 or has_emoji(x["sub"]): errs.append("countdown sub")
        if t == "verdict":
            if len(x["claim"]) > 60: errs.append(f"verdict claim {len(x['claim'])} chars")
            if x["verdict"] not in ("true", "false"): errs.append("verdict value")
            if W(x["text"]) > 12: errs.append("verdict text >12 words")
        if t == "wrong":
            if W(x["text"]) > 10: errs.append("wrong text >10 words")
            if W(x["why"]) > 12: errs.append("wrong why >12 words")
        if t == "outro" and (vo != OUTRO_VO or x["text"] != OUTRO_TEXT): errs.append("outro")
    if qbeat and rbeat and any(qbeat[k] != rbeat[k] for k in ("question", "options", "correct")):
        errs.append("reveal does not match question")
    wc = sum(W(x.get("vo", "")) for x in b)
    if not 120 <= wc <= 180: errs.append(f"VO words {wc} (need 120-180)")
    return errs, wc, e


def main():
    print("=== v2 episodes (ep031+) ===")
    files = sorted(f for f in glob.glob(os.path.join(D, "ep*.json")) if int(os.path.basename(f)[2:5]) >= 31)
    fails, wcs, letters, chapters, formats, slugs = 0, [], Counter(), Counter(), Counter(), Counter()
    for i, fp in enumerate(files, 31):
        errs, wc, e = check_v2(fp, f"ep{i:03d}")
        wcs.append(wc)
        if e and isinstance(e, dict) and "format" in e:
            formats[e["format"]] += 1; slugs[e.get("slug")] += 1
            code = e.get("syllabus", "")[:8]
            chapters[AEEE_CODES.get(code, "?")] += 1
            for x in e.get("beats", []):
                if x.get("type") == "question": letters[x.get("correct")] += 1
        fails += bool(errs)
        print(f"{'PASS' if not errs else 'FAIL'} {os.path.basename(fp):40s} vo={wc:3d}" + ("" if not errs else "  -> " + "; ".join(errs)))
    dup = [s for s, c in slugs.items() if c > 1]
    if dup: print("FAIL duplicate slugs:", dup); fails += 1
    if wcs: print(f"\nv2: {len(files) - fails}/{len(files)} passed; VO words min={min(wcs)} max={max(wcs)} avg={sum(wcs) / len(wcs):.0f}")
    print("formats:", dict(formats))
    print("MCQ correct letters:", dict(sorted(letters.items())))
    print("episodes per AEEE chapter:", dict(sorted(chapters.items(), key=lambda kv: str(kv[0]).zfill(2))))
    if letters and max(letters.values()) - min(letters.get(k, 0) for k in "ABCD") > 2:
        print("FAIL MCQ letters unbalanced"); fails += 1
    if "?" in chapters or len([k for k in chapters if k != "?"]) < 10:
        print("FAIL not all 10 chapters covered"); fails += 1

    print("\n=== legacy validator (engine/validate_episodes.py, unmodified) on ep001-ep030 ===")
    tmp = tempfile.mkdtemp(prefix="eedaily_legacy_")
    try:
        os.makedirs(os.path.join(tmp, "engine")); os.makedirs(os.path.join(tmp, "episodes"))
        shutil.copy2(os.path.join(ROOT, "engine", "validate_episodes.py"), os.path.join(tmp, "engine"))
        for fp in sorted(glob.glob(os.path.join(D, "ep*.json"))):
            if int(os.path.basename(fp)[2:5]) <= 30: shutil.copy2(fp, os.path.join(tmp, "episodes"))
        shutil.copy2(os.path.join(D, "INDEX.md"), os.path.join(tmp, "episodes"))
        r = subprocess.run([sys.executable, os.path.join(tmp, "engine", "validate_episodes.py")],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout.rstrip()); print(r.stderr.rstrip()) if r.stderr.strip() else None
        print("legacy exit code:", r.returncode)
        legacy_fail = r.returncode != 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok = not fails and not legacy_fail
    print("\nOVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
