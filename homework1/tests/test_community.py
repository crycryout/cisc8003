#!/usr/bin/env python3
"""Independent brute-force oracle, plus simulated multi-reducer shuffles.

This validates Python stage semantics, not Hadoop's Java Streaming protocol.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import community as c


def call(operation, rows, args):
    return list(c.OPERATIONS[operation](args, (row + "\n" for row in rows)))


def shuffle_reduce(rows, operation, args, key_fields, partition_fields=None,
                   numeric=False, reducers=3):
    partition_fields = partition_fields or key_fields
    buckets = [[] for _ in range(reducers)]
    for row in rows:
        fields = row.split("\t")
        partition = "\t".join(fields[:partition_fields])
        index = int.from_bytes(hashlib.md5(partition.encode()).digest()[:4], "big") % reducers
        buckets[index].append(row)
    result = []
    for bucket in buckets:
        key = (lambda row: tuple(int(x) for x in row.split("\t")[:key_fields])) if numeric else (
            lambda row: tuple(row.split("\t")[:key_fields]))
        bucket.sort(key=key)
        result.extend(call(operation, bucket, args))
    return result


def pipeline(text, k=10, block_size=3, fmt="auto", edge_order="follower-followee", undirected=False):
    args = argparse.Namespace(k=k, block_size=block_size, format=fmt,
                              edge_order=edge_order, undirected=undirected)
    data = text.splitlines()
    with contextlib.redirect_stderr(io.StringIO()):
        normalized = call("normalize", data, args)
        dedup = shuffle_reduce(normalized, "unique", args, 3)
        universe = call("universe-map", dedup, args)
        universe = call("universe-reduce", sorted(universe), args)
        block_records = shuffle_reduce(dedup, "blocks", args, 3, 2)
        replicated = call("replicate", block_records, args)
        pair_records = shuffle_reduce(replicated, "pairs", args, 5, 4)
        # A combiner may run zero, one, or multiple times.
        combined = shuffle_reduce(pair_records, "sums", args, 3)
        scores = shuffle_reduce(combined, "sums", args, 3)
        candidates = call("rank-map", scores, args)
        with tempfile.TemporaryDirectory() as directory:
            args.universe = str(Path(directory) / "universe.txt")
            Path(args.universe).write_text("\n".join(universe) + "\n")
            ranked = shuffle_reduce(candidates, "rank-reduce", args, 3, 1, True)
    ranks = {row.split(":")[0]: row.split(":")[1].split() for row in ranked}
    return ranks, scores


def oracle(text, k=10, fmt="auto", edge_order="follower-followee", undirected=False):
    # Intentionally independent parsing and similarity computation.
    followees = {}
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        if fmt == "adjacency" or (fmt == "auto" and ":" in raw):
            target, rest = raw.split(":", 1)
            target = str(int(target))
            followees.setdefault(target, set())
            edges = [(str(int(source)), target) for source in rest.split()]
        else:
            a, b = [str(int(x)) for x in raw.split()]
            edges = [(a, b) if edge_order == "follower-followee" else (b, a)]
        for source, target in edges:
            followees.setdefault(target, set())
            followees.setdefault(source, set()).add(target)
            if undirected:
                followees[target].add(source)
    result = {}
    for user, follows in followees.items():
        candidates = [v for v in followees if v != user]
        candidates.sort(key=lambda v: (-len(follows & followees[v]), int(v)))
        result[user] = candidates[:k]
    return result


class CommunityTests(unittest.TestCase):
    def test_assignment_figure(self):
        text = (ROOT / "data/figure_numeric.txt").read_text()
        ranks, scores = pipeline(text)
        self.assertEqual(ranks, oracle(text))
        self.assertIn("P\t1\t2\t2", scores)
        self.assertEqual(ranks["1"], ["2", "3", "5", "4"])

    def test_duplicate_edges_and_lines(self):
        text = "100:1 1 2 2\n100:1 2\n200:2 3\n300:\n"
        for block_size in (1, 2, 512):
            self.assertEqual(pipeline(text, block_size=block_size)[0], oracle(text))

    def test_zero_similarity_and_followee_only_users(self):
        text = "9:1\n8:2\n7:\n6:\n"
        self.assertEqual(pipeline(text, k=3)[0], oracle(text, k=3))

    def test_empty_and_single_user(self):
        self.assertEqual(pipeline("")[0], {})
        self.assertEqual(pipeline("7:\n")[0], {"7": []})

    def test_large_numeric_ids_and_leading_zeros(self):
        text = "9999999999999999999999999999:2 11 100\n001:2 11\n2:0001\n"
        self.assertEqual(pipeline(text, k=3)[0], oracle(text, k=3))

    def test_edge_direction_and_undirected_mode(self):
        text = "1 8\n2 8\n3 9\n"
        for order in ("follower-followee", "followee-follower"):
            for undirected in (False, True):
                self.assertEqual(pipeline(text, fmt="edges", edge_order=order, undirected=undirected)[0],
                                 oracle(text, fmt="edges", edge_order=order, undirected=undirected))

    def test_random_graphs(self):
        rng = random.Random(20261103)
        for case in range(100):
            n = rng.randint(1, 32)
            ids = rng.sample(range(1, 10000), n)
            lines = []
            for target in ids:
                followers = [u for u in ids if rng.random() < 0.18]
                if followers and rng.random() < .5:
                    followers.append(followers[0])
                lines.append(str(target) + ":" + " ".join(map(str, followers)))
            rng.shuffle(lines)
            text = "\n".join(lines)
            k, block = rng.randint(1, 12), rng.randint(1, 6)
            with self.subTest(case=case, k=k, block=block):
                self.assertEqual(pipeline(text, k=k, block_size=block)[0], oracle(text, k=k))

    def test_high_degree_blocking(self):
        # 128 followers -> 8,128 contributions, divided into 7-user blocks.
        text = "1000:" + " ".join(map(str, range(1, 129))) + "\n"
        self.assertEqual(pipeline(text, block_size=7)[0], oracle(text))

    def test_invalid_ids_fail(self):
        args = argparse.Namespace(format="auto", edge_order="follower-followee", undirected=False)
        for text in ("1:x", "-1:2", "1 2 3"):
            with self.assertRaises(ValueError):
                call("normalize", [text], args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
