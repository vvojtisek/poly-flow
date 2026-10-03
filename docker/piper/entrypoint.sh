#!/bin/sh
# Download any missing voices into the persistent volume, then serve.
# The first voice in PIPER_VOICES is the default; others are selected per request via {"voice": ...}.
set -eu
cd "$PIPER_DATA_DIR"
for v in $PIPER_VOICES; do
  [ -f "$v.onnx" ] || python -m piper.download_voices --data-dir "$PIPER_DATA_DIR" "$v"
done
default_voice=$(echo "$PIPER_VOICES" | awk '{print $1}')
exec python -m piper.http_server --host 0.0.0.0 --port 5000 --data-dir "$PIPER_DATA_DIR" -m "$default_voice"
