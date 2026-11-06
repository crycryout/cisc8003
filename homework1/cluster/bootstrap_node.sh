#!/usr/bin/env bash
# Run per Linux host as its non-root experiment user. No OS/CUDA changes by default.
set -euo pipefail
INSTALL_DEPS=0
PLAN_ONLY=0
case ${1:-} in
  '') [[ $# == 0 ]] || exit 2 ;;
  --install-deps) [[ $# == 1 ]] || exit 2; INSTALL_DEPS=1 ;;
  --plan) [[ $# == 1 ]] || exit 2; PLAN_ONLY=1 ;;
  *) echo "Usage: $0 [--plan|--install-deps]" >&2; exit 2 ;;
esac
VERSION=3.3.6
MACHINE=$(uname -m)
case "$MACHINE" in
  x86_64|amd64) ARCHIVE="hadoop-$VERSION.tar.gz" ;;
  aarch64|arm64) ARCHIVE="hadoop-$VERSION-aarch64.tar.gz" ;;
  *) echo "Unsupported CPU architecture: $MACHINE" >&2; exit 2 ;;
esac
printf 'Architecture: %s; selected archive: %s\n' "$MACHINE" "$ARCHIVE"
[[ $PLAN_ONLY == 0 ]] || exit 0
[[ $(id -u) != 0 ]] || { echo "Run as a non-root experiment user." >&2; exit 2; }
if [[ $INSTALL_DEPS == 1 ]]; then
  command -v apt-get >/dev/null || { echo "Install dependencies locally on this OS." >&2; exit 2; }
  sudo apt-get update
  sudo apt-get install -y openjdk-11-jdk-headless openssh-server rsync python3 curl
fi
for dep in python3 curl tar readlink; do
  command -v "$dep" >/dev/null || { echo "Missing $dep; install it before continuing." >&2; exit 2; }
done
JAVA_ROOT=''
JAVA_FROM_PATH=''
if command -v java >/dev/null; then
  JAVA_FROM_PATH=$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")
fi
for candidate in "${JAVA_HOME:-}" /usr/lib/jvm/java-11-openjdk-* "$JAVA_FROM_PATH"; do
  [[ -n $candidate && -x "$candidate/bin/java" && -x "$candidate/bin/javac" ]] || continue
  if "$candidate/bin/java" -version 2>&1 | head -n 1 | grep -Eq 'version "11([."]|$)'; then
    JAVA_ROOT=$(readlink -f "$candidate")
    break
  fi
done
[[ -n $JAVA_ROOT ]] || {
  echo 'JDK 11 not found. Set JAVA_HOME to a local, architecture-matched JDK 11.' >&2
  echo 'On apt-based hosts with an available package, --install-deps installs dependencies explicitly.' >&2
  exit 2
}
export JAVA_HOME="$JAVA_ROOT"
DEST="$HOME/hadoop-$VERSION"
if [[ ! -d "$DEST" ]]; then
  WORK=$(mktemp -d)
  trap 'rm -rf -- "$WORK"' EXIT
  BASE="https://archive.apache.org/dist/hadoop/common/hadoop-$VERSION"
  curl --fail --location --retry 3 "$BASE/$ARCHIVE" -o "$WORK/$ARCHIVE"
  curl --fail --location --retry 3 "$BASE/$ARCHIVE.sha512" -o "$WORK/checksum"
  python3 - "$WORK/$ARCHIVE" "$WORK/checksum" <<'PY'
import hashlib, pathlib, re, sys
archive, check = map(pathlib.Path, sys.argv[1:])
expected = re.findall(r'\b[0-9a-fA-F]{128}\b', check.read_text())
if len(expected) != 1:
    raise SystemExit('Cannot parse Apache SHA-512 checksum')
digest = hashlib.sha512()
with archive.open('rb') as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b''):
        digest.update(block)
if digest.hexdigest().lower() != expected[0].lower():
    raise SystemExit('Hadoop archive checksum mismatch')
print('Apache SHA-512 verified')
PY
  tar -xzf "$WORK/$ARCHIVE" -C "$HOME"
fi
python3 - "$JAVA_ROOT" "$DEST" "$HOME/hadoop-env-user.sh" <<'PY'
from pathlib import Path
import shlex
import sys
java, hadoop, output = sys.argv[1:]
Path(output).write_text('export JAVA_HOME=' + shlex.quote(java) + '\n'
                       'export HADOOP_HOME=' + shlex.quote(hadoop) + '\n'
                       'export HADOOP_MAPRED_HOME=' + shlex.quote(hadoop) + '\n'
                       'export PATH="$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH"\n')
PY
echo "Installed. Run: source ~/hadoop-env-user.sh"
"$JAVA_ROOT/bin/java" -version
"$DEST/bin/hadoop" version
