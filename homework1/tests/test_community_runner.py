"""Check recovery/no-overwrite contracts without submitting synthetic benchmarks."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / 'src/run_community.sh'


class RunnerRecoveryTests(unittest.TestCase):
    def exercise(self, *, start=5, missing=None, output_exists=False, log_exists=False, stop=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        binary = root / 'bin'
        binary.mkdir()
        jar = root / 'hadoop/share/hadoop/tools/lib/hadoop-streaming-3.3.6.jar'
        jar.parent.mkdir(parents=True)
        jar.touch()
        stages = ['01_dedup', '02_universe', '03_blocks', '04_pairs', '05_scores', '06_top10']
        paths = ['/test/' + s + '/_SUCCESS' for s in stages[:start - 1] if s != missing]
        if output_exists:
            paths.append('/test/' + stages[start - 1])
        (root / 'paths.json').write_text(json.dumps(paths))
        (binary / 'hdfs').write_text('''#!/usr/bin/env python3
import os,sys,json,pathlib
args=sys.argv[1:]
if args[:3]==['dfs','-test','-e']:
 raise SystemExit(0 if args[3] in json.loads(pathlib.Path(os.environ['FAKE_PATHS']).read_text()) else 1)
if args[:2]==['dfs','-getmerge']:
 pathlib.Path(args[-1]).write_text('1\\t0\\n2\\t0\\n');raise SystemExit(0)
raise SystemExit(2)
''')
        (binary / 'hadoop').write_text('''#!/usr/bin/env python3
import os,sys,json
with open(os.environ['FAKE_CALLS'],'a') as out:out.write(json.dumps(sys.argv[1:])+'\\n')
print('Recovery-contract fixture only; not a Hadoop benchmark')
''')
        for p in binary.iterdir():
            p.chmod(0o755)
        logs = root / 'logs'
        logs.mkdir()
        if log_exists:
            (logs / (stages[start - 1] + '.log')).write_text('preserved failure evidence')
        env = {**os.environ, 'PATH': str(binary) + os.pathsep + os.environ['PATH'],
               'HADOOP_HOME': str(root / 'hadoop'), 'LOG_DIR': str(logs),
               'FAKE_PATHS': str(root / 'paths.json'), 'FAKE_CALLS': str(root / 'calls.jsonl'),
               'RESUME_FROM_STAGE': str(start), 'COMPRESS_INTERMEDIATES': '1',
               'INTERMEDIATE_REPLICATION': '1', 'STOP_AFTER_BLOCKS': '1' if stop else '0'}
        env.pop('RESUME_AFTER_BLOCKS', None)
        result = subprocess.run(['bash', str(SCRIPT), '/source', '/test', 'edges', 'follower-followee'], env=env, capture_output=True, text=True)
        calls = [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()] if (root / 'calls.jsonl').exists() else []
        return result, calls, logs

    def test_resume_from_five_skips_completed_stage_four_and_keeps_final_plain(self):
        result, calls, _ = self.exercise()
        self.assertEqual(result.returncode, 0, result.stderr)
        names, properties = [], []
        for call in calls:
            props = {}
            for i, value in enumerate(call[:-1]):
                if value == '-D':
                    key, val = call[i + 1].split('=', 1)
                    props[key] = val
            names.append(props['mapreduce.job.name'])
            properties.append(props)
        self.assertEqual(names, ['hw1-05_scores', 'hw1-06_top10'])
        self.assertEqual(properties[0]['stream.num.reduce.output.key.fields'], '3')
        self.assertEqual(properties[0]['mapreduce.output.fileoutputformat.compress'], 'true')
        self.assertEqual(properties[0]['dfs.replication'], '1')
        self.assertEqual(properties[1]['mapreduce.output.fileoutputformat.compress'], 'false')
        self.assertEqual(properties[1]['mapreduce.partition.keypartitioner.options'], '-k1,1')

    def test_missing_successful_upstream_prevents_any_submission(self):
        result, calls, _ = self.exercise(missing='03_blocks')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_existing_failed_output_is_preserved_and_not_retried(self):
        result, calls, _ = self.exercise(output_exists=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_existing_stage_log_is_not_overwritten(self):
        result, calls, logs = self.exercise(log_exists=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertEqual((logs / '05_scores.log').read_text(), 'preserved failure evidence')

    def test_stop_after_blocks_conflicts_with_resume(self):
        result, calls, _ = self.exercise(start=4, stop=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
