#!/usr/bin/env python3
"""Exact common-followee Top-K using six Hadoop Streaming jobs.

All IDs are nonnegative decimal integers, with arbitrary precision.
No third-party Python packages are needed on the cluster.
"""
import argparse
import gzip
import heapq
import itertools
import json
import sys
import tempfile


def uid(text):
    if not text or not text.isascii() or not text.isdecimal():
        raise ValueError("Expected a nonnegative decimal user ID: %r" % text)
    return str(int(text))


def source_records(lines, fmt="auto", edge_order="follower-followee", undirected=False):
    """Yield (followee, follower) edges and (user, None) node markers."""
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            mode = ("adjacency" if ":" in line else "edges") if fmt == "auto" else fmt
            if mode == "adjacency":
                head, tail = line.split(":", 1)
                followee = uid(head.strip())
                yield followee, None
                for follower in tail.split():
                    follower = uid(follower)
                    yield followee, follower
                    if undirected and follower != followee:
                        yield follower, followee
            else:
                fields = line.split()
                if len(fields) != 2:
                    raise ValueError("Edge input must contain exactly two IDs")
                a, b = map(uid, fields)
                follower, followee = (a, b) if edge_order == "follower-followee" else (b, a)
                yield followee, follower
                if undirected and follower != followee:
                    yield follower, followee
        except ValueError as exc:
            raise ValueError("Input line %d: %s" % (number, exc)) from exc


def normalize(args, lines):
    for followee, follower in source_records(lines, args.format, args.edge_order, args.undirected):
        yield "U\t%s\t-\t1" % followee
        if follower is not None:
            yield "U\t%s\t-\t1" % follower
            yield "E\t%s\t%s\t1" % (followee, follower)


def unique(args, lines):
    previous = None
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        if len(fields) != 4 or fields[0] not in ("E", "U"):
            raise ValueError("Malformed dedup record")
        key = tuple(fields[:3])
        if key != previous:
            yield "\t".join((*key, "1"))
            previous = key


def universe_map(args, lines):
    # A mapper/combiner only needs its K+1 numerically smallest distinct IDs.
    smallest = set()
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        if fields[0] == "U":
            smallest.add(int(fields[1]))
            if len(smallest) > args.k + 1:
                smallest.remove(max(smallest))
    for user in sorted(smallest):
        yield "G\t%d" % user


def universe_reduce(args, lines):
    smallest = set()
    for line in lines:
        _, user = line.rstrip("\n").split("\t")
        smallest.add(int(user))
        if len(smallest) > args.k + 1:
            smallest.remove(max(smallest))
    for user in sorted(smallest):
        yield "%d\t0" % user


def counter(name, value):
    print("reporter:counter:HW,%s,%d" % (name, value), file=sys.stderr)


