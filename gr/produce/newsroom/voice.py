"""G. Dai's voice: OmniVoice (Apache-2.0) cloned from the fixed reference clip, then word timings via faster-whisper.

Runs inside a Python that has `omnivoice` + `faster_whisper` (locally: VoiceStudio's runtime venv; in the cloud: the
venv made by the produce workflow). Called as a subprocess by build_news.py:

    python voice.py job.json      job = {"ref_wav", "ref_text", "segments": [{"id", "text", "out"}], "words_out"}

Writes each segment wav and one JSON {segment_id: [{"w", "s", "e"}]} with the SCRIPT's words (correct spelling)
mapped onto the recognised timings.
"""
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

if os.environ.get("LOCALAPPDATA") and not os.environ.get("HF_HOME"):
    cache = Path(os.environ["LOCALAPPDATA"]) / "OmniVoice" / "hf_cache"
    if cache.exists():
        os.environ["HF_HOME"] = str(cache)

import torch
import torchaudio


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def align(script, rec):
    """script: list of words; rec: list of (word, s, e). Returns [{"w","s","e"}] for every script word."""
    a, b = [norm(w) for w in script], [norm(w) for w, _, _ in rec]
    times = [None] * len(script)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = rec[blk.b + k][1:]
    end = rec[-1][2] if rec else 0.3 * len(script)
    # fill gaps by spreading unmatched words between their matched neighbours
    i = 0
    while i < len(script):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(script) and times[j] is None:
            j += 1
        lo = times[i - 1][1] if i > 0 else 0.0
        hi = times[j][0] if j < len(script) else end
        step = max(0.05, (hi - lo) / (j - i))
        for k in range(i, j):
            times[k] = (lo + step * (k - i), lo + step * (k - i + 1))
        i = j
    return [{"w": w, "s": round(s, 3), "e": round(e, 3)} for w, (s, e) in zip(script, times)]


def main(job_path):
    job = json.loads(Path(job_path).read_text(encoding="utf8"))
    from omnivoice import OmniVoice
    from faster_whisper import WhisperModel

    t0 = time.time()
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
    print(f"tts loaded {time.time() - t0:.0f}s", flush=True)
    steps = int(os.environ.get("GDAI_STEPS", "16"))
    for seg in job["segments"]:
        if Path(seg["out"]).exists() and Path(seg["out"]).stat().st_size > 2000:
            continue
        t = time.time()
        torch.manual_seed(11)
        audio = model.generate(text=seg["text"], ref_audio=job["ref_wav"], ref_text=job["ref_text"], num_step=steps,
                               speed=float(os.environ.get("GDAI_SPEED", "1.04")))
        torchaudio.save(seg["out"], audio[0], model.sampling_rate)
        print(f"{seg['id']}: {time.time() - t:.0f}s", flush=True)
    del model

    wm = WhisperModel(os.environ.get("WHISPER_MODEL", "base.en"), device="cpu", compute_type="int8")
    words = {}
    for seg in job["segments"]:
        parts, _ = wm.transcribe(seg["out"], word_timestamps=True, language="en", beam_size=1)
        rec = [(w.word.strip(), w.start, w.end) for p in parts for w in (p.words or [])]
        words[seg["id"]] = align(seg["text"].split(), rec)
    Path(job["words_out"]).write_text(json.dumps(words, indent=1), encoding="utf8")
    print("voice done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
