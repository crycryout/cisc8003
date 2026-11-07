import contextlib
import importlib.util
import io
from pathlib import Path
import random
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('graph_audit', Path(__file__).parents[1] / 'src/graph_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def reference(edges, users, k=10):
    following = {u: set() for u in users}
    for source, target in edges:
        following[source].add(target)
    return {u: sorted(users - {u}, key=lambda v: (-len(following[u] & following[v]), v))[:k] for u in users}


def write_result(path, rankings):
    path.write_text(''.join(str(u) + ':' + ' '.join(map(str, candidates)) + '\n' for u, candidates in rankings.items()))


class GraphAuditTests(unittest.TestCase):
    def make_index(self, root, content, fmt='edges', order='follower-followee'):
        source, database = root / 'input.txt', root / 'source.sqlite'
        source.write_text(content)
        with contextlib.redirect_stdout(io.StringIO()):
            stats = audit.build_index(source, database, fmt, order, cache_mib=8)
        return source, database, stats

    def test_random_directed_graphs_against_set_intersections(self):
        rng = random.Random(20261107)
        for number in range(20):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                users = set(range(rng.randrange(1, 17)))
                edges = [(u, v) for u in users for v in users if rng.random() < .18]
                # Explicit empty adjacency heads preserve completely isolated users.
                incoming = {u: [] for u in users}
                for u, v in edges:
                    incoming[v].append(u)
                content = ''.join(str(u) + ':' + ' '.join(map(str, incoming[u] * 2)) + '\n' for u in users)
                _, database, stats = self.make_index(root, content, 'adjacency')
                result = root / 'results.txt'
                write_result(result, reference(edges, users))
                with contextlib.redirect_stdout(io.StringIO()):
                    report = audit.validate(database, result)
                self.assertTrue(report['valid'])
                self.assertEqual(report['users_checked_for_presence_and_format'], len(users))
                self.assertEqual(stats['unique_directed_edges'], len(edges))
                self.assertEqual(stats['duplicate_edge_records'], len(edges))

    def test_large_ids_zero_fill_direction_and_streamed_partitions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            a, b, c, d = 1, 2**90 + 7, 2**90 + 8, 10**70
            # Input is followee first; leading zeros and duplicate source records.
            text = '000%d %d\n%d %d\n%d %d\n%d %d\n' % (c, a, c, a, c, b, d, c)
            _, database, stats = self.make_index(root, text, order='followee-follower')
            edges = [(a, c), (b, c), (c, d)]
            result = root / 'result.txt'
            write_result(result, reference(edges, {a, b, c, d}))
            with contextlib.redirect_stdout(io.StringIO()):
                report = audit.validate(database, result)
            self.assertTrue(report['valid'])
            self.assertEqual(stats['duplicate_edge_records'], 1)
            self.assertEqual(stats['candidate_pairs'], 1)
            exported = audit.export_suffixes(database, result, root / 'suffixes')
            self.assertEqual(exported['files'], 1000)
            self.assertEqual(exported['total_users'], 4)
            self.assertTrue(exported['source_user_set_identical'])
            self.assertEqual(len(list((root / 'suffixes').glob('*.txt'))), 1000)
            for path in (root / 'suffixes').glob('*.txt'):
                for line in path.read_text().splitlines():
                    self.assertEqual(int(line.split(':')[0]) % 1000, int(path.stem))

    def test_output_coverage_duplicates_candidates_and_exact_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, database, _ = self.make_index(root, '1 3\n2 3\n3 4\n')
            good = reference([(1, 3), (2, 3), (3, 4)], {1, 2, 3, 4})
            path = root / 'result.txt'
            for content in ['1:2 3 4\n', '1:2 3 4\n1:2 3 4\n', '9:1 2 3\n', '1:1 2 3\n', '1:2 2 3\n']:
                path.write_text(content)
                with self.assertRaises((ValueError, sqlite3.IntegrityError)):
                    audit.validate(database, path)
            good[1] = list(reversed(good[1]))
            write_result(path, good)
            report = audit.validate(database, path)
            self.assertFalse(report['valid'])
            self.assertEqual(report['ranking_mismatches'], 1)

    def test_empty_source_and_completed_index_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, database, stats = self.make_index(root, '# comment\n\n')
            self.assertEqual(stats['users'], 0)
            self.assertEqual(audit.build_index(source, database, cache_mib=8)['candidate_pairs'], 0)
            result = root / 'result.txt'
            result.write_text('')
            self.assertTrue(audit.validate(database, result)['valid'])
            source.write_text('1 2\n')
            with self.assertRaises(ValueError):
                audit.build_index(source, database, cache_mib=8)

    def test_invalid_ids_rejected_and_resume_uses_committed_source_identity(self):
        for value in ['-1', '+1', '１', '1.5', '1e9', '']:
            with self.assertRaises(ValueError):
                audit.canonical(value)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, database, stats = self.make_index(root, '1 2\n1 2\n3 2\n')
            with sqlite3.connect(database) as con:
                con.execute("UPDATE metadata SET value='building' WHERE key='status'")
            with self.assertRaises(ValueError):
                audit.build_index(source, database, cache_mib=8)
            with contextlib.redirect_stdout(io.StringIO()):
                resumed = audit.build_index(source, database, cache_mib=8, resume=True)
            self.assertEqual(resumed['edge_records'], stats['edge_records'])
            self.assertEqual(resumed['users'], stats['users'])
            self.assertEqual(resumed['unique_directed_edges'], stats['unique_directed_edges'])


if __name__ == '__main__':
    unittest.main()
