"""Persistent state for the media operation, kept as JSON/JSONL files in the repo (committed by each cloud run).

Item lifecycle (one id per Reel):  briefed → rendered → qa_passed → scheduled → submitted → published
                                    any step can go → failed (with reason, retries counted)
`published` is only set after the platform returns a media id AND a permalink was read back.
"""
import datetime as dt
import json
import os
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
NPT = dt.timezone(dt.timedelta(hours=5, minutes=45))
STATUSES = ["briefed", "rendered", "qa_passed", "scheduled", "submitted", "published", "failed"]


def now():
    return dt.datetime.now(dt.timezone.utc)


def load(name, default):
    p = STATE / name
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else default


def save(name, data):
    p = STATE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf8")
    os.replace(tmp, p)


def append(name, row):
    p = STATE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": now().isoformat(), **row}
    with p.open("a", encoding="utf8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def audit(action, **kw):
    """Every significant automated action leaves a line in state/audit.jsonl (no secrets)."""
    append("audit.jsonl", {"action": action, **kw})


@contextmanager
def queue():
    """The queue of Reels: {"items": {id: {...}}}. Saved on exit even if the block raises."""
    q = load("queue.json", {"items": {}})
    try:
        yield q
    finally:
        save("queue.json", q)


def set_status(q, item_id, status, **extra):
    assert status in STATUSES, status
    it = q["items"][item_id]
    it.setdefault("history", []).append({"at": now().isoformat(), "status": status, **({"note": extra.get("note")} if extra.get("note") else {})})
    it["status"] = status
    it.update({k: v for k, v in extra.items() if k != "note"})
    audit("status", id=item_id, status=status, **{k: v for k, v in extra.items() if k in ("note", "media_id", "permalink", "slot")})
