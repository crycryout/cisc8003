# Resolve machine-specific paths locally: ARM64 master and x86 workers may differ.
if [ -r "$HOME/hadoop-env-user.sh" ]; then . "$HOME/hadoop-env-user.sh"; fi
export HADOOP_MAPRED_HOME="${HADOOP_HOME:-$HOME/hadoop-3.3.6}"
export HW1_MEMORY_PROFILE=standard
export HW1_HISTORY_URL=http://master:39888
export HADOOP_CONF_DIR=/home/experiment-user/cisc8003/.local/conf/multi
export HADOOP_PID_DIR=/home/experiment-user/cisc8003/.local/multi/gpu01/pids
export HADOOP_LOG_DIR=/home/experiment-user/cisc8003/.local/multi/gpu01/daemon-logs
export HADOOP_HEAPSIZE_MAX=512m
export JAVA_TOOL_OPTIONS=-Djdk.net.hosts.file=/home/experiment-user/cisc8003/.local/hosts
