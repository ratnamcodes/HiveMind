#!/usr/bin/env bash
# Render a composition to a crisp h264 master, then 2-pass linear loudnorm to -14 LUFS.
# usage: finalize.sh <CompositionId> <outName>
set -euo pipefail
cd "$(dirname "$0")/.."
COMP="$1"; OUT="$2"
RAW="out/${OUT}-raw.mp4"
FINAL="out/${OUT}.mp4"

echo ">>> rendering $COMP -> $RAW"
bunx remotion render src/index.ts "$COMP" "$RAW" \
  --crf=16 --jpeg-quality=95 --x264-preset=slow --color-space=bt709 --log=error

echo ">>> measuring loudness"
MEAS=$(ffmpeg -i "$RAW" -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
II=$(echo "$MEAS" | python3 -c "import json,sys;print(json.load(sys.stdin)['input_i'])")
ITP=$(echo "$MEAS" | python3 -c "import json,sys;print(json.load(sys.stdin)['input_tp'])")
ILRA=$(echo "$MEAS" | python3 -c "import json,sys;print(json.load(sys.stdin)['input_lra'])")
ITH=$(echo "$MEAS" | python3 -c "import json,sys;print(json.load(sys.stdin)['input_thresh'])")
echo "    measured I=$II TP=$ITP LRA=$ILRA TH=$ITH"

echo ">>> normalizing -> $FINAL"
ffmpeg -y -hide_banner -loglevel error -i "$RAW" -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I=$II:measured_TP=$ITP:measured_LRA=$ILRA:measured_thresh=$ITH" \
  -c:a aac -b:a 320k "$FINAL"

echo ">>> done: $FINAL"
ffmpeg -i "$FINAL" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)"
ls -la "$FINAL"
