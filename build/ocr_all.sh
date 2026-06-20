#!/usr/bin/env bash
# OCR both Liber books in parallel chunks, then concatenate into one file each.
# Outputs: /tmp/liber_astartes_ocr.txt, /tmp/liber_hereticus_ocr.txt
set -uo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2   # cap per-process threads so 8 chunks share 16 cores

run_book () {           # $1=pdf  $2=tag  $3=pages  $4=nchunks
  local pdf="$1" tag="$2" pages="$3" n="$4" per pids=()
  per=$(( (pages + n - 1) / n ))
  for ((c=0;c<n;c++)); do
    local s=$(( c*per + 1 )) e=$(( (c+1)*per ))
    (( e > pages )) && e=$pages
    (( s > pages )) && break
    python3 build/ocr_liber.py "$pdf" "/tmp/${tag}_chunk${c}.txt" "$s" "$e" >/dev/null 2>&1 &
    pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
  cat /tmp/${tag}_chunk*.txt > "/tmp/${tag}_ocr.txt"
  rm -f /tmp/${tag}_chunk*.txt
  echo "DONE ${tag}: $(grep -c 'PDF PAGE' /tmp/${tag}_ocr.txt) pages -> /tmp/${tag}_ocr.txt"
}

run_book "HH 30 Liber Astartes Raw.pdf"  liber_astartes  336 4 &
A=$!
run_book "HH 30 Liber Hereticus Raw.pdf" liber_hereticus 356 4 &
H=$!
wait $A; wait $H
echo "ALL OCR COMPLETE"
