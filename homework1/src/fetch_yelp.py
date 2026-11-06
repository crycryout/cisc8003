#!/usr/bin/env python3
"""Download the official Yelp ZIP with checked byte ranges and extract reviews only."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import time
import urllib.request
import zipfile

URL = "https://business.yelp.com/external-assets/files/Yelp-JSON.zip"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--connections", type=int, default=8)
    args = parser.parse_args()
    if args.connections < 1 or args.output.exists():
        parser.error("Use positive connections and a new review output path")
    args.directory.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(URL, method="HEAD", headers={"User-Agent": "curl/8.5.0"}), timeout=30) as response:
        size = int(response.headers["Content-Length"])
        etag = response.headers.get("ETag")
    archive = args.directory / "Yelp-JSON.zip"
    plan = {"url": URL, "bytes": size, "etag": etag}
    plan_path = args.directory / "download.json"
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError("Remote input changed; use a new download directory")
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    chunk_size = 64 * 1024 * 1024

    def download(index):
        start, end = index * chunk_size, min(size, (index + 1) * chunk_size) - 1
        path = args.directory / ("range-%04d" % index)
        if path.exists() and path.stat().st_size == end - start + 1:
            return path
        for attempt in range(4):
            try:
                partial = path.with_suffix(".partial")
                have = partial.stat().st_size if partial.exists() else 0
                if have > end - start + 1:
                    raise ValueError("Partial range exceeds its recorded size")
                if have == end - start + 1:
                    partial.rename(path)
                    return path
                request_start = start + have
                request = urllib.request.Request(URL, headers={"User-Agent": "curl/8.5.0", "Range": "bytes=%d-%d" % (request_start, end), "If-Range": etag or ""})
                with urllib.request.urlopen(request, timeout=90) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != "bytes %d-%d/%d" % (request_start, end, size):
                        raise ValueError("Server did not honor the exact requested range")
                    with partial.open("ab") as output:
                        shutil.copyfileobj(response, output, 1024 * 1024)
                if path.with_suffix(".partial").stat().st_size != end - start + 1:
                    raise ValueError("Truncated range")
                path.with_suffix(".partial").rename(path)
                print("Downloaded range %d/%d" % (index + 1, (size + chunk_size - 1) // chunk_size), flush=True)
                return path
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)

    if not archive.exists():
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.connections) as executor:
            paths = list(executor.map(download, range((size + chunk_size - 1) // chunk_size)))
        print("All byte ranges verified; assembling complete ZIP", flush=True)
        with archive.with_suffix(".partial").open("wb") as output:
            for path in paths:
                with path.open("rb") as source:
                    shutil.copyfileobj(source, output, 4 * 1024 * 1024)
        archive.with_suffix(".partial").rename(archive)
    if archive.stat().st_size != size:
        raise ValueError("ZIP byte count differs from HEAD")
    print("Extracting the complete review JSONL", flush=True)
    with zipfile.ZipFile(archive) as package:
        members = [m for m in package.namelist() if m.endswith("/yelp_dataset.tar")]
        if len(members) != 1:
            raise ValueError("Expected one Yelp dataset tar member")
        with package.open(members[0]) as stream, tarfile.open(fileobj=stream, mode="r|*") as data:
            found = False
            for member in data:
                if member.isfile() and Path(member.name).name == "yelp_academic_dataset_review.json":
                    with data.extractfile(member) as source, args.output.with_suffix(".partial").open("wb") as output:
                        shutil.copyfileobj(source, output, 4 * 1024 * 1024)
                    found = True
                    break
            if not found:
                raise ValueError("Review JSONL was absent")
    args.output.with_suffix(".partial").rename(args.output)
    result = {**plan, "zip_sha256": sha256(archive), "review_bytes": args.output.stat().st_size,
              "review_sha256": sha256(args.output), "input_scope": "complete uncompressed review JSONL"}
    args.output.with_name(args.output.name + ".manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
