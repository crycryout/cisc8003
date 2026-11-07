#!/usr/bin/env python3
"""Independent disk-backed source audit, exact sampled oracle and streaming export.

No ranking code is imported from the Hadoop implementation. Decimal IDs remain
strings/Python integers; SQLite stores only dense integer node indices in edges.
"""
import argparse
from collections import OrderedDict
import datetime
import gzip
import hashlib
import heapq
import json
import os
from pathlib import Path
import random
import re
import resource
import sqlite3
import sys
import time


def canonical(value):
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError("Expected an ASCII nonnegative decimal ID: %r" % value)
    return str(int(value))


def parse_line(raw, fmt, order):
    line = raw.strip()
    if not line or line.startswith("#"):
        return
    if fmt == "edges":
        fields = line.split()
        if len(fields) != 2:
            raise ValueError("An edge line must contain exactly two IDs")
        left, right = map(canonical, fields)
        yield (left, right) if order == "follower-followee" else (right, left)
    else:
        head, tail = line.split(":", 1)
        head = canonical(head.strip())
        yield head, None
        for value in tail.split():
            yield canonical(value), head


def text_input(path):
    return gzip.open(path, "rt", encoding="utf-8") if str(path).endswith(".gz") else open(path, encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def connect(database, cache_mib=256, readonly=False):
    if readonly:
        con = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    else:
        con = sqlite3.connect(database)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA cache_size=%d" % (-1024 * cache_mib))
    con.execute("PRAGMA temp_store=FILE")
    con.execute("PRAGMA mmap_size=0")
    return con


def memory_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def build_index(input_path, database, fmt="edges", order="follower-followee", cache_mib=256, resume=False):
    started = time.monotonic()
    source_hash = sha256(input_path)
    existed = Path(database).exists()
    con = connect(database, cache_mib)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users (node INTEGER PRIMARY KEY, uid TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS edges (src INTEGER NOT NULL, dst INTEGER NOT NULL,
                                         PRIMARY KEY(src,dst)) WITHOUT ROWID;
    """)
    old = dict(con.execute("SELECT key,value FROM metadata"))
    identity = {"source_sha256": source_hash, "format": fmt, "edge_order": order}
    if old:
        for key, value in identity.items():
            if old.get(key) != value:
                raise ValueError("Existing audit index belongs to different input or direction")
        if old.get("status") == "complete":
            return json.loads(old["statistics"])
        if not resume:
            raise ValueError("Incomplete audit index exists; use --resume after inspecting its checkpoint")
    elif existed:
        raise ValueError("Refusing an existing database without this audit's metadata")
    for key, value in identity.items():
        con.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, value))
    con.execute("INSERT OR REPLACE INTO metadata VALUES ('status','building')")
    con.commit()
    users = {uid: node for node, uid in con.execute("SELECT node,uid FROM users")}
    checkpoint = int(old.get("committed_line", 0))
    edge_records = int(old.get("edge_records", 0))
    nonempty_lines = int(old.get("nonempty_lines", 0))
    max_digits = max(map(len, users), default=0)
    pending_users, pending_edges = [], []
    last_commit = checkpoint

    def node(uid):
        nonlocal max_digits
        found = users.get(uid)
        if found is None:
            found = len(users)
            users[uid] = found
            pending_users.append((found, uid))
            max_digits = max(max_digits, len(uid))
        return found

    def flush():
        if pending_users:
            con.executemany("INSERT INTO users VALUES (?,?)", pending_users)
            pending_users.clear()
        if pending_edges:
            con.executemany("INSERT OR IGNORE INTO edges VALUES (?,?)", pending_edges)
            pending_edges.clear()

    def commit(number):
        flush()
        for key, value in [("committed_line", number), ("edge_records", edge_records), ("nonempty_lines", nonempty_lines)]:
            con.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, str(value)))
        con.commit()
        print("INDEX checkpoint line=%d edge_records=%d users=%d peak_rss_mib=%.1f" % (number, edge_records, len(users), memory_mib()), flush=True)

    with text_input(input_path) as handle:
        last_line = checkpoint
        for number, raw in enumerate(handle, 1):
            last_line = number
            if number <= checkpoint:
                continue
            if raw.strip() and not raw.lstrip().startswith("#"):
                nonempty_lines += 1
            for source, target in parse_line(raw, fmt, order):
                src = node(source)
                if target is not None:
                    pending_edges.append((src, node(target)))
                    edge_records += 1
                if len(pending_edges) >= 20000:
                    flush()
            # Checkpoint only at a whole-line boundary, including adjacency lines.
            if number - last_commit >= 1000000:
                commit(number)
                last_commit = number
        commit(last_line)
    con.execute("CREATE INDEX IF NOT EXISTS edge_by_dst ON edges(dst,src)")
    con.commit()
    counts = {"indegree": {}, "outdegree": {}}
    max_degrees = {}
    top = {}
    pairs, replicated = 0, 0
    for kind, column in [("indegree", "dst"), ("outdegree", "src")]:
        degrees = []
        for index, degree in con.execute("SELECT %s,COUNT(*) FROM edges GROUP BY %s" % (column, column)):
            counts[kind][degree] = counts[kind].get(degree, 0) + 1
            degrees.append((degree, index))
            if kind == "indegree":
                pairs += degree * (degree - 1) // 2
                replicated += degree * ((degree + 511) // 512)
        counts[kind][0] = len(users) - len(degrees)
        max_degrees[kind] = max((d for d, _ in degrees), default=0)
        numeric = {index: int(uid) for uid, index in users.items()}
        top[kind] = [{"user": str(numeric[index]), "degree": degree} for degree, index in heapq.nsmallest(20, degrees, key=lambda x: (-x[0], numeric[x[1]]))]
    unique_edges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    stats = {**identity, "source_file": Path(input_path).name, "source_bytes": Path(input_path).stat().st_size,
             "nonempty_noncomment_lines": nonempty_lines, "edge_records": edge_records,
             "unique_directed_edges": unique_edges, "duplicate_edge_records": edge_records - unique_edges,
             "users": len(users), "self_edges": con.execute("SELECT COUNT(*) FROM edges WHERE src=dst").fetchone()[0],
             "maximum_id_digits": max_digits, "maximum_indegree": max_degrees["indegree"],
             "maximum_outdegree": max_degrees["outdegree"], "candidate_pairs": pairs,
             "replicated_follower_ids_at_block_size_512": replicated,
             "degree_histograms": {key: {str(d): n for d, n in sorted(value.items())} for key, value in counts.items()},
             "highest_degrees": top, "sqlite_cache_mib": cache_mib, "peak_rss_mib": memory_mib(),
             "elapsed_s": time.monotonic() - started, "implementation": "independent canonical source parser + SQLite unique directed edges"}
    con.execute("INSERT OR REPLACE INTO metadata VALUES ('statistics',?)", (json.dumps(stats),))
    con.execute("INSERT OR REPLACE INTO metadata VALUES ('status','complete')")
    con.commit()
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    return stats


def user_arrays(con):
    values = list(con.execute("SELECT node,uid FROM users ORDER BY node"))
    assert all(node == i for i, (node, _) in enumerate(values))
    uids = [uid for _, uid in values]
    return uids, {uid: i for i, uid in enumerate(uids)}, [int(uid) for uid in uids]


def expected_rank(con, user, uids, numeric, smallest, k):
    query = """SELECT candidate.src,COUNT(*) FROM edges AS mine
               JOIN edges AS candidate INDEXED BY edge_by_dst ON candidate.dst=mine.dst
               WHERE mine.src=? AND candidate.src<>? GROUP BY candidate.src"""
    positive = heapq.nsmallest(k, con.execute(query, (user, user)), key=lambda x: (-x[1], numeric[x[0]]))
    selected = [index for index, _ in positive]
    for index in smallest:
        if len(selected) >= min(k, len(uids) - 1):
            break
        if index != user and index not in selected:
            selected.append(index)
    return [uids[index] for index in selected], len(positive)


def result_record(raw):
    text = raw.decode("utf-8").rstrip("\r\n")
    user, tail = text.split(":", 1)
    return canonical(user), [canonical(value) for value in tail.split()]


def validate(database, results, samples=1000, seed=20261107, k=10, cache_mib=256):
    started = time.monotonic()
    con = connect(database, cache_mib, readonly=True)
    if dict(con.execute("SELECT key,value FROM metadata")).get("status") != "complete":
        raise ValueError("A completed source audit is required")
    uids, lookup, numeric = user_arrays(con)
    total = len(uids)
    con.execute("CREATE TEMP TABLE audited_results(node INTEGER PRIMARY KEY, candidates TEXT NOT NULL)")
    digest = hashlib.sha256()
    rows, size = 0, 0
    with open(results, "rb") as handle:
        for number, raw in enumerate(handle, 1):
            digest.update(raw)
            size += len(raw)
            user, candidates = result_record(raw)
            if user not in lookup:
                raise ValueError("Extra result user at line %d: %s" % (number, user))
            if len(candidates) != min(k, max(0, total - 1)) or len(set(candidates)) != len(candidates):
                raise ValueError("Wrong candidate count or duplicate at line %d" % number)
            if user in candidates or any(value not in lookup for value in candidates):
                raise ValueError("Self or nonexistent candidate at line %d" % number)
            try:
                con.execute("INSERT INTO audited_results VALUES (?,?)", (lookup[user], " ".join(candidates)))
            except sqlite3.IntegrityError as exc:
                raise ValueError("Duplicate result user: " + user) from exc
            rows += 1
    missing = con.execute("SELECT COUNT(*) FROM users u LEFT JOIN audited_results r ON u.node=r.node WHERE r.node IS NULL").fetchone()[0]
    if missing:
        raise ValueError("Missing %d source users" % missing)
    groups = {}
    groups["fixed_seed_random"] = random.Random(seed).sample(range(total), min(samples, total))
    ordered = sorted(range(total), key=numeric.__getitem__)
    groups["numeric_boundaries"] = ordered[:10] + ordered[-10:]
    for kind, column in [("highest_outdegree", "src"), ("highest_indegree", "dst")]:
        groups[kind] = [row[0] for row in con.execute("SELECT %s,COUNT(*) AS degree FROM edges GROUP BY %s ORDER BY degree DESC,%s LIMIT 10" % (column, column, column))]
    groups["zero_outdegree_zero_positive"] = [row[0] for row in con.execute("SELECT u.node FROM users u WHERE NOT EXISTS (SELECT 1 FROM edges e WHERE e.src=u.node) ORDER BY u.node LIMIT 20")]
    groups["followers_of_popular_targets"] = []
    for target in groups["highest_indegree"]:
        groups["followers_of_popular_targets"] += [row[0] for row in con.execute("SELECT src FROM edges INDEXED BY edge_by_dst WHERE dst=? ORDER BY src LIMIT 3", (target,))]
    chosen = sorted(set(index for group in groups.values() for index in group), key=numeric.__getitem__)
    mismatches = []
    for number, index in enumerate(chosen, 1):
        expected, positives = expected_rank(con, index, uids, numeric, ordered[:k + 1], k)
        actual = con.execute("SELECT candidates FROM audited_results WHERE node=?", (index,)).fetchone()[0].split()
        if actual != expected:
            mismatches.append({"user": uids[index], "actual": actual, "expected": expected})
        if number % 100 == 0:
            print("VALIDATE exact_samples=%d/%d mismatches=%d peak_rss_mib=%.1f" % (number, len(chosen), len(mismatches), memory_mib()), flush=True)
    con.close()
    return {"valid": not mismatches, "scope": "all-user coverage/format/candidate validity plus independent exact samples; not all-user independent ranking recomputation",
            "users_checked_for_presence_and_format": total, "output_rows": rows, "missing_users": missing,
            "extra_users": 0, "duplicate_users": 0, "fixed_seed_random_samples": len(groups["fixed_seed_random"]),
            "independent_exact_sample_users": len(chosen), "seed": seed,
            "sample_groups": {key: [uids[i] for i in value] for key, value in groups.items()},
            "ranking_mismatches": len(mismatches), "mismatch_examples": mismatches[:20],
            "result_bytes": size, "result_sha256": digest.hexdigest(), "validator_sha256": sha256(__file__),
            "sqlite_cache_mib": cache_mib, "peak_rss_mib": memory_mib(), "elapsed_s": time.monotonic() - started,
            "oracle": "deduplicated raw directed-edge SQLite self join on shared followee, exact integer counts, numeric-ID tie order and independent zero fill"}


def export_suffixes(database, results, output):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    for suffix in range(1000):
        (root / ("%03d.txt" % suffix)).touch()
    handles = OrderedDict()
    hashes = [hashlib.sha256() for _ in range(1000)]
    counts, sizes = [0] * 1000, [0] * 1000
    source_hash = hashlib.sha256()
    try:
        with open(results, "rb") as source:
            for raw in source:
                user, _ = result_record(raw)
                bucket = int(user) % 1000
                source_hash.update(raw)
                if bucket in handles:
                    handle = handles.pop(bucket)
                else:
                    if len(handles) >= 32:
                        _, old = handles.popitem(last=False)
                        old.close()
                    handle = (root / ("%03d.txt" % bucket)).open("ab")
                handles[bucket] = handle
                handle.write(raw)
                hashes[bucket].update(raw)
                counts[bucket] += 1
                sizes[bucket] += len(raw)
    finally:
        for handle in handles.values():
            handle.close()
    con = connect(database, readonly=True)
    con.execute("CREATE TEMP TABLE exported_users(node INTEGER PRIMARY KEY)")
    manifests = []
    for suffix in range(1000):
        path = root / ("%03d.txt" % suffix)
        check = hashlib.sha256()
        lines = 0
        with path.open("rb") as handle:
            for raw in handle:
                user, _ = result_record(raw)
                if int(user) % 1000 != suffix:
                    raise ValueError("Wrong suffix partition")
                found = con.execute("SELECT node FROM users WHERE uid=?", (user,)).fetchone()
                if found is None:
                    raise ValueError("Export contains an extra source user")
                con.execute("INSERT INTO exported_users VALUES (?)", found)
                check.update(raw)
                lines += 1
        assert check.hexdigest() == hashes[suffix].hexdigest() and lines == counts[suffix] and path.stat().st_size == sizes[suffix]
        manifests.append({"file": path.name, "rows": lines, "bytes": sizes[suffix], "sha256": check.hexdigest()})
    missing = con.execute("SELECT COUNT(*) FROM users u LEFT JOIN exported_users e ON u.node=e.node WHERE e.node IS NULL").fetchone()[0]
    assert missing == 0
    expected = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert sum(counts) == expected
    con.close()
    return {"files": 1000, "total_users": sum(counts), "source_result_sha256": source_hash.hexdigest(),
            "source_user_set_identical": True, "missing_users": 0, "duplicate_users": 0,
            "maximum_open_output_files": 32, "peak_rss_mib": memory_mib(), "shards": manifests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    build = sub.add_parser("build")
    build.add_argument("--input", required=True)
    build.add_argument("--database", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--format", choices=["edges", "adjacency"], required=True)
    build.add_argument("--edge-order", choices=["follower-followee", "followee-follower"], default="follower-followee")
    build.add_argument("--cache-mib", type=int, default=256)
    build.add_argument("--resume", action="store_true")
    audit = sub.add_parser("validate")
    audit.add_argument("--database", required=True)
    audit.add_argument("--results", required=True)
    audit.add_argument("--output", required=True)
    audit.add_argument("--samples", type=int, default=1000)
    audit.add_argument("--seed", type=int, default=20261107)
    audit.add_argument("--k", type=int, default=10)
    audit.add_argument("--cache-mib", type=int, default=256)
    export = sub.add_parser("export")
    export.add_argument("--database", required=True)
    export.add_argument("--results", required=True)
    export.add_argument("--directory", required=True)
    export.add_argument("--output", required=True)
    args = parser.parse_args()
    if getattr(args, "cache_mib", 256) < 1 or getattr(args, "samples", 1) < 1 or getattr(args, "k", 1) < 1:
        parser.error("cache, samples and k must be positive")
    try:
        if args.operation == "build":
            result = build_index(args.input, args.database, args.format, args.edge_order, args.cache_mib, args.resume)
        elif args.operation == "validate":
            result = validate(args.database, args.results, args.samples, args.seed, args.k, args.cache_mib)
        else:
            result = export_suffixes(args.database, args.results, args.directory)
    except Exception as exc:
        write_json(args.output, {"valid": False, "operation": args.operation, "error": str(exc), "exception": type(exc).__name__, "peak_rss_mib": memory_mib()})
        raise
    write_json(args.output, result)
    print(json.dumps({key: value for key, value in result.items() if key not in ("degree_histograms", "sample_groups", "shards")}, indent=2))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
