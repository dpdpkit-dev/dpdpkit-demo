#!/usr/bin/env python3
"""Download the dpdpkit-admin release bundle pinned in admin-bundle.version and unpack it into a folder.

The published dpdpkit-fastapi wheel does not carry the dashboard yet, so the admin page serves this bundle itself.
Usage: scripts/fetch_admin_bundle.py <destination folder>
"""

import hashlib
import io
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

RELEASES = "https://github.com/dpdpkit-dev/dpdpkit-admin/releases/download"
PIN = Path(__file__).parent.parent / "admin-bundle.version"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main(dest: Path) -> None:
    version = PIN.read_text(encoding="utf-8").strip()
    name = f"dpdpkit-admin-{version}.tar.gz"
    data = fetch(f"{RELEASES}/v{version}/{name}")
    expected = fetch(f"{RELEASES}/v{version}/{name}.sha256").split()[0].decode()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        sys.exit(f"{name}: checksum {actual} does not match {expected}")
    shutil.rmtree(dest, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(dest, filter="data")
    print(f"unpacked {name} into {dest}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
