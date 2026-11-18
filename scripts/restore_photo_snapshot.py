#!/usr/bin/env python3
"""Recover product-identity-matched photos from a successful Pages artifact.

The archived image library is read-only; current photos always win. This seed
protects against temporary image-search blocking or changes in provider markup.
No unknown archive paths are extracted.
"""
import sys
import tarfile
from pathlib import Path

TARGET = Path("images/verified-products")
PREFIX = "./images/verified-products/"
MAX_IMAGE_SIZE = 1_500_000

def restore(path):
    archive = Path(path)
    if not archive.is_file():
        print("No photo archive available; using existing cache and live search")
        return
    TARGET.mkdir(parents=True, exist_ok=True)
    saved = 0
    existing = 0
    with tarfile.open(archive, "r:*") as source:
        for member in source:
            if not member.isfile() or not member.name.startswith(PREFIX):
                continue
            name = member.name[len(PREFIX):]
            if not name or "/" in name or "\\" in name:
                continue
            if not name.endswith(".webp") or member.size < 500 or member.size > MAX_IMAGE_SIZE:
                continue
            destination = TARGET / name
            if destination.exists() and destination.stat().st_size > 500:
                existing += 1
                continue
            stream = source.extractfile(member)
            if stream is None:
                continue
            data = stream.read(MAX_IMAGE_SIZE + 1)
            if len(data) != member.size or not data.startswith(b"RIFF") or data[8:12] != b"WEBP":
                continue
            destination.write_bytes(data)
            saved += 1
    print(f"Restored product-photo snapshot: {saved} new, {existing} already cached")

if __name__ == "__main__":
    restore(sys.argv[1] if len(sys.argv) > 1 else "/tmp/bogo-photo-backup/artifact.tar")
