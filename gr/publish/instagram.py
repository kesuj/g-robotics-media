"""Instagram Reels publisher (official Graph API only). Checked against Meta docs, Graph API v26.0, 2026-10-26.

Two supported login paths (env IG_LOGIN):
  "instagram"  graph.instagram.com, Instagram User token (instagram_business_basic + instagram_business_content_publish).
               No Facebook Page needed. Reels need a PUBLIC video_url (Meta fetches it) — see gr/publish/hosting.py.
  "facebook"   graph.facebook.com, token via Facebook Login for Business (instagram_basic, instagram_content_publish,
               pages_read_engagement); account linked to a Page. Allows resumable upload of the file itself
               (rupload.facebook.com), so no public hosting is needed.

Flow: create container (media_type=REELS) → [upload bytes] → poll status_code once a minute (≤ 5 min; FINISHED /
ERROR / EXPIRED) → media_publish(creation_id) → read back permalink. Instagram has no API-side scheduling, so the
cloud worker calls publish() at the slot time. Rate limit is read live from content_publishing_limit.
Tokens never appear in logs or exceptions.
"""
import os
import time
from pathlib import Path

import requests

API_VERSION = os.environ.get("IG_API_VERSION", "v26.0")


class PublishError(Exception):
    pass


class Instagram:
    def __init__(self, user_id=None, token=None, login=None):
        self.user_id = user_id or os.environ["IG_USER_ID"]
        self._token = token or os.environ["IG_ACCESS_TOKEN"]
        self.login = (login or os.environ.get("IG_LOGIN", "instagram")).lower()
        host = "graph.instagram.com" if self.login == "instagram" else "graph.facebook.com"
        self.base = f"https://{host}/{API_VERSION}"

    # -- plumbing -------------------------------------------------------------------------------------------
    def _req(self, method, path, **params):
        url = path if path.startswith("http") else f"{self.base}/{path}"
        params["access_token"] = self._token
        for attempt in range(4):
            r = requests.request(method, url, params=params, timeout=60)
            if r.status_code < 500 and r.status_code != 429:
                break
            time.sleep(5 * 2 ** attempt)   # transient: back off and retry
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code >= 400 or "error" in data:
            err = data.get("error", {})
            code = err.get("code")
            msg = (err.get("message") or r.text[:200]).replace(self._token, "***")
            if code == 190:
                raise PublishError(f"TOKEN_EXPIRED_OR_INVALID: {msg}")
            raise PublishError(f"HTTP {r.status_code} code={code}: {msg}")
        return data

    # -- checks ---------------------------------------------------------------------------------------------
    def quota(self):
        d = self._req("GET", f"{self.user_id}/content_publishing_limit", fields="quota_usage,config")
        row = (d.get("data") or [{}])[0]
        return row.get("quota_usage", 0), (row.get("config") or {}).get("quota_total")

    def whoami(self):
        return self._req("GET", "me", fields="user_id,username" if self.login == "instagram" else "id,username")

    def recent_captions(self, n=15):
        d = self._req("GET", f"{self.user_id}/media", fields="id,caption,timestamp,permalink", limit=n)
        return d.get("data", [])

    # -- publish flow ---------------------------------------------------------------------------------------
    def create_container(self, caption, video_url=None, cover_offset_ms=None, share_to_feed=True):
        p = {"media_type": "REELS", "caption": caption, "share_to_feed": str(share_to_feed).lower()}
        if cover_offset_ms is not None:
            p["thumb_offset"] = int(cover_offset_ms)
        if video_url:
            p["video_url"] = video_url
        else:
            if self.login != "facebook":
                raise PublishError("resumable upload is only available with Facebook Login; set a public video_url")
            p["upload_type"] = "resumable"
        return self._req("POST", f"{self.user_id}/media", **p)["id"]

    def upload_bytes(self, container_id, path):
        """Resumable upload (Facebook Login path only)."""
        path = Path(path)
        size = path.stat().st_size
        url = f"https://rupload.facebook.com/ig-api-upload/{API_VERSION}/{container_id}"
        with path.open("rb") as f:
            r = requests.post(url, data=f, timeout=600, headers={
                "Authorization": f"OAuth {self._token}", "offset": "0", "file_size": str(size)})
        if r.status_code >= 400:
            raise PublishError(f"upload failed HTTP {r.status_code}: {r.text[:200].replace(self._token, '***')}")

    def wait_ready(self, container_id, max_minutes=10):
        for _ in range(max_minutes):
            st = self._req("GET", container_id, fields="status_code,status").get("status_code")
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise PublishError(f"container {st}")
            time.sleep(60)
        raise PublishError("container not FINISHED in time")

    def publish(self, container_id):
        media_id = self._req("POST", f"{self.user_id}/media_publish", creation_id=container_id)["id"]
        link = self._req("GET", media_id, fields="permalink").get("permalink")
        if not link:
            raise PublishError(f"published media {media_id} has no permalink yet")
        return media_id, link

    # -- token ----------------------------------------------------------------------------------------------
    def refresh_token(self):
        """Instagram Login long-lived tokens last ~60 days and can be refreshed once they are ≥ 24 h old.
        Returns (new_token, expires_in_seconds). The caller stores it as a GitHub secret."""
        if self.login != "instagram":
            return None, None
        d = self._req("GET", "https://graph.instagram.com/refresh_access_token", grant_type="ig_refresh_token")
        return d.get("access_token"), d.get("expires_in")