def blocks(args, lines):
    # Input is partitioned by (kind, followee) and sorted by the full key.
    records = (line.rstrip("\n").split("\t") for line in lines)
    for (kind, user), group in itertools.groupby(records, key=lambda x: (x[0], x[1])):
        if kind == "U":
            for _ in group:
                pass
            counter("Users", 1)
            yield "U\t%s" % user
            continue
        if kind != "E":
            raise ValueError("Unexpected block input kind: " + kind)
        # Spool one followee's blocks to disk; do not hold its whole list in RAM.
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as spool:
            current, degree, count = [], 0, 0
            for row in group:
                current.append(row[2])
                degree += 1
                if len(current) == args.block_size:
                    spool.write(" ".join(current) + "\n")
                    current = []
                    count += 1
            if current:
                spool.write(" ".join(current) + "\n")
                count += 1
            counter("Edges", degree)
            counter("CandidatePairs", degree * (degree - 1) // 2)
            counter("ReplicatedFollowerIDs", degree * count)
            spool.seek(0)
            for index, payload in enumerate(spool):
                yield "B\t%s\t%d\t%d\t%s" % (user, index, count, payload.rstrip("\n"))


def replicate(args, lines):
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        if fields[0] == "U":
            yield "U\t%s\t0\t0\t0\t-" % fields[1]
            continue
        _, followee, block, total, payload = fields
        block, total = int(block), int(total)
        for other in range(total):
            left, right = sorted((block, other))
            side = "L" if block <= other else "R"
            yield "P\t%s\t%d\t%d\t%s\t%s" % (followee, left, right, side, payload)


def pairs(args, lines):
    records = (line.rstrip("\n").split("\t") for line in lines)
    for key, group in itertools.groupby(records, key=lambda x: tuple(x[:4])):
        if key[0] == "U":
            for _ in group:
                pass
            yield "U\t%s\t-\t1" % key[1]
            continue
        left, right = None, None
        for fields in group:
            if fields[4] == "L" and left is None:
                left = fields[5].split()
            elif fields[4] == "R" and right is None:
                right = fields[5].split()
            else:
                raise ValueError("Duplicate or invalid block side")
        if left is None or (key[2] != key[3] and right is None):
            raise ValueError("Missing follower block")
        iterator = itertools.combinations(left, 2) if key[2] == key[3] else itertools.product(left, right)
        for u, v in iterator:
            if int(u) > int(v):
                u, v = v, u
            if u == v:
                raise ValueError("Duplicate edge escaped deduplication")
            yield "P\t%s\t%s\t1" % (u, v)


def sums(args, lines):
    records = (line.rstrip("\n").split("\t") for line in lines)
    for key, group in itertools.groupby(records, key=lambda x: tuple(x[:3])):
        count = sum(int(fields[3]) for fields in group)
        yield "\t".join((*key, str(count if key[0] == "P" else 1)))


def rank_map(args, lines):
    for line in lines:
        kind, u, v, score = line.rstrip("\n").split("\t")
        if kind == "U":
            yield "%s\t0\t%s\t1" % (u, u)
        else:
            score = int(score)
            yield "%s\t%d\t%s\t1" % (u, -score, v)
            yield "%s\t%d\t%s\t1" % (v, -score, u)


def rank_reduce(args, lines):
    with open(args.universe, encoding="utf-8") as handle:
        universe = [row.split()[0] for row in handle if row.strip()]
    if len(universe) > args.k + 1:
        raise ValueError("Universe file must contain at most K+1 users")
    records = (line.rstrip("\n").split("\t") for line in lines)
    for user, group in itertools.groupby(records, key=lambda x: x[0]):
        selected = []
        for row in group:
            # Shuffle has ordered candidates by (-score, numerical candidate ID).
            if int(row[1]) < 0 and len(selected) < args.k:
                if row[2] == user:
                    raise ValueError("Self candidate is not allowed")
                selected.append(row[2])
        # Literal EVERY-user Top-K: fill zero-score places deterministically.
        for other in universe:
            if len(selected) == args.k:
                break
            if other != user and other not in selected:
                selected.append(other)
        separator = "\t" if getattr(args, "hadoop_output", False) else ":"
        yield user + separator + " ".join(selected)


OPERATIONS = {"normalize": normalize, "unique": unique,
              "universe-map": universe_map, "universe-reduce": universe_reduce,
              "blocks": blocks, "replicate": replicate, "pairs": pairs,
              "sums": sums, "rank-map": rank_map, "rank-reduce": rank_reduce}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=OPERATIONS)
    parser.add_argument("--format", choices=["auto", "adjacency", "edges"], default="auto")
    parser.add_argument("--edge-order", choices=["follower-followee", "followee-follower"], default="follower-followee")
    parser.add_argument("--undirected", action="store_true")
    parser.add_argument("--block-size", type=int, default=512)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--universe", default="universe.txt")
    parser.add_argument("--hadoop-output", action="store_true", help="Emit key/value for colon-separated TextOutputFormat")
    args = parser.parse_args()
    if args.block_size < 1 or args.k < 1:
        parser.error("block-size and k must be positive")
    try:
        for row in OPERATIONS[args.operation](args, sys.stdin):
            sys.stdout.write(row + "\n")
    except (ValueError, IndexError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
