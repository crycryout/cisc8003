#!/usr/bin/env python3
"""Compare exact per-user rankings, ignoring only the order of users across part files."""
import argparse
import gzip
import json
from pathlib import Path
import sys


def load(path):
    result = {}
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as handle:
        for number, raw in enumerate(handle, 1):
            user, candidates = raw.rstrip("\n").split(":", 1)
            user = int(user)
            values = tuple(int(item) for item in candidates.split())
            if user < 0 or any(item < 0 for item in values):
                raise ValueError("Negative ID at line %d" % number)
            if user in result or user in values or len(set(values)) != len(values):
                raise ValueError("Duplicate user, self recommendation or duplicate candidate at line %d" % number)
            result[user] = values
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--actual", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    reference, actual = load(args.reference), load(args.actual)
    missing = sorted(reference.keys() - actual.keys())
    extra = sorted(actual.keys() - reference.keys())
    changed = sorted(user for user in reference.keys() & actual.keys() if reference[user] != actual[user])
    success = not (missing or extra or changed)
    result = {"reference_users": len(reference), "actual_users": len(actual),
              "missing_users": len(missing), "extra_users": len(extra),
              "ranking_mismatches": len(changed), "identical_rankings": success,
              "missing_user_examples": missing[:10], "extra_user_examples": extra[:10],
              "mismatched_user_examples": changed[:10],
              "comparison": "Exact candidate order per numeric user; user-line order ignored"}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    print(text, end="")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
