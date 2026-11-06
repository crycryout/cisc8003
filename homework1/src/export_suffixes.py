#!/usr/bin/env python3
"""Export all 000..999 suffix subsets so no student ID has to be disclosed."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True, help="New output directory")
args = parser.parse_args()
root = Path(args.output)
root.mkdir(parents=True, exist_ok=False)
# At most one file is held open at a time; all 1000 files exist, even if empty.
for suffix in range(1000):
    (root / ("%03d.txt" % suffix)).touch()
buckets = [[] for _ in range(1000)]
# This export helper is intended for compact Top-10 output, not edge data.
with open(args.input) as handle:
    for line in handle:
        user = int(line.split(":",1)[0])
        buckets[user % 1000].append(line.rstrip("\t\r\n") + "\n")
for suffix, rows in enumerate(buckets):
    (root / ("%03d.txt" % suffix)).write_text("".join(rows))
print("Created 1000 suffix files in", root)
