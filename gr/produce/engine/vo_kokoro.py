"""Free local voiceover with word timings (Kokoro TTS) — the fallback when ElevenLabs is out of credits.

    <eedaily>/.venv/Scripts/python.exe vo_kokoro.py <jobs.json>
    jobs = [{ "text": "...", "mp3": "path.mp3", "words": "path.json" }]  (existing outputs are skipped)
Writes the same files as vo.mjs: an MP3 and [{"w", "s", "e"}] word timings.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

VOICE = os.environ.get("EE_KOKORO_VOICE", "am_michael")
SPEED = float(os.environ.get("EE_KOKORO_SPEED", "1.05"))
SR = 24000
FFMPEG = shutil.which("ffmpeg") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin/ffmpeg.exe")


def main(jobs_path):
    jobs = json.loads(Path(jobs_path).read_text(encoding="utf8"))
    pipe = None
    for job in jobs:
        if Path(job["mp3"]).exists() and Path(job["words"]).exists():
            continue
        pipe = pipe or KPipeline(lang_code="a")
        text = re.sub(r"\[[^\]]*\]", "", job["text"]).strip()   # drop ElevenLabs audio tags like [excited]
        audio, words, offset = [], [], 0.0
        for res in pipe(text, voice=VOICE, speed=SPEED):
            a = res.audio.numpy() if hasattr(res.audio, "numpy") else np.asarray(res.audio)
            for t in res.tokens or []:
                if t.start_ts is None or not t.text.strip():
                    continue
                w = (t.text + (t.whitespace and "" or "")).strip()
                if re.fullmatch(r"[^\w]+", w) and words:   # glue punctuation to the previous word
                    words[-1]["w"] += w
                    continue
                words.append({"w": w, "s": round(offset + t.start_ts, 3), "e": round(offset + t.end_ts, 3)})
            audio.append(a)
            offset += len(a) / SR
        with tempfile.TemporaryDirectory() as d:
            wav = Path(d) / "vo.wav"
            sf.write(wav, np.concatenate(audio), SR)
            subprocess.run([str(FFMPEG), "-v", "error", "-y", "-i", str(wav), "-ar", "44100", "-b:a", "160k", job["mp3"]], check=True)
        Path(job["words"]).write_text(json.dumps(words), encoding="utf8")
        print("kokoro", job["mp3"])


if __name__ == "__main__":
    main(sys.argv[1])
