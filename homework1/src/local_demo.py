#!/usr/bin/env python3
"""Small-input in-memory test harness; NOT a Hadoop runtime or a scale runner."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_community import pipeline

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("input")
parser.add_argument("--output", required=True)
parser.add_argument("--k", type=int, default=10)
parser.add_argument("--block-size", type=int, default=3)
args = parser.parse_args()
ranks, scores = pipeline(Path(args.input).read_text(), args.k, args.block_size)
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("".join(u + ":" + " ".join(ranks[u]) + "\n" for u in sorted(ranks, key=int)))
output.with_suffix(".scores.txt").write_text("\n".join(sorted(scores)) + "\n")
print(json.dumps({"mode": "local semantic simulation; not Hadoop", "users": len(ranks), "output": str(output)}))
