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
parser.add_argument("--port-offset", type=int, default=0,
                    help="Offset every fixed service port to isolate this experiment")
parser.add_argument("--node-host", help="This node's reachable IPv4 address or hostname")
parser.add_argument("--hosts-file", help="Absolute, per-process JVM hosts file; no system DNS changes")
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
hosts = [args.master] + args.workers + ([args.node_host] if args.node_host else [])
if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", name) for name in hosts):
    parser.error("Use simple hostnames or private IPv4 addresses")
if args.mode == "multi" and (len(args.workers) != 3 or len(set([args.master] + args.workers)) != 4):
    parser.error("Multi mode requires one master and three distinct workers")
if not 0 <= args.port_offset <= 40000:
    parser.error("port-offset must be between 0 and 40000")
if args.hosts_file and (not Path(args.hosts_file).is_absolute() or any(c.isspace() for c in args.hosts_file)):
    parser.error("hosts-file must be an absolute path without whitespace")
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


def address(host, port):
    return "%s:%d" % (host, port + args.port_offset)


node = args.node_host or "0.0.0.0"


write_xml("core-site.xml", {"fs.defaultFS": "hdfs://" + address(args.master, 9000),
                           "hadoop.tmp.dir": root + "/tmp"})
write_xml("hdfs-site.xml", {
    "dfs.replication": 1 if args.mode == "single" else 3,
    "dfs.namenode.name.dir": "file://" + root + "/name",
    "dfs.datanode.data.dir": "file://" + root + "/data",
    "dfs.namenode.http-address": address(args.master, 9870),
    "dfs.namenode.secondary.http-address": address(node, 9868),
    "dfs.namenode.checkpoint.dir": "file://" + root + "/checkpoint",
    "dfs.datanode.address": address(node, 9866),
    "dfs.datanode.ipc.address": address(node, 9867),
    "dfs.datanode.http.address": address(node, 9864),
    **({"dfs.datanode.hostname": args.node_host} if args.node_host else {})})
write_xml("yarn-site.xml", {
    "yarn.resourcemanager.hostname": args.master,
    "yarn.resourcemanager.address": address(args.master, 8032),
    "yarn.resourcemanager.scheduler.address": address(args.master, 8030),
    "yarn.resourcemanager.resource-tracker.address": address(args.master, 8031),
    "yarn.resourcemanager.admin.address": address(args.master, 8033),
    "yarn.resourcemanager.webapp.address": address(args.master, 8088),
    "yarn.nodemanager.address": address(node, 8041),
    "yarn.nodemanager.localizer.address": address(node, 8040),
    "yarn.nodemanager.webapp.address": address(node, 8042),
    **({"yarn.nodemanager.hostname": args.node_host} if args.node_host else {}),
    "yarn.nodemanager.vmem-check-enabled": "false",
    **({"yarn.nodemanager.admin-env": "JAVA_TOOL_OPTIONS=-Djdk.net.hosts.file=" + args.hosts_file}
       if args.hosts_file else {}),
    "mapreduce.shuffle.port": 13562 + args.port_offset,
    "yarn.nodemanager.aux-services": "mapreduce_shuffle",
    "yarn.nodemanager.env-whitelist": "JAVA_HOME,JAVA_TOOL_OPTIONS,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,CLASSPATH_PREPEND_DISTCACHE,HADOOP_YARN_HOME,HADOOP_HOME,PATH,LANG,TZ,HADOOP_MAPRED_HOME",
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
    "mapreduce.jobhistory.address": address(args.master, 10020),
    "mapreduce.jobhistory.webapp.address": address(args.master, 19888),
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
    handle.write("export HW1_HISTORY_URL=%s\n" % shlex.quote("http://" + address(args.master, 19888)))
    handle.write("export HADOOP_CONF_DIR=%s\n" % shlex.quote(str(out.resolve())))
    handle.write("export HADOOP_PID_DIR=%s\n" % shlex.quote(root + "/pids"))
    handle.write("export HADOOP_LOG_DIR=%s\n" % shlex.quote(root + "/daemon-logs"))
    handle.write("export HADOOP_HEAPSIZE_MAX=512m\n")
    if args.hosts_file:
        handle.write("export JAVA_TOOL_OPTIONS=%s\n" % shlex.quote("-Djdk.net.hosts.file=" + args.hosts_file))
if lowmem:
    with (out / "homework-env.sh").open("a") as handle:
        handle.write("export HADOOP_HEAPSIZE_MAX=256m\n")
print("Generated configuration in", out)
print("Copy the four XML files and workers into $HADOOP_HOME/etc/hadoop/.")
print("Append homework-env.sh to $HADOOP_HOME/etc/hadoop/hadoop-env.sh.")
print("No daemons started and no filesystem formatted.")
