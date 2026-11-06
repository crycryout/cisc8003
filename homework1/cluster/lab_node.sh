#!/usr/bin/env bash
# Operate only the task-specific configuration, PID and data directories.
set -euo pipefail
[[ $# == 2 ]] || { echo "Usage: $0 CONFIG_DIRECTORY start-single|start-master|start-worker|stop-single|stop-master|stop-worker|status" >&2; exit 2; }
CONFIG=$(realpath "$1")
ACTION=$2
[[ -f "$CONFIG/homework-env.sh" && -f "$CONFIG/hadoop-env.sh" ]] || exit 2
source "$CONFIG/homework-env.sh"
mkdir -p "$HADOOP_PID_DIR" "$HADOOP_LOG_DIR"
format_new() {
  local name_root
  name_root=$(python3 - "$CONFIG/hdfs-site.xml" <<'PY'
import sys,xml.etree.ElementTree as ET
props={p.findtext('name'):p.findtext('value') for p in ET.parse(sys.argv[1]).getroot()}
print(props['dfs.namenode.name.dir'].removeprefix('file://'))
PY
)
  if [[ -e "$name_root" ]]; then
    echo "Refusing format: NameNode directory already exists: $name_root" >&2
    return 2
  fi
  hdfs namenode -format -nonInteractive
}
case "$ACTION" in
  start-single)
    format_new
    hdfs --daemon start namenode
    hdfs --daemon start secondarynamenode
    hdfs --daemon start datanode
    yarn --daemon start resourcemanager
    yarn --daemon start nodemanager
    ;;
  start-master)
    format_new
    hdfs --daemon start namenode
    hdfs --daemon start secondarynamenode
    yarn --daemon start resourcemanager
    ;;
  start-worker)
    hdfs --daemon start datanode
    yarn --daemon start nodemanager
    ;;
  stop-single)
    mapred --daemon stop historyserver
    yarn --daemon stop nodemanager
    yarn --daemon stop resourcemanager
    hdfs --daemon stop datanode
    hdfs --daemon stop secondarynamenode
    hdfs --daemon stop namenode
    ;;
  stop-master)
    mapred --daemon stop historyserver
    yarn --daemon stop resourcemanager
    hdfs --daemon stop secondarynamenode
    hdfs --daemon stop namenode
    ;;
  stop-worker)
    yarn --daemon stop nodemanager
    hdfs --daemon stop datanode
    ;;
  status)
    hostname
    "$JAVA_HOME/bin/java" -version
    "$JAVA_HOME/bin/jps" -l
    hdfs dfsadmin -report
    yarn node -list
    ;;
  *) echo "Unknown action: $ACTION" >&2; exit 2 ;;
esac
