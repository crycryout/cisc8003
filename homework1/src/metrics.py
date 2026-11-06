#!/usr/bin/env python3
"""Collect real Hadoop JobHistory REST timings, preserving raw evidence."""
import argparse
import csv
import json
from pathlib import Path
import statistics
import time
import urllib.error
import urllib.request


def fetch_json(url, attempts=25):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2)


def stats(values):
    if not values:
        return {"max_s": None, "min_s": None, "avg_s": None}
    return {"max_s": max(values), "min_s": min(values), "avg_s": statistics.mean(values)}


def summarize(job, tasks):
    if job["state"] != "SUCCEEDED":
        raise ValueError("Job did not succeed: " + job["state"])
    if any(t["state"] != "SUCCEEDED" for t in tasks):
        raise ValueError("Some tasks did not succeed")
    maps = [t for t in tasks if t["type"] == "MAP"]
    reduces = [t for t in tasks if t["type"] == "REDUCE"]
    if len(maps) != job["mapsTotal"] or len(reduces) != job["reducesTotal"]:
        raise ValueError("Incomplete task response; refusing to report partial timing statistics")
    result = {"job_id": job["id"], "state": job["state"],
              "actual_mappers": len(maps), "actual_reducers": len(reduces),
              "job_s": (job["finishTime"] - job["startTime"]) / 1000.0,
              "failed_map_attempts": job.get("failedMapAttempts", 0),
              "failed_reduce_attempts": job.get("failedReduceAttempts", 0)}
    for kind, group in (("map", maps), ("reduce", reduces)):
        timings = [(task["finishTime"] - task["startTime"]) / 1000.0 for task in group]
        if any(t < 0 for t in timings):
            raise ValueError("Invalid task timestamp")
        for name, value in stats(timings).items():
            result[kind + "_" + name] = value
    return result


def collect(base_url, job_id, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    base = base_url.rstrip("/") + "/ws/v1/history/mapreduce/jobs/" + job_id
    raw_job = fetch_json(base)
    raw_tasks = fetch_json(base + "/tasks")
    (directory / "job.json").write_text(json.dumps(raw_job, indent=2))
    (directory / "tasks.json").write_text(json.dumps(raw_tasks, indent=2))
    task_list = (raw_tasks.get("tasks") or {}).get("task", [])
    result = summarize(raw_job["job"], task_list)
    # Counters help diagnose spill, skew, I/O and the block-pair cost.
    raw_counters = fetch_json(base + "/counters")
    (directory / "counters.json").write_text(json.dumps(raw_counters, indent=2))
    (directory / "summary.json").write_text(json.dumps(result, indent=2))
    return result


def write_csv(path, rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://master:19888")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(collect(args.base_url, args.job_id, args.output), indent=2))
