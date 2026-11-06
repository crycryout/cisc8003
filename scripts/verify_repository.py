#!/usr/bin/env python3
"""Verify the recorded repository snapshot without downloading or running cluster jobs."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "docs/IMPORT_MANIFEST.json").read_text())
errors = []
for row in manifest["files"]:
    path = (root / row["path"]).resolve()
    if root not in path.parents or not path.is_file():
        errors.append({"path": row["path"], "error": "missing file or path outside repository"})
        continue
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if path.stat().st_size != row["bytes"] or digest.hexdigest() != row["sha256"]:
        errors.append({"path": row["path"], "error": "content differs from imported snapshot"})
print(json.dumps({"checked_files": len(manifest["files"]), "mismatches": len(errors),
                  "errors": errors[:20],
                  "scope": "Repository byte integrity, not a cluster benchmark"}, indent=2))
sys.exit(bool(errors))
