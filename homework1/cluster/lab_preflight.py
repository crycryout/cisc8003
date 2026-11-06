#!/usr/bin/env python3
"""Read-only inventory for an individual lab host; never installs or starts services."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess


def command(argv):
    if not shutil.which(argv[0]):
        return {"available": False, "command": argv}
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        return {"available": True, "returncode": result.returncode,
                "stdout": result.stdout[:24000], "stderr": result.stderr[:4000]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "error": str(exc)}


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", default=str(Path.home()),
                        help="Existing directory on the intended experiment filesystem")
    args = parser.parse_args()
    work = Path(args.work_dir).expanduser().resolve()
    if not work.is_dir():
        parser.error("work-dir must already exist; no directories are created by this check")
    usage = shutil.disk_usage(work)
    interfaces = {}
    for interface in sorted(Path("/sys/class/net").glob("*")):
        if interface.name == "lo":
            continue
        interfaces[interface.name] = {
            "operstate": read_text(interface / "operstate"),
            "link_speed_mbps": read_text(interface / "speed")}
    numa = {p.name: {"cpulist": read_text(p / "cpulist"),
                     "meminfo": read_text(p / "meminfo")}
            for p in sorted(Path("/sys/devices/system/node").glob("node[0-9]*"))}
    try:
        affinity = sorted(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        affinity = None
    hadoop = Path(os.environ.get("HADOOP_HOME", str(Path.home() / "hadoop-3.3.6")))
    report = {
        "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "evidence_kind": "read_only_host_inventory_not_a_cluster_benchmark",
        "hostname": socket.gethostname(), "architecture": platform.machine(),
        "kernel": platform.release(), "os_release": read_text("/etc/os-release"),
        "logical_cpus": os.cpu_count(), "process_cpu_affinity": affinity,
        "cpu": command(["lscpu", "--json"]), "numa": numa,
        "meminfo": read_text("/proc/meminfo"),
        "cgroup_membership": read_text("/proc/self/cgroup"),
        "cgroup_mount_root_limits": {
            name: read_text(Path("/sys/fs/cgroup") / name)
            for name in ["memory.max", "cpu.max", "cpuset.cpus.effective"]},
        "work_filesystem": {"path": str(work), "total_bytes": usage.total,
                            "free_bytes": usage.free, "used_bytes": usage.used,
                            "writable_by_current_user": os.access(work, os.W_OK)},
        "mount": command(["findmnt", "-T", str(work), "-J"]),
        "interfaces": interfaces,
        "java_home": os.environ.get("JAVA_HOME"),
        "java": command(["java", "-version"]),
        "java_from_java_home": (command([str(Path(os.environ["JAVA_HOME"]) / "bin/java"), "-version"])
                                if os.environ.get("JAVA_HOME") else None),
        "python": command(["python3", "--version"]),
        "ssh_client": command(["ssh", "-V"]),
        "listening_tcp_ports": command(["ss", "-ltn"]),
        "hadoop": command([str(hadoop / "bin/hadoop"), "version"]),
        "notes": ["No GPU/CUDA command is run and no package is installed.",
                  "Link speed is local interface information, not measured end-to-end bandwidth.",
                  "Host RAM/CPU totals may exceed an account's or container's allocation.",
                  "Cgroup mount-root limits may not be the calling process's leaf limits."]}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
