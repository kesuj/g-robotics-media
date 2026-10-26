"""Design G. Dai's news-anchor voice once with OmniVoice voice design (Indian English, professional).

Run with VoiceStudio's runtime python (has omnivoice + torch):
  "%APPDATA%/VoiceStudio/runtime/project/.venv/Scripts/python.exe" tools/gdai_voice_design.py out_dir
Writes one wav per candidate; the chosen one becomes assets/voice/gdai_ref.wav (+ its transcript) and every
episode is then voice-cloned from that reference so G. Dai always sounds the same.
"""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HOME", str(Path(os.environ["LOCALAPPDATA"]) / "OmniVoice" / "hf_cache"))

import torchaudio
import torch
from omnivoice import OmniVoice

TEXT = ("Good evening, and welcome to Tech News with G. Dai. "
        "Here are the stories shaping technology in Nepal and around the world today.")
CANDIDATES = {
    "a_mid_low": "male, middle-aged, low pitch, indian accent",
    "b_young_mod": "male, young adult, moderate pitch, indian accent",
    "c_mid_mod": "male, middle-aged, moderate pitch, indian accent",
}

out = Path(sys.argv[1] if len(sys.argv) > 1 else "voice_candidates")
out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
print(f"loaded in {time.time() - t0:.0f}s", flush=True)
for name, instruct in CANDIDATES.items():
    torch.manual_seed(7)
    t = time.time()
    audio = model.generate(text=TEXT, instruct=instruct, num_step=16)
    torchaudio.save(str(out / f"{name}.wav"), audio[0], model.sampling_rate)
    print(f"{name}: {time.time() - t:.0f}s", flush=True)
