#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from metrics import summarize


class TimingTests(unittest.TestCase):
    def test_synthetic_timestamp_arithmetic(self):
        # Synthetic fixture is for parser validation, never an experimental result.
        job = {"id": "fixture", "state": "SUCCEEDED", "mapsTotal": 2, "reducesTotal": 1,
               "startTime": 1000, "finishTime": 21000}
        tasks = [{"state": "SUCCEEDED", "type": "MAP", "startTime": 2000, "finishTime": 6000},
                 {"state": "SUCCEEDED", "type": "MAP", "startTime": 3000, "finishTime": 9000},
                 {"state": "SUCCEEDED", "type": "REDUCE", "startTime": 6000, "finishTime": 20000}]
        result = summarize(job, tasks)
        self.assertEqual(result["map_min_s"], 4)
        self.assertEqual(result["map_max_s"], 6)
        self.assertEqual(result["map_avg_s"], 5)
        self.assertEqual(result["reduce_avg_s"], 14)
        self.assertEqual(result["job_s"], 20)

    def test_partial_tasks_are_rejected(self):
        job = {"id": "fixture", "state": "SUCCEEDED", "mapsTotal": 2, "reducesTotal": 1,
               "startTime": 1000, "finishTime": 21000}
        with self.assertRaises(ValueError):
            summarize(job, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
