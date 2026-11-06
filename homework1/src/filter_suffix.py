#!/usr/bin/env python3
"""Filter completed ALL-user results; supply only your student ID's last 3 digits."""
import argparse
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--suffix", required=True)
args = parser.parse_args()
if len(args.suffix) != 3 or not args.suffix.isascii() or not args.suffix.isdigit():
    parser.error("--suffix must contain exactly three decimal digits, e.g. 007")
target = int(args.suffix)
for line in sys.stdin:
    if not line.strip():
        continue
    user = line.split(":", 1)[0]
    if int(user) % 1000 == target:
        sys.stdout.write(line.rstrip("\t\r\n") + "\n")
