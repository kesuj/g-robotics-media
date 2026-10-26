"""Beat types for the news, people and quick-clip lanes (imported by build.py).

headline · stat · quote · timeline · profile. Written in the classic palette; styles.skin() recolours them.
"""
import html

from beats_v2 import chip, emoji_img, theme

esc = html.escape


def beat_headline(scene, cid, b, dur, ep):
    """Breaking-news card: tag + date, the headline word by word, source line, scrolling ticker."""
    th = theme(ep)
    words = " ".join(f'<span class="w">{esc(w)}</span>' for w in b.get("text", "").split())
    ticker = esc(b.get("ticker", ep.get("title", "")).upper())
    css = f'''    #hl-chip {{ position: absolute; left: 80px; top: 300px; }}
    #hl-date {{ position: absolute; right: 80px; top: 310px; font-family: "Inter"; font-weight: 800; font-size: 34px; color: #b45309; }}
    #hl-h {{ position: absolute; left: 80px; right: 80px; top: 400px; font-size: 92px; line-height: 1.02; }}
    #hl-h .w {{ display: inline-block; }}
    #hl-src {{ position: absolute; left: 80px; right: 80px; top: 960px; font-size: 38px; opacity: 0.75; }}
    #hl-tk {{ position: absolute; left: 0; right: 0; top: 1060px; height: 76px; background: #111828; overflow: hidden; }}
    #hl-tk div {{ position: absolute; left: 0; top: 14px; white-space: nowrap; font-family: "Archivo Black"; font-size: 40px; color: #ffd400; }}'''
    body = f'''    <div id="hl-chip">{chip(b.get("tag", "BREAKING"), th)}</div>
    <div id="hl-date">{esc(b.get("date", ""))}</div>
    <div id="hl-h" class="k-h">{words}</div>
    <div id="hl-src" class="k-b">{esc(b.get("source", ""))}</div>
    <div id="hl-tk" data-layout-allow-overflow><div data-layout-allow-overflow>{(ticker + " ⚡ ") * 4}</div></div>'''
    js = f'''      tl.fromTo("#hl-chip", {{ scale: 0 }}, {{ scale: 1, duration: 0.3, ease: "back.out(2.5)" }}, 0.05);
      tl.fromTo("#hl-h .w", {{ opacity: 0, y: 50, rotationX: -70 }}, {{ opacity: 1, y: 0, rotationX: 0, duration: 0.3, ease: "power3.out", stagger: 0.06 }}, 0.2);
      tl.fromTo("#hl-src", {{ opacity: 0 }}, {{ opacity: 0.75, duration: 0.3 }}, {min(1.6, dur * 0.5):.2f});
      tl.fromTo("#hl-tk div", {{ x: 0 }}, {{ x: -1600, duration: {dur:.2f}, ease: "none" }}, 0);'''
    return scene(cid, dur, css, body, js)


def beat_stat(scene, cid, b, dur, ep):
    """One giant number that counts up, with what it means."""
    th = theme(ep)
    num = b.get("number", 0)
    dec = len(str(num).split(".")[1]) if "." in str(num) else 0
    shown = f'{b.get("prefix", "")}{float(num):,.{dec}f}{b.get("suffix", "")}'
    size = min(260, int(960 / (0.68 * max(1, len(shown)))))  # fit the final number on one line
    css = f'''    #sx-chip {{ position: absolute; left: 80px; top: 300px; }}
    #sx-n {{ position: absolute; left: 40px; right: 40px; top: 470px; text-align: center; font-family: "Archivo Black"; font-size: {size}px; line-height: 1; color: #b45309; white-space: nowrap; }}
    #sx-u {{ position: absolute; left: 80px; right: 80px; top: 760px; text-align: center; font-size: 70px; }}
    #sx-t {{ position: absolute; left: 80px; right: 80px; top: 900px; text-align: center; font-size: 50px; }}'''
    body = f'''    <div id="sx-chip">{chip(b.get("tag", "BY THE NUMBERS"), th)}</div>
    <div id="sx-n">{esc(b.get("prefix", ""))}<span id="sx-v">0</span>{esc(b.get("suffix", ""))}</div>
    <div id="sx-u" class="k-h">{esc(b.get("unit", ""))}</div>
    <div id="sx-t" class="k-b">{esc(b.get("text", ""))}</div>'''
    js = f'''      const c = {{ v: 0 }};
      tl.fromTo(c, {{ v: 0 }}, {{ v: {float(num)}, duration: {min(1.6, dur * 0.45):.2f}, ease: "power2.out", onUpdate: () => {{ document.querySelector("#sx-v").textContent = c.v.toLocaleString("en-US", {{ minimumFractionDigits: {dec}, maximumFractionDigits: {dec} }}); }} }}, 0.15);
      tl.fromTo("#sx-n", {{ scale: 0.6 }}, {{ scale: 1, duration: 0.5, ease: "back.out(1.6)" }}, 0.1);
      tl.fromTo("#sx-u", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.25 }}, 0.5);
      tl.fromTo("#sx-t", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.25 }}, {min(1.9, dur * 0.55):.2f});'''
    return scene(cid, dur, css, body, js)


