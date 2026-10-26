"""Publisher safety tests with a fake Instagram (no network). Run: python -m pytest tests -q"""
import json
import shutil

import pytest

import gr.publish.instagram as igmod
import gr.publish.slot as slot
import gr.state as state


class FakeIG:
    login = "instagram"
    published, containers = [], []
    recent = []
    quota_used, fail_publish = 0, None

    def __init__(self, *a, **k):
        pass

    def quota(self):
        return FakeIG.quota_used, 100

    def recent_captions(self, n=15):
        return FakeIG.recent

    def create_container(self, caption, video_url=None, **k):
        FakeIG.containers.append(video_url)
        return f"c{len(FakeIG.containers)}"

    def wait_ready(self, cid):
        pass

    def publish(self, cid):
        if FakeIG.fail_publish:
            raise igmod.PublishError(FakeIG.fail_publish)
        FakeIG.published.append(cid)
        return f"m{cid}", f"https://instagram.com/reel/{cid}"


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE", tmp_path / "state")
    monkeypatch.setattr(slot, "ROOT", tmp_path)
    monkeypatch.setattr(igmod, "Instagram", FakeIG)
    (tmp_path / "cap.txt").write_text("hello reel", encoding="utf8")
    FakeIG.published, FakeIG.containers, FakeIG.recent, FakeIG.quota_used, FakeIG.fail_publish = [], [], [], 0, None
    state.save("queue.json", {"items": {"g1": {"id": "g1", "title": "t", "status": "qa_passed", "created": "2026-10-27T00:00:00+00:00",
                                               "caption_file": "cap.txt", "video_url": "https://x/g1.mp4", "retries": 0}}})
    yield tmp_path


def q():
    return state.load("queue.json", {})["items"]["g1"]


def test_publishes_once_and_never_twice():
    assert slot.main() == 0 and q()["status"] == "published" and q()["permalink"]
    assert slot.main() == 0                              # second run: nothing ready
    assert len(FakeIG.published) == 1


def test_lost_commit_guard_finds_existing_post():
    FakeIG.recent = [{"id": "m9", "caption": "hello reel", "permalink": "https://instagram.com/reel/9"}]
    slot.main()
    assert q()["status"] == "published" and q()["media_id"] == "m9" and FakeIG.published == []


def test_quota_exhausted_does_not_publish():
    FakeIG.quota_used = 100
    assert slot.main() == 1 and FakeIG.published == [] and q()["retries"] == 1


def test_token_expiry_fails_item_and_reuses_container_on_retry():
    FakeIG.fail_publish = "TOKEN_EXPIRED_OR_INVALID: x"
    slot.main()
    assert q()["status"] == "failed" and q()["container_id"] == "c1"


def test_transient_error_retries_with_same_container():
    FakeIG.fail_publish = "HTTP 400 code=9007: media not ready"
    slot.main()
    assert q()["status"] == "submitted" and q()["retries"] == 1
    FakeIG.fail_publish = None
    slot.main()
    assert q()["status"] == "published" and len(FakeIG.containers) == 1
