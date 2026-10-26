"""Public hosting for Reel files when publishing via Instagram Login (Meta must fetch a public video_url).

Default: a GitHub Release asset in this repository (the repo must be PUBLIC for Meta to fetch it; secrets stay in
GitHub Actions secrets, never in the repo). Uses the Actions-provided GITHUB_TOKEN + GITHUB_REPOSITORY.
Assets are deleted after the Reel is published (cleanup policy), so the release only holds the upcoming queue.
Not needed on the Facebook Login path (resumable upload sends the file directly).
"""
import os
from pathlib import Path

import requests

API = "https://api.github.com"
TAG = "reel-queue"


def _h():
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"}


def _release(repo):
    r = requests.get(f"{API}/repos/{repo}/releases/tags/{TAG}", headers=_h(), timeout=30)
    if r.status_code == 200:
        return r.json()
    r = requests.post(f"{API}/repos/{repo}/releases", headers=_h(), timeout=30,
                      json={"tag_name": TAG, "name": "Reel queue (auto)", "body": "Upcoming Reels, removed after publishing.", "prerelease": True})
    r.raise_for_status()
    return r.json()


def upload(path, name=None):
    """Upload a file as a release asset; returns its public download URL."""
    repo = os.environ["GITHUB_REPOSITORY"]
    rel = _release(repo)
    name = name or Path(path).name
    for a in rel.get("assets", []):
        if a["name"] == name:            # idempotent: reuse an asset already uploaded for this item
            return a["browser_download_url"]
    up = rel["upload_url"].split("{")[0]
    with open(path, "rb") as f:
        r = requests.post(f"{up}?name={name}", headers={**_h(), "Content-Type": "video/mp4"}, data=f, timeout=600)
    r.raise_for_status()
    return r.json()["browser_download_url"]


def remove(name):
    repo = os.environ["GITHUB_REPOSITORY"]
    rel = _release(repo)
    for a in rel.get("assets", []):
        if a["name"] == name:
            requests.delete(f"{API}/repos/{repo}/releases/assets/{a['id']}", headers=_h(), timeout=30)
