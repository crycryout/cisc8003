#!/usr/bin/env python3
"""Download the exact URLs in the assignment (without substituting datasets)."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

URLS = {
    "small": "https://www.dropbox.com/s/ns771cy27fpjthj/facebook_combined.txt.gz?dl=1",
    "medium": "https://www.dropbox.com/s/g1nthvj98iaikly/twitter_combined.txt.gz?dl=1",
    "large": "https://www.dropbox.com/s/cbf4r2at8dmd9ms/gplus_combined.txt.gz?dl=1",
    "shakespeare": "https://github.com/hupili/agile-ir/raw/master/data/Shakespeare.tar.gz",
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dataset", choices=URLS)
parser.add_argument("--directory", default="data")
parser.add_argument("--decompress", action="store_true", help="Write plain course_<size>.txt for graph data")
args = parser.parse_args()
root = Path(args.directory)
root.mkdir(parents=True, exist_ok=True)
name = "Shakespeare.tar.gz" if args.dataset == "shakespeare" else "course_" + args.dataset + ".txt.gz"
path = root / name
plain = path.with_suffix("")
if path.exists() or (args.decompress and plain.exists()):
    parser.error("Output already exists; refusing to overwrite")
request = urllib.request.Request(URLS[args.dataset], headers={"User-Agent": "Homework1-Reproduction/1.0"})
digest = hashlib.sha256()
with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as output:
    for chunk in iter(lambda: response.read(1024 * 1024), b""):
        digest.update(chunk)
        output.write(chunk)
with path.open("rb") as handle:
    if handle.read(2) != b"\x1f\x8b":
        raise ValueError("Download is not gzip; it may be an HTML access/expired-link page")
if args.decompress:
    if args.dataset == "shakespeare":
        parser.error("Extract the Shakespeare tar archive separately; --decompress is for graph inputs")
    with gzip.open(path,"rb") as source, plain.open("wb") as output:
        shutil.copyfileobj(source,output)
metadata = {"assignment_dataset": args.dataset, "url": URLS[args.dataset],
            "compressed_bytes": path.stat().st_size, "compressed_sha256": digest.hexdigest(),
            "substitution": False}
path.with_name(path.name + ".metadata.json").write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata,indent=2))
