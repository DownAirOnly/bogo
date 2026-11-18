#!/usr/bin/env python3
"""Publish validated weekly catalogs through the GitHub API, with SHA leases.

Supports the current catalog and a separately staged future-week preview. A
failed scrape cannot affect the live data because the importer only writes
validated snapshots.
"""
import base64
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "DownAirOnly/bogo")
TOKEN = os.environ["GH_TOKEN"]
FILES = ["data/deals.json", "data/next-deals.json", "data/current-deals.json"]

def request(method, path, payload=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "bogo-weekly-catalog",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and method == "GET":
            return None
        raise

def validate(cat):
    if len(cat.get("deals", [])) < 50:
        raise ValueError("Catalog too small for release")
    start = dt.date.fromisoformat(cat["saleStart"])
    end = dt.date.fromisoformat(cat["saleEnd"])
    if not 5 <= (end - start).days <= 8:
        raise ValueError("Invalid week dates")
    if not cat.get("sourceUrl", "").startswith("https://www.iheartpublix.com/"):
        raise ValueError("Unrecognized source")
    ids = [d["id"] for d in cat["deals"]]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate product identifiers")
    return cat

def publish(path):
    local = Path(path)
    if not local.is_file():
        return
    proposed = validate(json.loads(local.read_text(encoding="utf-8")))
    for attempt in range(4):
        remote = request("GET", path)
        current = json.loads(base64.b64decode(remote["content"])) if remote else None
        # Never clobber the same or newer week with a stale job.
        if current and proposed["saleStart"] <= current.get("saleStart", ""):
            print(path, "same week or newer is already published")
            return
        payload = {
            "message": f"Publish {path} for {proposed['saleStart']}",
            "content": base64.b64encode((json.dumps(proposed, ensure_ascii=False, indent=2) + "\n").encode()).decode(),
        }
        if remote:
            payload["sha"] = remote["sha"]
        try:
            request("PUT", path, payload)
            print("Published", path, len(proposed["deals"]), "offers")
            return
        except urllib.error.HTTPError as exc:
            if exc.code not in (409, 422) or attempt == 3:
                raise
            time.sleep(attempt + 1)

if __name__ == "__main__":
    for file in FILES:
        publish(file)
