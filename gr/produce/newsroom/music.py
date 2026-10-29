"""Procedural news bed + transition SFX (numpy only, no samples → no licence questions, identical every run).

bed(path, seconds, hits, speech)  — a driving broadcast-style bed: pulsing synth bass, warm pad chords, ticking hats,
                            with a soft whoosh + impact at every time in `hits` (story transitions), ducked by DUCK
                            (≈ −7 dB, fast attack / slow release) inside every `speech` span [(start, end)] so the
                            voice sits on top and the music lifts in the gaps.
"""
import wave

import numpy as np

SR = 44100
CHORDS = [  # A minor → F → C → G (root, third, fifth in Hz)
    (110.00, 130.81, 164.81), (87.31, 110.00, 130.81), (130.81, 164.81, 196.00), (98.00, 123.47, 146.83)]
BPM = 112
DUCK = 0.45


def _env(n, a, r):
    e = np.ones(n)
    a, r = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    return sum(2 * ((t * f * (1 + d)) % 1) - 1 for d in (-detune, 0, detune)) / 3


def _lowpass(x, k):
    """One-pole low-pass, k in (0,1]: smaller = darker."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def _lp_fast(x, k):
    # vectorised approximation of the one-pole filter via exponential kernel convolution
    m = int(min(len(x), 4 / max(k, 1e-3)))
    ker = k * (1 - k) ** np.arange(m)
    return np.convolve(x, ker)[:len(x)]


def duck(n, speech, attack=0.08, release=0.45):
    """Gain curve: 1 in the gaps, DUCK while the voice talks, smoothed in 1 ms blocks."""
    target = np.ones(n)
    for s, e in speech:
        target[max(0, int((s - 0.06) * SR)):min(n, int((e + 0.12) * SR))] = DUCK
    env, acc, blk = np.empty(n), 1.0, SR // 1000
    for i in range(0, n, blk):
        k = 1 - np.exp(-blk / ((attack if target[i] < acc else release) * SR))
        acc += k * (target[i] - acc)
        env[i:i + blk] = acc
    return env


def bed(path, seconds, hits=(), speech=()):
    n = int(seconds * SR) + SR
    out = np.zeros((n, 2))
    beat = 60 / BPM
    bar = beat * 4
    rng = np.random.default_rng(7)
    t = 0.0
    k = 0
    while t < seconds + bar:
        root, third, fifth = CHORDS[k % 4]
        s = int(t * SR)
        ln = min(int(bar * SR), n - s)
        if ln <= 0:
            break
        pad = (_saw(root * 2, ln, 0.004) + _saw(third * 2, ln, 0.005) + _saw(fifth * 2, ln, 0.003)) / 3
        pad = _lp_fast(pad, 0.025) * _env(ln, 0.25, 0.3) * 0.16
        out[s:s + ln, 0] += pad
        out[s:s + ln, 1] += np.roll(pad, 240)
        for e in range(8):   # eighth-note pulsing bass
            bs = s + int(e * beat / 2 * SR)
            bl = min(int(beat / 2 * SR * 0.9), n - bs)
            if bl <= 0:
                continue
            b = _lp_fast(_saw(root, bl, 0.002), 0.06) * _env(bl, 0.004, 0.12) * (0.30 if e % 2 == 0 else 0.20)
            out[bs:bs + bl] += b[:, None]
        for e in range(16):  # sixteenth hats, accented off-beats
            hs = s + int(e * beat / 4 * SR)
            hl = min(int(0.03 * SR), n - hs)
            if hl <= 0:
                continue
            h = rng.standard_normal(hl)
            h = (h - _lp_fast(h, 0.3)) * np.exp(-np.linspace(0, 9, hl)) * (0.05 if e % 4 == 2 else 0.025)
            out[hs:hs + hl, 0] += h * 0.8
            out[hs:hs + hl, 1] += h
        for e in (0, 2):     # soft kick on 1 and 3
            ks = s + int(e * beat * SR)
            kl = min(int(0.22 * SR), n - ks)
            if kl <= 0:
                continue
            tt = np.arange(kl) / SR
            kick = np.sin(2 * np.pi * (50 + 70 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14) * 0.35
            out[ks:ks + kl] += kick[:, None]
        t += bar
        k += 1
    for h in hits:           # whoosh into + low impact on each transition
        hs = int(max(0, h - 0.45) * SR)
        wl = min(int(0.5 * SR), n - hs)
        if wl > 0:
            w = rng.standard_normal(wl)
            sweep = np.linspace(0.01, 0.35, wl)
            w = np.array(_lowpass(w, 0.2)) * (sweep ** 1.5) * 0.9
            out[hs:hs + wl] += w[:, None]
        ks = int(h * SR)
        kl = min(int(0.9 * SR), n - ks)
        if kl > 0:
            tt = np.arange(kl) / SR
            boom = np.sin(2 * np.pi * (38 + 40 * np.exp(-tt * 9)) * tt) * np.exp(-tt * 4) * 0.45
            out[ks:ks + kl] += boom[:, None]
    out = out[:int(seconds * SR)]
    if speech:
        out *= duck(len(out), speech)[:, None]
    fade = int(1.2 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    out /= max(1e-6, np.abs(out).max()) / 0.8
    pcm = (out * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    import sys
    bed(sys.argv[1], float(sys.argv[2]), [float(x) for x in sys.argv[3:]])
