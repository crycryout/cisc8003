#!/usr/bin/env python3
"""Run Q1(b)/(c), collect real timings and check output equivalence."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from metrics import collect, write_csv


def output_digest(hdfs_output, evidence_dir):
    # Sort on disk; no need to hold all distinct words in Python memory.
    with tempfile.TemporaryFile() as sorted_output:
        reader = subprocess.Popen(["hdfs", "dfs", "-cat", hdfs_output + "/part-*"], stdout=subprocess.PIPE)
        sorter = subprocess.Popen(["sort", "-T", str(evidence_dir)], stdin=reader.stdout,
                                  stdout=sorted_output, env={**os.environ, "LC_ALL": "C"})
        reader.stdout.close()
        sort_rc, read_rc = sorter.wait(), reader.wait()
        if read_rc or sort_rc:
            raise RuntimeError("Could not hash word-count output")
        sorted_output.seek(0)
        digest = hashlib.sha256()
        for block in iter(lambda: sorted_output.read(1024 * 1024), b""):
            digest.update(block)
        return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["files", "sweep"], required=True)
    parser.add_argument("--small-input")
    parser.add_argument("--merged-input")
    parser.add_argument("--large-input", help="Single uncompressed HDFS file for controlled input splits")
    parser.add_argument("--output-root", required=True, help="New HDFS directory")
    parser.add_argument("--evidence", required=True, help="New local directory")
    parser.add_argument("--history", default="http://master:19888")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--plan", default="6:1,6:3,12:1,12:3", help="Target mappers:reducers combinations")
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("repetitions must be positive")
    home = os.environ.get("HADOOP_HOME")
    if not home:
        parser.error("Set HADOOP_HOME")
    jar = str(Path(home) / "share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar")
    if not Path(jar).is_file():
        parser.error("Hadoop 3.3.6 examples JAR not found")
    evidence = Path(args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    if subprocess.run(["hdfs", "dfs", "-test", "-e", args.output_root]).returncode == 0:
        parser.error("HDFS output root already exists; choose a new root")
    if args.mode == "files":
        if not args.small_input or not args.merged_input:
            parser.error("files mode needs --small-input and --merged-input")
        settings = [("small", args.small_input, None, 1), ("merged", args.merged_input, None, 1)]
    else:
        if not args.large_input or args.large_input.endswith((".gz", ".zip", ".bz2")):
            parser.error("sweep needs a single UNCOMPRESSED --large-input")
        if subprocess.run(["hdfs", "dfs", "-test", "-f", args.large_input]).returncode != 0:
            parser.error("large-input must be a single HDFS file")
        size = int(subprocess.check_output(["hdfs", "dfs", "-stat", "%b", args.large_input], text=True).strip())
        if size == 0:
            parser.error("Input is empty")
        plan = [tuple(map(int, item.split(":"))) for item in args.plan.split(",")]
        if len(plan) < 4 or any(len(p) != 2 or min(p) < 1 for p in plan) or len(set(plan)) != len(plan):
            parser.error("Use at least four distinct positive mapper:reducer combinations")
        settings = [("m%d_r%d" % (m, r), args.large_input, m, r) for m, r in plan]
    all_rows, digest = [], None
    # Alternate order to reduce a consistent first-run cache advantage.
    for repetition in range(1, args.repetitions + 1):
        ordered = settings if repetition % 2 else list(reversed(settings))
        for label, input_path, target_maps, reducers in ordered:
            run = "%s_rep%d" % (label, repetition)
            run_dir = evidence / run
            run_dir.mkdir()
            cmd = ["hadoop", "jar", jar, "wordcount",
                   "-D", "mapreduce.job.name=hw1-" + run,
                   "-D", "mapreduce.job.reduces=" + str(reducers),
                   "-D", "mapreduce.map.speculative=false",
                   "-D", "mapreduce.reduce.speculative=false",
                   "-D", "mapreduce.map.output.compress=true"]
            split = None
            if target_maps is not None:
                split = math.ceil(size / target_maps)
                cmd += ["-D", "mapreduce.input.fileinputformat.split.minsize=" + str(split),
                        "-D", "mapreduce.input.fileinputformat.split.maxsize=" + str(split)]
            output = args.output_root.rstrip("/") + "/" + run
            cmd += [input_path, output]
            (run_dir / "command.json").write_text(json.dumps(cmd, indent=2))
            started = time.monotonic()
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            chunks = []
            with (run_dir / "console.log").open("w") as log:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                    chunks.append(line)
            if process.wait():
                raise RuntimeError("WordCount failed; see " + str(run_dir / "console.log"))
            client_wall = time.monotonic() - started
            ids = list(dict.fromkeys(re.findall(r"\bjob_\d+_\d+\b", "".join(chunks))))
            if len(ids) != 1:
                raise RuntimeError("Could not identify exactly one job in Hadoop log")
            result = collect(args.history, ids[0], run_dir)
            result.update(setting=label, repetition=repetition, target_mappers=target_maps,
                          split_bytes=split, client_wall_s=client_wall,
                          output_sha256=output_digest(output, evidence))
            if digest is None:
                digest = result["output_sha256"]
            if result["output_sha256"] != digest:
                raise RuntimeError("WordCount outputs disagree; do not compare timings yet")
            all_rows.append(result)
            write_csv(evidence / "timings.csv", all_rows)
    if args.mode == "sweep":
        actual = {(r["actual_mappers"], r["actual_reducers"]) for r in all_rows}
        if len(actual) < 4:
            raise RuntimeError("Fewer than four ACTUAL combinations; adjust --plan or input size and rerun")
    print("Complete. Real task/job statistics:", evidence / "timings.csv")


if __name__ == "__main__":
    main()
