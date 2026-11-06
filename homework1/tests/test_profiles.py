#!/usr/bin/env python3
"""Check real generated Hadoop configurations against node resource budgets."""
from pathlib import Path
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def properties(path):
    return {p.findtext("name"): p.findtext("value") for p in ET.parse(path).getroot()}


class ProfileTests(unittest.TestCase):
    def generate(self, profile, directory):
        subprocess.run([sys.executable, str(ROOT / "cluster/configure.py"),
                        "--mode", "multi", "--profile", profile, "--master", "master",
                        "--workers", "worker1", "worker2", "worker3", "--data-root", "/home/ubuntu/hadoop-multi",
                        "--output", directory], check=True, capture_output=True)
        return properties(Path(directory) / "yarn-site.xml"), properties(Path(directory) / "mapred-site.xml")

    def test_lowmem_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            yarn, mr = self.generate("lowmem", directory)
            available = int(yarn["yarn.nodemanager.resource.memory-mb"])
            self.assertEqual(available, 2048)
            self.assertEqual(int(yarn["yarn.nodemanager.resource.cpu-vcores"]), 2)
            task = int(mr["mapreduce.map.memory.mb"])
            master = int(mr["yarn.app.mapreduce.am.resource.mb"])
            self.assertLessEqual(task + master, available)
            self.assertEqual(mr["mapreduce.map.java.opts"], "-Xmx512m")
            self.assertLess(available + 2 * 256 + 512, 4096)
            env = (Path(directory) / "homework-env.sh").read_text()
            self.assertIn("HADOOP_HEAPSIZE_MAX=256m", env)
            self.assertIn("HW1_MEMORY_PROFILE=lowmem", env)

    def test_standard_budget_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            yarn, mr = self.generate("standard", directory)
            self.assertEqual(int(yarn["yarn.nodemanager.resource.memory-mb"]), 6144)
            self.assertEqual(int(mr["mapreduce.map.memory.mb"]), 1536)
            self.assertEqual(mr["mapreduce.map.java.opts"], "-Xmx768m")

    def test_machine_specific_environment_is_resolved_on_each_host(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "config"
            self.generate("standard", str(generated))
            env_script = generated / "homework-env.sh"
            for arch in ("arm64", "amd64"):
                node_home = Path(directory) / arch
                node_home.mkdir()
                java = "/usr/lib/jvm/java-11-openjdk-" + arch
                hadoop = str(node_home / "hadoop-3.3.6")
                (node_home / "hadoop-env-user.sh").write_text(
                    "export JAVA_HOME=" + shlex.quote(java) + "\n"
                    "export HADOOP_HOME=" + shlex.quote(hadoop) + "\n")
                result = subprocess.run(
                    ["bash", "-c", '. "$1"; printf "%s\\n" "$JAVA_HOME" "$HADOOP_MAPRED_HOME" "$HW1_MEMORY_PROFILE"',
                     "bash", str(env_script)], capture_output=True, text=True, check=True,
                    env={**os.environ, "HOME": str(node_home)})
                self.assertEqual(result.stdout.splitlines(), [java, hadoop, "standard"])

    def test_invalid_resource_budget_fails_before_creating_config(self):
        with tempfile.TemporaryDirectory() as directory:
            for option, value in (("--node-vcores", "0"), ("--node-memory-mb", "0")):
                output = Path(directory) / "not-created"
                result = subprocess.run(
                    [sys.executable, str(ROOT / "cluster/configure.py"), "--mode", "multi",
                     "--master", "thor", "--workers", "h800", "rtx5090a", "rtx5090b",
                     "--data-root", "/lab/homework1", "--output", str(output), option, value],
                    capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_isolated_cluster_ports_and_runtime_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "config"
            subprocess.run(
                [sys.executable, str(ROOT / "cluster/configure.py"), "--mode", "multi",
                 "--master", "master", "--workers", "worker1", "worker2", "worker3",
                 "--node-host", "worker1", "--port-offset", "20000", "--hosts-file", "/lab/hosts",
                 "--data-root", "/lab/multi", "--output", str(output)], check=True, capture_output=True)
            core = properties(output / "core-site.xml")
            hdfs = properties(output / "hdfs-site.xml")
            yarn = properties(output / "yarn-site.xml")
            mr = properties(output / "mapred-site.xml")
            self.assertEqual(core["fs.defaultFS"], "hdfs://master:29000")
            self.assertEqual(hdfs["dfs.datanode.address"], "worker1:29866")
            self.assertEqual(yarn["yarn.resourcemanager.address"], "master:28032")
            self.assertEqual(yarn["yarn.nodemanager.hostname"], "worker1")
            self.assertEqual(mr["mapreduce.jobhistory.webapp.address"], "master:39888")
            self.assertEqual(yarn["yarn.nodemanager.admin-env"], "JAVA_TOOL_OPTIONS=-Djdk.net.hosts.file=/lab/hosts")
            env = (output / "homework-env.sh").read_text()
            self.assertIn("HADOOP_PID_DIR=/lab/multi/pids", env)
            self.assertIn("HADOOP_LOG_DIR=/lab/multi/daemon-logs", env)

    def test_invalid_port_offset_is_rejected_without_creating_config(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "config"
            result = subprocess.run(
                [sys.executable, str(ROOT / "cluster/configure.py"), "--mode", "single",
                 "--master", "master", "--port-offset", "50000", "--data-root", "/lab/single",
                 "--output", str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
