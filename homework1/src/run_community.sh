#!/usr/bin/env bash
# Run from any directory on the master, as the same non-root Hadoop user.
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: $0 HDFS_INPUT NEW_HDFS_OUTPUT [FORMAT=auto] [EDGE_ORDER=follower-followee]" >&2
  exit 2
fi
INPUT=$1
OUT=${2%/}
FORMAT=${3:-auto}
EDGE_ORDER=${4:-follower-followee}
PROFILE=${HW1_MEMORY_PROFILE:-standard}
if [[ "$PROFILE" == lowmem ]]; then
  TASK_MEMORY=1024
  TASK_HEAP=512
  SORT_MEMORY=64
  DEFAULT_REDUCERS=3
elif [[ "$PROFILE" == standard ]]; then
  TASK_MEMORY=1536
  TASK_HEAP=768
  SORT_MEMORY=128
  DEFAULT_REDUCERS=6
else
  echo "HW1_MEMORY_PROFILE must be standard or lowmem" >&2; exit 2
fi
REDUCERS=${REDUCERS:-$DEFAULT_REDUCERS}
BLOCK_SIZE=${BLOCK_SIZE:-512}
K=${K:-10}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${HADOOP_HOME:?Set HADOOP_HOME to your Hadoop installation}"
STREAMING="$HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-3.3.6.jar"
[[ -f "$STREAMING" ]] || { echo "Expected Hadoop 3.3.6 streaming JAR: $STREAMING" >&2; exit 2; }
if [[ ${RESUME_AFTER_BLOCKS:-0} == 1 ]]; then
  hdfs dfs -test -e "$OUT/03_blocks/_SUCCESS" || { echo "Completed 03_blocks is required to resume." >&2; exit 2; }
  for stage in 04_pairs 05_scores 06_top10; do
    if hdfs dfs -test -e "$OUT/$stage"; then echo "$stage already exists; refusing to overwrite." >&2; exit 2; fi
  done
elif hdfs dfs -test -e "$OUT"; then
  echo "Output exists; choose a NEW output root. No existing data was removed." >&2
  exit 2
fi
WORK=$(mktemp -d)
trap 'rm -rf -- "$WORK"' EXIT
LOG_DIR=${LOG_DIR:-"$SCRIPT_DIR/../results/community-$(date -u +%Y%m%dT%H%M%SZ)"}
mkdir -p "$LOG_DIR"
LOG_DIR=$(cd -- "$LOG_DIR" && pwd)
COMMON=(-D mapreduce.map.output.compress=true
  -D mapreduce.map.output.compress.codec=org.apache.hadoop.io.compress.DefaultCodec
  -D mapreduce.map.speculative=false -D mapreduce.reduce.speculative=false
  -D mapreduce.map.memory.mb="$TASK_MEMORY" -D mapreduce.map.java.opts="-Xmx${TASK_HEAP}m"
  -D mapreduce.reduce.memory.mb="$TASK_MEMORY" -D mapreduce.reduce.java.opts="-Xmx${TASK_HEAP}m"
  -D mapreduce.task.io.sort.mb="$SORT_MEMORY"
  -D mapreduce.job.reduces="$REDUCERS")
PARTITIONER=org.apache.hadoop.mapred.lib.KeyFieldBasedPartitioner
SOURCE="$SCRIPT_DIR/community.py"
cp "$SOURCE" "$WORK/community.py"
# LocalJobRunner reducers may use the submitter working directory; YARN uses
# its localized container directory. Both contain the same named source file.
cd "$WORK"
job() {
  local name=$1
  shift
  hadoop jar "$STREAMING" "${COMMON[@]}" -D "mapreduce.job.name=hw1-$name" "$@" 2>&1 | tee "$LOG_DIR/$name.log"
}
NORMALIZE="python3 community.py normalize --format $FORMAT --edge-order $EDGE_ORDER"
if [[ ${UNDIRECTED:-0} == 1 ]]; then NORMALIZE="$NORMALIZE --undirected"; fi
if [[ ${RESUME_AFTER_BLOCKS:-0} != 1 ]]; then
job 01_dedup -D stream.num.map.output.key.fields=3 -D stream.num.reduce.output.key.fields=3 -files "$SOURCE" \
  -input "$INPUT" -output "$OUT/01_dedup" -mapper "$NORMALIZE" \
  -combiner "python3 community.py unique" -reducer "python3 community.py unique"
job 02_universe -D mapreduce.job.reduces=1 -files "$SOURCE" \
  -input "$OUT/01_dedup" -output "$OUT/02_universe" \
  -mapper "python3 community.py universe-map --k $K" \
  -reducer "python3 community.py universe-reduce --k $K"
job 03_blocks -D stream.num.map.output.key.fields=3 \
  -D mapreduce.partition.keypartitioner.options=-k1,2 -files "$SOURCE" \
  -input "$OUT/01_dedup" -output "$OUT/03_blocks" -mapper cat \
  -partitioner "$PARTITIONER" -reducer "python3 community.py blocks --block-size $BLOCK_SIZE"
fi
if [[ ${STOP_AFTER_BLOCKS:-0} == 1 ]]; then
  echo "Preparation complete. Inspect 03_blocks counters and disk capacity."
  echo "Resume with RESUME_AFTER_BLOCKS=1 and the same arguments."
  exit 0
fi
hdfs dfs -getmerge "$OUT/02_universe/part-*" "$WORK/universe.txt"
job 04_pairs -D stream.num.map.output.key.fields=5 \
  -D mapreduce.partition.keypartitioner.options=-k1,4 -files "$SOURCE" \
  -input "$OUT/03_blocks" -output "$OUT/04_pairs" -mapper "python3 community.py replicate" \
  -partitioner "$PARTITIONER" -reducer "python3 community.py pairs"
job 05_scores -D stream.num.map.output.key.fields=3 -D stream.num.reduce.output.key.fields=3 -files "$SOURCE" \
  -input "$OUT/04_pairs" -output "$OUT/05_scores" -mapper cat \
  -combiner "python3 community.py sums" -reducer "python3 community.py sums"
job 06_top10 -D stream.num.map.output.key.fields=3 \
  -D mapreduce.partition.keypartitioner.options=-k1,1 \
  -D mapreduce.job.output.key.comparator.class=org.apache.hadoop.mapreduce.lib.partition.KeyFieldBasedComparator \
  -D 'mapreduce.partition.keycomparator.options=-k1,1n -k2,2n -k3,3n' \
  -D mapreduce.output.textoutputformat.separator=: -D mapred.textoutputformat.separator=: \
  -files "$SOURCE,$WORK/universe.txt" -input "$OUT/05_scores" -output "$OUT/06_top10" \
  -mapper "python3 community.py rank-map" -partitioner "$PARTITIONER" \
  -reducer "python3 community.py rank-reduce --k $K --hadoop-output"
echo "All-user output: $OUT/06_top10"
echo "Job logs: $LOG_DIR"
