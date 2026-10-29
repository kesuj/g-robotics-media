"""Viral QA, performance digest and voice choice (no network). Run: python -m pytest tests -q"""
import copy
import json
import sys
from pathlib import Path

import gr.analytics.digest as digest
import gr.state as state
from gr.qa import viral

FIX = Path(__file__).parent / "fixtures" / "g20261030-91-viral-test.json"
GOOD = json.loads(FIX.read_text(encoding="utf8"))


def test_good_brief_passes():
    assert viral.check(GOOD) == []


def test_weak_opener_and_slow_hook_fail():
    ep = copy.deepcopy(GOOD)
    ep["beats"][0]["vo"] = "Today we will talk about how a drone that you see in the sky is able to hover so very still for us."
    errs = " ".join(viral.check(ep))
    assert "throat-clearing" in errs and "first sentence" in errs and "hook_variants must include" in errs


def test_low_scores_early_payoff_and_generic_cta_fail():
    ep = copy.deepcopy(GOOD)
    ep["viral"]["hook_scores"]["clarity"] = 6
    ep["viral"]["payoff_beat"] = 0
    ep["beats"][-1]["vo"] = "Follow for a daily dose of engineering."
    errs = " ".join(viral.check(ep))
    assert "hook too weak" in errs and "payoff_beat" in errs and "generic sign-off" in errs


def test_unspoken_rehook_and_devanagari_fail():
    ep = copy.deepcopy(GOOD)
    ep["viral"]["rehooks"] = ["but here is the part nobody tells you"]
    ep["caption"] += "\nनेपालमा पनि"
    errs = " ".join(viral.check(ep))
    assert "not spoken" in errs and "English only" in errs


def test_legacy_brief_without_viral_block_is_lenient():
    ep = copy.deepcopy(GOOD)
    del ep["viral"]
    ep["beats"][-1]["vo"] = "Follow for a daily dose of engineering."
    assert viral.check(ep) == []
    assert any("viral" in e for e in viral.check(ep, strict=True))


def test_digest_ranks_and_joins_briefs(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE", tmp_path)
    monkeypatch.setattr(digest, "STATE", tmp_path)
    monkeypatch.setattr(digest, "ROOT", FIX.parents[2])
    (tmp_path / "queue.json").write_text(json.dumps({"items": {
        "a": {"id": "a", "title": "Winner", "brief": FIX.relative_to(FIX.parents[2]).as_posix(), "format": "clip"},
        "b": {"id": "b", "title": "Loser", "brief": "missing.json", "format": "clip"}}}), encoding="utf8")
    rows = [{"id": "b", "views": 900}, {"id": "a", "views": 100, "shares": 40, "ig_reels_avg_watch_time": 9000},
            {"id": "b", "views": 50}]          # newest row per id wins
    (tmp_path / "analytics.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf8")
    md = digest.build().read_text(encoding="utf8")
    assert md.index("Winner") < md.index("Loser")
    assert "That drone is not floating" in md and "contrarian" in md and "views=50" in md


def test_digest_without_data(tmp_path, monkeypatch):
    monkeypatch.setattr(digest, "STATE", tmp_path)
    monkeypatch.setattr(digest, "load", lambda name, d: d)
    assert "No Instagram Insights yet" in digest.build().read_text(encoding="utf8")


def test_edge_voice_is_south_asian_english_only(monkeypatch):
    sys.path.insert(0, str(FIX.parents[2] / "gr" / "produce" / "engine"))
    monkeypatch.delenv("GR_EDGE_VOICE", raising=False)
    import build
    assert build.edge_voice({}) == "en-IN-PrabhatNeural"
    assert build.edge_voice({"voice": "female"}) == "en-IN-NeerjaExpressiveNeural"
    assert build.edge_voice({"presenter": "maya"}) == "en-IN-NeerjaExpressiveNeural"
    assert build.edge_voice({"voice": "ne-NP-SagarNeural"}) == "en-IN-PrabhatNeural"   # never a non-English voice
    assert build.CONFIG["voice"] == "edge"
