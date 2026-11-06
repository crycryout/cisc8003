#!/usr/bin/env python3
"""Create equivalent small-file and merged-file inputs from extracted TEXT files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", required=True, help="Directory of extracted Shakespeare text files only")
parser.add_argument("--output", required=True, help="New directory outside source")
args = parser.parse_args()
source, output = Path(args.source).resolve(), Path(args.output).resolve()
if not source.is_dir():
    parser.error("source must be an existing directory")
if output == source or source in output.parents:
    parser.error("output must be outside the source directory")
if output.exists():
    parser.error("output already exists; use a new path")
files = sorted(p for p in source.rglob("*") if p.is_file() and not any(part.startswith(".") for part in p.relative_to(source).parts))
if not files:
    parser.error("No input files")
(output / "small").mkdir(parents=True)
manifest = []
with (output / "merged.txt").open("wb") as merged:
    for index, original in enumerate(files):
        if original.suffix.lower() in (".gz", ".zip", ".tar", ".pdf", ".png"):
            parser.error("source must contain text only; found " + str(original))
        target = output / "small" / ("%06d.txt" % index)
        shutil.copyfile(original, target)
        size = target.stat().st_size
        if size:
            with target.open("rb+") as handle:
                handle.seek(-1, 2)
                if handle.read(1) != b"\n":
                    handle.seek(0, 2)
                    handle.write(b"\n")
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
                merged.write(block)
        manifest.append({"source": str(original.relative_to(source)), "copy": target.name,
                         "normalized_bytes": target.stat().st_size, "sha256": digest.hexdigest()})
(output / "manifest.json").write_text(json.dumps({"files": manifest,
    "total_bytes": sum(row["normalized_bytes"] for row in manifest),
    "normalization": "Every nonempty file ends in newline; small and merged contain identical token streams."}, indent=2))
print(json.dumps({"files": len(files), "merged_bytes": (output / "merged.txt").stat().st_size}))
