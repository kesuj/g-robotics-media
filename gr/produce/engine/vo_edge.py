"""Free voiceover with word timings (Microsoft neural voices via edge-tts) — South Asian English accents, the default.

    python vo_edge.py <jobs.json>
    jobs = [{ "text": "...", "mp3": "path.mp3", "words": "path.json", "voice"?: "en-IN-..." }]  (existing outputs are skipped)
Writes the same files as vo.mjs / vo_kokoro.py: an MP3 and [{"w", "s", "e"}] word timings (from WordBoundary events).
Voice: GR_EDGE_VOICE (default en-US-AndrewMultilingualNeural, natural male; en-US-AvaMultilingualNeural for female).
English only — the channel does not publish Nepali/Hindi voiceover.
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import edge_tts

VOICE = os.environ.get("GR_EDGE_VOICE", "en-US-AndrewMultilingualNeural")
RATE = os.environ.get("GR_EDGE_RATE", "+8%")


async def one(job):
    text = re.sub(r"\[[^\]]*\]", "", job["text"]).strip()   # drop ElevenLabs audio tags like [excited]
    words = []
    with open(job["mp3"], "wb") as f:
        comm = edge_tts.Communicate(text, job.get("voice") or VOICE, rate=job.get("rate") or RATE, boundary="WordBoundary")
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7   # 100 ns ticks
                words.append({"w": chunk["text"], "s": round(s, 3), "e": round(s + chunk["duration"] / 1e7, 3)})
    if not words or Path(job["mp3"]).stat().st_size < 2000:
        raise RuntimeError("edge-tts returned no audio/word timings")
    # edge-tts reports bare words; put the script's punctuation back for captions
    toks = text.split()
    i = 0
    for w in words:
        j = i
        while j < len(toks) and w["w"] not in toks[j]:
            j += 1
        if j < len(toks):
            w["w"] = toks[j]
            i = j + 1
    Path(job["words"]).write_text(json.dumps(words), encoding="utf8")
    print("edge", job.get("voice") or VOICE, job["mp3"])


async def main(jobs_path):
    for job in json.loads(Path(jobs_path).read_text(encoding="utf8")):
        if Path(job["mp3"]).exists() and Path(job["words"]).exists():
            continue
        for attempt in range(3):
            try:
                await one(job)
                break
            except Exception:
                Path(job["mp3"]).unlink(missing_ok=True)
                if attempt == 2:
                    raise
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
