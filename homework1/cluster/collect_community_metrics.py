#!/usr/bin/env python3
"""Collect completed YARN job evidence from the six Streaming console logs."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from metrics import collect, write_csv

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--logs", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--history", default=os.environ.get("HW1_HISTORY_URL", "http://master:19888"))
args = parser.parse_args()
logs = sorted(Path(args.logs).glob("*.log"))
if len(logs) != 6:
    parser.error("Expected exactly six Streaming stage logs")
output = Path(args.output)
output.mkdir(parents=True, exist_ok=False)
results = []
for path in logs:
    ids = list(dict.fromkeys(re.findall(r"\bjob_\d+_\d+\b", path.read_text())))
    if len(ids) != 1:
        raise ValueError("Expected one real YARN job ID in " + str(path))
    result = collect(args.history, ids[0], output / path.stem)
    result["stage"] = path.stem
    results.append(result)
    write_csv(output / "timings.csv", results)
(output / "manifest.json").write_text(json.dumps(results, indent=2))
print("Collected six completed YARN jobs:", output)
