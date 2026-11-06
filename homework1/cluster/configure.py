#!/usr/bin/env python3
"""Generate Hadoop 3.3.6 configuration without modifying or formatting HDFS."""
import argparse
from pathlib import Path
import re
import shlex
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--mode", required=True, choices=["single", "multi"])
parser.add_argument("--master", required=True)
parser.add_argument("--workers", nargs="*", default=[])
parser.add_argument("--output", required=True)
parser.add_argument("--data-root", required=True, help="Absolute path; use separate roots for single and multi")
parser.add_argument("--java-home", help="Explicit per-node JDK path; otherwise use that node's hadoop-env-user.sh")
parser.add_argument("--profile", choices=["standard", "lowmem"], default="standard",
                    help="standard: 8 GiB/4 vCPU nodes; lowmem: 4 GiB/2 vCPU nodes")
parser.add_argument("--node-memory-mb", type=int)
parser.add_argument("--node-vcores", type=int)
args = parser.parse_args()
lowmem = args.profile == "lowmem"
if args.node_memory_mb is None:
    args.node_memory_mb = 2048 if lowmem else 6144
if args.node_vcores is None:
    args.node_vcores = 2 if lowmem else 4
task_memory = 1024 if lowmem else 1536
task_heap = 512 if lowmem else 768
if args.node_memory_mb < task_memory or args.node_vcores < 1:
    parser.error("Node resources must fit at least one task container")
if not Path(args.data_root).is_absolute():
    parser.error("data-root must be absolute")
hosts = [args.master] + args.workers
if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", name) for name in hosts):
    parser.error("Use simple hostnames or private IPv4 addresses")
if args.mode == "multi" and (len(args.workers) != 3 or len(set(hosts)) != 4):
    parser.error("Multi mode requires one master and three distinct workers")
workers = [args.master] if args.mode == "single" else args.workers
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
root = args.data_root


def write_xml(filename, properties):
    doc = ET.Element("configuration")
    for name, value in properties.items():
        prop = ET.SubElement(doc, "property")
        ET.SubElement(prop, "name").text = name
        ET.SubElement(prop, "value").text = str(value)
    ET.indent(doc, space="  ")
    ET.ElementTree(doc).write(out / filename, encoding="UTF-8", xml_declaration=True)


write_xml("core-site.xml", {"fs.defaultFS": "hdfs://%s:9000" % args.master,
                           "hadoop.tmp.dir": root + "/tmp"})
write_xml("hdfs-site.xml", {
    "dfs.replication": 1 if args.mode == "single" else 3,
    "dfs.namenode.name.dir": "file://" + root + "/name",
    "dfs.datanode.data.dir": "file://" + root + "/data",
    "dfs.namenode.http-address": args.master + ":9870"})
write_xml("yarn-site.xml", {
    "yarn.resourcemanager.hostname": args.master,
    "yarn.nodemanager.aux-services": "mapreduce_shuffle",
    "yarn.nodemanager.env-whitelist": "JAVA_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,CLASSPATH_PREPEND_DISTCACHE,HADOOP_YARN_HOME,HADOOP_HOME,PATH,LANG,TZ,HADOOP_MAPRED_HOME",
    "yarn.nodemanager.resource.memory-mb": args.node_memory_mb,
    "yarn.nodemanager.resource.cpu-vcores": args.node_vcores,
    "yarn.scheduler.minimum-allocation-mb": 512,
    "yarn.scheduler.maximum-allocation-mb": args.node_memory_mb,
    "yarn.nodemanager.local-dirs": root + "/yarn-local",
    "yarn.nodemanager.log-dirs": root + "/yarn-logs",
    "yarn.log-aggregation-enable": "true",
    "yarn.nodemanager.remote-app-log-dir": "/tmp/logs"})
write_xml("mapred-site.xml", {
    "mapreduce.framework.name": "yarn",
    "mapreduce.application.classpath": "$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/*,$HADOOP_MAPRED_HOME/share/hadoop/mapreduce/lib/*",
    "mapreduce.jobhistory.address": args.master + ":10020",
    "mapreduce.jobhistory.webapp.address": args.master + ":19888",
    "mapreduce.jobhistory.intermediate-done-dir": "/mr-history/tmp",
    "mapreduce.jobhistory.done-dir": "/mr-history/done",
    "mapreduce.map.memory.mb": task_memory,
    "mapreduce.map.java.opts": "-Xmx%dm" % task_heap,
    "mapreduce.reduce.memory.mb": task_memory,
    "mapreduce.reduce.java.opts": "-Xmx%dm" % task_heap,
    "mapreduce.task.io.sort.mb": 64 if lowmem else 128,
    "mapreduce.reduce.shuffle.input.buffer.percent": 0.4 if lowmem else 0.7,
    "yarn.app.mapreduce.am.resource.mb": 512 if lowmem else 1536,
    "yarn.app.mapreduce.am.command-opts": "-Xmx256m" if lowmem else "-Xmx1024m",
    "mapreduce.map.speculative": "false",
    "mapreduce.reduce.speculative": "false"})
(out / "workers").write_text("\n".join(workers) + "\n")
(out / "homework-env.sh").write_text(
    '# Resolve machine-specific paths locally: ARM64 master and x86 workers may differ.\n'
    'if [ -r "$HOME/hadoop-env-user.sh" ]; then . "$HOME/hadoop-env-user.sh"; fi\n'
    + ("export JAVA_HOME=%s\n" % shlex.quote(args.java_home) if args.java_home else "")
    + 'export HADOOP_MAPRED_HOME="${HADOOP_HOME:-$HOME/hadoop-3.3.6}"\n')
with (out / "homework-env.sh").open("a") as handle:
    handle.write("export HW1_MEMORY_PROFILE=%s\n" % args.profile)
if lowmem:
    with (out / "homework-env.sh").open("a") as handle:
        handle.write("export HADOOP_HEAPSIZE_MAX=256m\n")
print("Generated configuration in", out)
print("Copy the four XML files and workers into $HADOOP_HOME/etc/hadoop/.")
print("Append homework-env.sh to $HADOOP_HOME/etc/hadoop/hadoop-env.sh.")
print("No daemons started and no filesystem formatted.")
