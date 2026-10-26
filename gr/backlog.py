"""Prints "true" when the approved queue is below config min_backlog (the editor should write more briefs)."""
import json

from gr.state import ROOT, load

cfg = json.loads((ROOT / "config" / "editorial.json").read_text(encoding="utf8"))
items = load("queue.json", {"items": {}})["items"].values()
ready = sum(1 for i in items if i["status"] in ("briefed", "rendered", "qa_passed"))
print("true" if ready < cfg["min_backlog"] else "false")
