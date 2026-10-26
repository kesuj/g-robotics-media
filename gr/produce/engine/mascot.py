"""Bijuli Dai — the channel's code-drawn engineer mascot. Sits bottom-left and lip-syncs to the voiceover.

The SVG uses off-by-one colours (#111828…) so style skins leave the character's own colours alone.
parts(words, total) -> (css, html, js) to splice into the captions scene; words = [{"w", "s", "e"}] in video time.
"""

CSS = '''    #ms { position: absolute; left: 30px; top: 1365px; width: 270px; height: 337px; transform-origin: 50% 100%; }
    #ms-tag { position: absolute; left: 45px; top: 1705px; width: 240px; text-align: center; font-family: "Archivo Black"; font-size: 26px; letter-spacing: 0.06em; color: @ONHI@; background: #ffd400; border: 3px solid @ONHI@; border-radius: 10px; padding: 2px 0; }
    #ms-mouth { transform-box: fill-box; transform-origin: 50% 50%; }
    .ms-lid { transform-box: fill-box; transform-origin: 50% 0%; }'''

SVG = '''    <svg id="ms" viewBox="0 0 200 250" aria-hidden="true">
      <path d="M40 250 C40 196 66 178 100 178 C134 178 160 196 160 250 Z" fill="#2563ec" stroke="#111828" stroke-width="5"/>
      <path d="M100 196 L88 222 H102 L94 246 L116 214 H102 L110 196 Z" fill="#ffd401" stroke="#111828" stroke-width="3" stroke-linejoin="round"/>
      <rect x="86" y="160" width="28" height="24" fill="#f2c79b" stroke="#111828" stroke-width="5"/>
      <circle cx="100" cy="112" r="56" fill="#f2c79b" stroke="#111828" stroke-width="5"/>
      <circle cx="47" cy="116" r="11" fill="#f2c79b" stroke="#111828" stroke-width="5"/>
      <circle cx="153" cy="116" r="11" fill="#f2c79b" stroke="#111828" stroke-width="5"/>
      <path d="M38 82 C40 34 160 34 162 82 Z" fill="#ffd401" stroke="#111828" stroke-width="5" stroke-linejoin="round"/>
      <rect x="28" y="78" width="144" height="14" rx="7" fill="#ffd401" stroke="#111828" stroke-width="5"/>
      <rect x="92" y="40" width="16" height="40" rx="5" fill="#f5b800" stroke="#111828" stroke-width="4"/>
      <circle cx="78" cy="112" r="8" fill="#111828"/>
      <circle cx="122" cy="112" r="8" fill="#111828"/>
      <rect class="ms-lid" x="66" y="102" width="24" height="20" fill="#f2c79b"/>
      <rect class="ms-lid" x="110" y="102" width="24" height="20" fill="#f2c79b"/>
      <path d="M64 96 Q78 88 90 96 M110 96 Q122 88 136 96" fill="none" stroke="#111828" stroke-width="5" stroke-linecap="round"/>
      <path d="M80 140 Q100 150 120 140" fill="none" stroke="#111828" stroke-width="4" stroke-linecap="round"/>
      <ellipse id="ms-mouth" cx="100" cy="146" rx="14" ry="11" fill="#7f1d1d" stroke="#111828" stroke-width="4"/>
    </svg>
    <div id="ms-tag">BIJULI DAI</div>'''


def parts(words, total):
    js = ['      tl.set("#ms-mouth", { scaleY: 0.15 }, 0);',
          '      tl.set(".ms-lid", { scaleY: 0 }, 0);',
          '      tl.fromTo("#ms", { y: 300, rotation: -8 }, { y: 0, rotation: 0, duration: 0.5, ease: "back.out(1.8)" }, 0.1);',
          f'      tl.fromTo("#ms", {{ scaleY: 1 }}, {{ scaleY: 1.025, duration: 0.9, ease: "sine.inOut", yoyo: true, repeat: {max(1, int(total / 0.9) - 1)} }}, 0.6);']
    for w in words:
        js.append(f'      tl.to("#ms-mouth", {{ scaleY: 1, duration: 0.06 }}, {w["s"]:.3f});')
        js.append(f'      tl.to("#ms-mouth", {{ scaleY: 0.15, duration: 0.06 }}, {max(w["s"] + 0.08, w["e"] - 0.06):.3f});')
    t = 2.3
    while t < total - 0.5:  # blink every few seconds
        js.append(f'      tl.to(".ms-lid", {{ scaleY: 1, duration: 0.06, yoyo: true, repeat: 1 }}, {t:.2f});')
        t += 3.1 if int(t) % 2 else 2.6
    return CSS, SVG, "\n".join(js)
