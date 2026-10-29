"""Sound design for an engine Reel: the music bed ducked under the voice + procedural impact hits (numpy only, no samples).

    mix(bed_mp3, out_wav, total, speech, hits=(), rises=(), ffmpeg="ffmpeg")

speech  [(start, end)] seconds where the voice talks → the bed dips ~9 dB there (fast attack, slow release) and
        comes back up in the gaps, the intro and the outro so the Reel never feels empty.
hits    times of a sub boom + noise crack (hook claim, payoff, CTA).
rises   times a 1.4 s filtered-noise riser ENDS on (the build into the payoff).
The stem is written at final level (the composition plays it at volume 1); whoosh/pop SFX on cuts stay separate clips.
"""
import subprocess
import wave

import numpy as np

SR = 44100
BED_UP, BED_DUCK = 0.16, 0.055     # linear gain in gaps / under speech (old fixed level was 0.10)


def _decode(path, seconds, ffmpeg, offset=2.0):
    raw = subprocess.run([ffmpeg, "-v", "error", "-stream_loop", "-1", "-ss", f"{offset}", "-i", str(path), "-t", f"{seconds:.3f}",
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(np.float64)
    n = int(seconds * SR)
    return np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]


def duck_envelope(n, speech, attack=0.08, release=0.45, lead=0.06):
    """1.0 in the gaps, BED_DUCK/BED_UP under speech, with smooth ramps (one-pole attack/release)."""
    target = np.ones(n)
    for s, e in speech:
        target[max(0, int((s - lead) * SR)):min(n, int((e + 0.12) * SR))] = BED_DUCK / BED_UP
    env = np.empty(n)
    acc = 1.0
    ka, kr = 1 - np.exp(-1 / (attack * SR)), 1 - np.exp(-1 / (release * SR))
    # per-block smoothing (1 ms blocks) keeps this fast in pure numpy
    blk = SR // 1000
    for i in range(0, n, blk):
        t = target[i]
        k = ka if t < acc else kr
        acc += (1 - (1 - k) ** blk) * (t - acc)
        env[i:i + blk] = acc
    return env


def _lowpass(x, fc):
    s = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(s / (1 + (f / fc) ** 4), len(x))


def _add(out, sig, t):
    i = int(max(0, t) * SR)
    sig = sig[:max(0, len(out) - i)]
    out[i:i + len(sig)] += sig[:, None] if sig.ndim == 1 else sig


def mix(bed_mp3, out_wav, total, speech, hits=(), rises=(), ffmpeg="ffmpeg"):
    n = int(total * SR)
    rng = np.random.default_rng(5)
    bed = _decode(bed_mp3, total, ffmpeg)
    bed /= max(1e-6, np.abs(bed).max())
    out = bed * BED_UP * duck_envelope(n, speech)[:, None]
    for t in hits:                      # cinematic sub boom + short noise crack
        m = int(1.4 * SR)
        tt = np.arange(m) / SR
        f = 42 + 70 * np.exp(-tt / 0.08)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.45)
        crack = _lowpass(rng.standard_normal(m), 2500) * np.exp(-tt / 0.03) * 0.5
        _add(out, (body + crack) * 0.26, t)
    for t in rises:                     # filtered-noise riser ending on t
        d = 1.4
        m = int(d * SR)
        k = (np.arange(m) / m) ** 2.2
        x = rng.standard_normal(m)
        sig = (_lowpass(x, 500) * (1 - k) + _lowpass(x, 6000) * k) * k * 0.09
        _add(out, sig, t - d)
    fade = min(n, int(1.2 * SR))
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    fin = min(n, int(0.02 * SR))
    out[:fin] *= np.linspace(0, 1, fin)[:, None]
    peak = np.abs(out).max()
    if peak > 0.7:                      # never let the stem clip under the voice
        out *= 0.7 / peak
    with wave.open(str(out_wav), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((out * 32767).astype("<i2").tobytes())
    return out_wav


def speech_spans(starts, voices, gap=0.35):
    """Merge every word of every beat into speaking spans (absolute seconds)."""
    spans = []
    for st, v in zip(starts, voices):
        for w in v["words"]:
            s, e = st + w["s"], st + w["e"]
            if spans and s - spans[-1][1] < gap:
                spans[-1][1] = max(spans[-1][1], e)
            else:
                spans.append([s, e])
    return spans
