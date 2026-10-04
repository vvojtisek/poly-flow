#!/bin/sh
# Serve the voices in PIPER_VOICES from the volume. Never downloads: the `models` compose service
# (scripts/models.py fetch) puts pinned, checksum-verified voices there first.
# The first voice is the default; others are selected per request via {"voice": ...}.
# Note: piper falls back to the default voice for an unknown name, so callers must only send
# names listed by GET /voices.
set -eu
cd "$PIPER_DATA_DIR"
for v in $PIPER_VOICES; do
  if [ ! -f "$v.onnx" ] || [ ! -f "$v.onnx.json" ]; then
    echo "voice $v missing in $PIPER_DATA_DIR: run scripts/models.py fetch (compose service 'models')" >&2
    exit 1
  fi
done
default_voice=$(echo "$PIPER_VOICES" | awk '{print $1}')
exec python -m piper.http_server --host 0.0.0.0 --port 5000 --data-dir "$PIPER_DATA_DIR" -m "$default_voice"
