"""Publish the next approved Reel for the current slot. Run by the cloud scheduler at each slot time.

    python -m gr.publish.slot [--dry-run]

Safety: an item already holding a media_id is never published again; a container already created is reused;
before publishing, recent account media are checked for the same caption (catches a publish that succeeded
but whose state commit was lost). Status moves qa_passed → submitted → published, or → failed with a reason.
"""
import datetime as dt
import os
import sys
from pathlib import Path

from gr.state import NPT, ROOT, audit, now, queue, set_status

MAX_RETRIES = 3


def pick(q):
    """Oldest qa_passed item whose not_before has passed; news items first if they are for today."""
    # "submitted" = a container exists but publishing hasn't been confirmed (transient error) → resume it first
    ready = [i for i in q["items"].values() if i["status"] in ("qa_passed", "submitted") and i.get("retries", 0) < MAX_RETRIES
             and (not i.get("not_before") or dt.datetime.fromisoformat(i["not_before"]) <= now())]
    if not ready:
        return None
    today = dt.datetime.now(NPT).date().isoformat()
    ready.sort(key=lambda i: (0 if i["status"] == "submitted" else 1, 0 if (i.get("kind") == "news" and i.get("news_date") == today) else 1, i.get("priority", 5), i["created"]))
    return ready[0]


def main(dry=False):
    from gr.publish.instagram import Instagram, PublishError
    with queue() as q:
        it = pick(q)
        if not it:
            audit("slot.empty", note="no approved Reel ready — slot skipped rather than posting filler")
            print("no approved Reel ready; skipping this slot")
            return 0
        iid = it["id"]
        if it.get("media_id"):
            set_status(q, iid, "published", note="already had media_id; not republished")
            return 0
        if dry:
            print("dry run would publish", iid, it.get("title"))
            return 0
        ig = Instagram()
        try:
            used, total = ig.quota()
            if total and used >= total:
                raise PublishError(f"publishing quota used up ({used}/{total})")
            caption = Path(ROOT / it["caption_file"].replace("\\", "/")).read_text(encoding="utf8")
            # lost-commit guard: was this caption already published in the last few posts?
            for m in ig.recent_captions():
                if (m.get("caption") or "").strip() == caption.strip():
                    set_status(q, iid, "published", media_id=m["id"], permalink=m.get("permalink"), note="found already published")
                    return 0
            cid = it.get("container_id")
            if not cid:
                if ig.login == "facebook":
                    cid = ig.create_container(caption)
                    ig.upload_bytes(cid, ROOT / it["video_file"].replace("\\", "/"))
                else:
                    from gr.publish import hosting
                    url = it.get("video_url") or hosting.upload(ROOT / it["video_file"].replace("\\", "/"), f"{iid}.mp4")
                    cid = ig.create_container(caption, video_url=url)
                set_status(q, iid, "submitted", container_id=cid)
            ig.wait_ready(cid)
            media_id, link = ig.publish(cid)
            set_status(q, iid, "published", media_id=media_id, permalink=link, published_at=now().isoformat())
            print("published", iid, link)
            if ig.login != "facebook" and os.environ.get("GITHUB_REPOSITORY"):
                from gr.publish import hosting
                hosting.remove(f"{iid}.mp4")
            return 0
        except PublishError as e:
            it["retries"] = it.get("retries", 0) + 1
            fatal = "TOKEN_EXPIRED" in str(e) or it["retries"] >= MAX_RETRIES
            set_status(q, iid, "failed" if fatal else it["status"], note=str(e)[:300])
            audit("slot.error", id=iid, note=str(e)[:300], alert=True)
            print("publish error:", e)
            return 1


if __name__ == "__main__":
    sys.exit(main(dry="--dry-run" in sys.argv))
