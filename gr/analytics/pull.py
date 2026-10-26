"""Pulls Instagram Insights for published Reels into state/analytics.jsonl (only metrics the API returns — none invented).

    python -m gr.analytics.pull

Reels metrics requested: views, reach, saved, shares, likes, comments, total_interactions, ig_reels_avg_watch_time.
Metrics the API rejects for this account/version are dropped and noted, not guessed.
"""
from gr.state import append, audit, load

METRICS = ["views", "reach", "saved", "shares", "likes", "comments", "total_interactions", "ig_reels_avg_watch_time"]


def main():
    from gr.publish.instagram import Instagram, PublishError
    ig = Instagram()
    items = [i for i in load("queue.json", {"items": {}})["items"].values() if i.get("media_id")]
    ok = 0
    for it in items:
        metrics, got = list(METRICS), {}
        while metrics:
            try:
                d = ig._req("GET", f"{it['media_id']}/insights", metric=",".join(metrics))
                got = {m["name"]: (m.get("values") or [{}])[0].get("value", m.get("total_value", {}).get("value")) for m in d.get("data", [])}
                break
            except PublishError as e:
                bad = next((m for m in metrics if m in str(e)), None)
                if not bad:
                    audit("analytics.error", id=it["id"], note=str(e)[:200])
                    break
                metrics.remove(bad)
        if got:
            append("analytics.jsonl", {"id": it["id"], "media_id": it["media_id"], "format": it.get("format"), "series": it.get("series"),
                                       "style": it.get("style"), "published_at": it.get("published_at"), **got})
            ok += 1
    audit("analytics.pull", items=ok)
    print(f"insights for {ok} Reel(s)")


if __name__ == "__main__":
    main()