def beat_quote(scene, cid, b, dur, ep):
    th = theme(ep)
    words = " ".join(f'<span class="w">{esc(w)}</span>' for w in b.get("quote", "").split())
    css = f'''    #qt-chip {{ position: absolute; left: 80px; top: 300px; }}
    #qt-mark {{ position: absolute; left: 60px; top: 330px; font-family: "Playfair Display"; font-weight: 900; font-size: 360px; line-height: 1; color: #ffd400; }}
    #qt-q {{ position: absolute; left: 100px; right: 80px; top: 520px; font-size: 70px; line-height: 1.12; }}
    #qt-by {{ position: absolute; left: 100px; right: 80px; top: 1010px; font-size: 44px; color: #b45309; }}'''
    body = f'''    <div id="qt-mark">“</div>
    <div id="qt-chip">{chip(b.get("tag", "IN THEIR WORDS"), th)}</div>
    <div id="qt-q" class="k-h">{words}</div>
    <div id="qt-by" class="k-b">— {esc(b.get("by", ""))}</div>'''
    js = f'''      tl.fromTo("#qt-mark", {{ scale: 0, rotation: -30 }}, {{ scale: 1, rotation: 0, duration: 0.4, ease: "back.out(2)" }}, 0.05);
      tl.fromTo("#qt-q .w", {{ opacity: 0.1 }}, {{ opacity: 1, duration: 0.1, stagger: {max(0.05, min(0.12, dur * 0.6 / max(1, len(b.get("quote", "").split())))):.3f} }}, 0.3);
      tl.fromTo("#qt-by", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.3 }}, {dur * 0.7:.2f});'''
    return scene(cid, dur, css, body, js)


def beat_timeline(scene, cid, b, dur, ep):
    th = theme(ep)
    ev = b.get("events", [])[:4]
    css = f'''    #tl-chip {{ position: absolute; left: 80px; top: 300px; }}
    #tl-line {{ position: absolute; left: 150px; top: 420px; width: 8px; height: {max(1, len(ev)) * 175}px; background: #c9d4e3; transform-origin: 50% 0; }}
    .tl-e {{ position: absolute; left: 120px; right: 70px; height: 160px; display: flex; gap: 34px; align-items: flex-start; }}
    .tl-e i {{ flex: none; width: 68px; height: 68px; border-radius: 50%; background: #ffd400; border: 6px solid #111827; }}
    .tl-e b {{ display: block; font-family: "Archivo Black"; font-weight: 400; font-size: 54px; color: #b45309; }}
    .tl-e span {{ display: block; font-family: "Inter"; font-weight: 700; font-size: 42px; color: #111827; line-height: 1.12; }}'''
    rows = "\n".join(f'    <div id="tl-e{k}" class="tl-e" style="top: {410 + k * 175}px"><i></i><div><b>{esc(str(e.get("year", "")))}</b><span>{esc(e.get("text", ""))}</span></div></div>' for k, e in enumerate(ev))
    body = f'''    <div id="tl-chip">{chip(b.get("tag", "TIMELINE"), th)}</div>
    <div id="tl-line"></div>
{rows}'''
    js = [f'      tl.fromTo("#tl-line", {{ scaleY: 0 }}, {{ scaleY: 1, duration: {dur * 0.7:.2f}, ease: "none" }}, 0.1);']
    for k in range(len(ev)):
        at = 0.15 + (dur * 0.65) * k / max(1, len(ev))
        js.append(f'      tl.fromTo("#tl-e{k} i", {{ scale: 0 }}, {{ scale: 1, duration: 0.3, ease: "back.out(3)" }}, {at:.2f});')
        js.append(f'      tl.fromTo("#tl-e{k} div", {{ opacity: 0, x: 50 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: "power3.out" }}, {at + 0.1:.2f});')
    return scene(cid, dur, css, body, "\n".join(js))


def beat_profile(scene, cid, b, dur, ep):
    """Person card: big emoji medallion (no photos), name, role, years, three 'known for' tags."""
    th = theme(ep)
    tags = b.get("known_for", [])[:3]
    css = f'''    #pf-chip {{ position: absolute; left: 80px; top: 300px; }}
    #pf-med {{ position: absolute; left: 340px; top: 390px; width: 400px; height: 400px; border-radius: 50%; background: #ffd400; border: 10px solid #111827; display: flex; align-items: center; justify-content: center; }}
    #pf-med .e {{ width: 230px; height: 230px; }}
    #pf-name {{ position: absolute; left: 60px; right: 60px; top: 820px; text-align: center; font-size: 84px; line-height: 1.02; }}
    #pf-role {{ position: absolute; left: 80px; right: 80px; top: 935px; text-align: center; font-size: 42px; color: #b45309; }}
    #pf-tags {{ position: absolute; left: 60px; right: 60px; top: 1010px; display: flex; flex-wrap: wrap; justify-content: center; gap: 14px; }}
    #pf-tags span {{ font-family: "Inter"; font-weight: 800; font-size: 34px; color: #111827; background: #ffffff; border: 4px solid #111827; border-radius: 40px; padding: 6px 22px; }}'''
    body = f'''    <div id="pf-chip">{chip(b.get("tag", "MEET THE MIND"), th)}</div>
    <div id="pf-med">{emoji_img(b.get("icon", "💡"), "e")}</div>
    <div id="pf-name" class="k-h">{esc(b.get("name", ""))}</div>
    <div id="pf-role" class="k-b">{esc(b.get("role", ""))}</div>
    <div id="pf-tags">{"".join(f"<span>{esc(t)}</span>" for t in tags)}</div>'''
    js = f'''      tl.fromTo("#pf-med", {{ scale: 0, rotation: -120 }}, {{ scale: 1, rotation: 0, duration: 0.55, ease: "back.out(1.6)" }}, 0.05);
      tl.fromTo("#pf-name", {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power3.out" }}, 0.4);
      tl.fromTo("#pf-role", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, 0.7);
      tl.fromTo("#pf-tags span", {{ opacity: 0, scale: 0.5 }}, {{ opacity: 1, scale: 1, duration: 0.25, ease: "back.out(2)", stagger: 0.15 }}, {min(1.4, dur * 0.4):.2f});'''
    return scene(cid, dur, css, body, js)


BEATS = {"headline": beat_headline, "stat": beat_stat, "quote": beat_quote, "timeline": beat_timeline, "profile": beat_profile}
