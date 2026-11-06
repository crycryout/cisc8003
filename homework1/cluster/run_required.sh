#!/usr/bin/env bash
# Requires a running YARN cluster and an installed generated configuration,
# and the real Yelp/medium inputs already uploaded to the supplied HDFS paths.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo "Usage: $0 HDFS_YELP_UNCOMPRESSED_FILE HDFS_MEDIUM_EDGE_FILE" >&2
  exit 2
fi
: "${HADOOP_HOME:?Source your Hadoop environment first}"
case ${HW1_MEMORY_PROFILE:-} in
  standard|lowmem) ;;
  *) echo "Source the generated homework-env.sh (standard or lowmem) first." >&2; exit 2 ;;
esac
REPETITIONS=${REPETITIONS:-1}
[[ $REPETITIONS =~ ^[1-9][0-9]*$ ]] || { echo "REPETITIONS must be a positive integer." >&2; exit 2; }
PROJECT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$$
BASE="/hw1/e2e-$RUN_ID"
EVIDENCE="$PROJECT/results/e2e-$RUN_ID"
mkdir -p "$EVIDENCE"
export LOG_DIR="$EVIDENCE/community"
hdfs dfs -test -f "$1"
hdfs dfs -test -f "$2"
hdfs dfs -mkdir -p "$BASE/input"
hdfs dfs -put "$PROJECT/data/shakespeare_prepared/small" "$BASE/input/small"
hdfs dfs -put "$PROJECT/data/shakespeare_prepared/merged.txt" "$BASE/input/merged.txt"
python3 "$PROJECT/src/run_wordcount.py" --mode files --repetitions "$REPETITIONS" \
  --small-input "$BASE/input/small" --merged-input "$BASE/input/merged.txt" \
  --output-root "$BASE/shakespeare" --evidence "$EVIDENCE/shakespeare"
python3 "$PROJECT/src/run_wordcount.py" --mode sweep --repetitions "$REPETITIONS" \
  --large-input "$1" --plan 6:1,6:3,12:1,12:3 \
  --output-root "$BASE/yelp" --evidence "$EVIDENCE/yelp"
bash "$PROJECT/src/run_community.sh" "$2" "$BASE/community" edges follower-followee
hdfs dfs -getmerge "$BASE/community/06_top10/part-*" "$EVIDENCE/medium_all_users_top10.txt"
python3 "$PROJECT/src/export_suffixes.py" --input "$EVIDENCE/medium_all_users_top10.txt" \
  --output "$EVIDENCE/medium_by_suffix"
python3 "$PROJECT/cluster/collect_community_metrics.py" --logs "$LOG_DIR" --output "$EVIDENCE/community-history"
printf '%s\n' "Required jobs finished. Evidence: $EVIDENCE" "HDFS output: $BASE"
