#!/bin/sh
set -eu
DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
cd "$DIR"
JAR="$DIR/tla2tools.jar"
[ -f "$JAR" ] || { echo "missing tla2tools.jar" >&2; exit 1; }
DEFAULT="ContextStack UniqueId UniqueIdSafe WebSocketIsolation RouteVsDom RenderIdempotent"
if [ "$#" -eq 0 ]; then
  # shellcheck disable=SC2086
  set -- $DEFAULT
fi
pass=0
fail=0
for name in "$@"; do
  echo "======== TLC $name ========"
  if java -XX:+UseParallelGC -cp "$JAR" tlc2.TLC -config "$name.cfg" -workers 1 "$name.tla" \
      >"/tmp/tlc_$name.log" 2>&1; then
    if grep -q 'No error has been found' "/tmp/tlc_$name.log"; then
      grep 'states generated' "/tmp/tlc_$name.log" | tail -1
      echo "PASS $name"
      pass=$((pass+1))
    else
      echo "FAIL $name"
      grep -E 'Error:|Couldn' "/tmp/tlc_$name.log" | head -5
      fail=$((fail+1))
    fi
  else
    # TLC returns non-zero on invariant violation
    if grep -q 'No error has been found' "/tmp/tlc_$name.log"; then
      echo "PASS $name"
      pass=$((pass+1))
    else
      echo "FAIL $name"
      grep -E 'Error:|Couldn' "/tmp/tlc_$name.log" | head -5
      fail=$((fail+1))
    fi
  fi
done
echo "======== RESULT pass=$pass fail=$fail ========"
[ "$fail" -eq 0 ]
