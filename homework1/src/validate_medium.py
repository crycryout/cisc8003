#!/usr/bin/env python3
"""Independent medium-graph validation; this checker loads the graph in memory.

The actual Hadoop implementation is disk/shuffle based. This optional oracle is
for small/medium validation and is deliberately independent of its stage code.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import random

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input", required=True)
parser.add_argument("--results", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--format", choices=["edges", "adjacency"], default="edges")
parser.add_argument("--edge-order", choices=["follower-followee", "followee-follower"], default="follower-followee")
parser.add_argument("--samples", type=int, default=1000)
args = parser.parse_args()
if args.samples < 1:
    parser.error("samples must be positive")
follows, incoming, users = defaultdict(set), defaultdict(set), set()
opener = gzip.open if args.input.endswith(".gz") else open
with opener(args.input, "rt") as handle:
    for line in handle:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if args.format == "adjacency":
            target, tail = line.split(":", 1)
            target = int(target)
            users.add(target)
            edges = ((int(u), target) for u in tail.split())
        else:
            a, b = map(int, line.split())
            edges = [(a, b) if args.edge_order == "follower-followee" else (b, a)]
        for user, target in edges:
            follows[user].add(target)
            incoming[target].add(user)
            users.update((user, target))
rankings = {}
with open(args.results) as handle:
    for line in handle:
        user, rest = line.rstrip("\n").split(":", 1)
        user = int(user)
        candidates = list(map(int, rest.split()))
        if user in rankings:
            raise ValueError("Duplicate user result")
        if len(candidates) != min(10, len(users)-1) or len(set(candidates)) != len(candidates):
            raise ValueError("Invalid result length or duplicate candidates")
        if user in candidates or any(v not in users for v in candidates):
            raise ValueError("Self or nonexistent candidate")
        rankings[user] = candidates
if set(rankings) != users:
    raise ValueError("Result user universe does not match input")
ordered = sorted(users)
sample = random.Random(20261103).sample(ordered, min(args.samples, len(users)))
for user in sample:
    scores = Counter()
    for target in follows[user]:
        for candidate in incoming[target]:
            if candidate != user:
                scores[candidate] += 1
    expected = sorted(scores, key=lambda v: (-scores[v], v))[:10]
    for candidate in ordered[:11]:
        if len(expected) == min(10,len(users)-1):
            break
        if candidate != user and candidate not in expected:
            expected.append(candidate)
    if rankings[user] != expected:
        raise ValueError("Ranking mismatch for %d: actual=%r expected=%r" % (user, rankings[user], expected))
result = {"users_checked_for_presence_and_format": len(users),
          "sampled_users_checked_for_exact_top10": len(sample),
          "sampling_seed": 20261103,
          "independent_oracle": "deduplicated followee sets + inverted-index counting per sampled user",
          "ranking_mismatches": 0,
          "result_sha256": hashlib.sha256(Path(args.results).read_bytes()).hexdigest(),
          "edge_order": args.edge_order}
Path(args.output).write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
