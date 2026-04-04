#!/bin/sh
set -eu

MODEL_NAME="${OLLAMA_MODEL:-gemma4:e2b}"

ollama serve &
OLLAMA_PID="$!"

cleanup() {
  kill "$OLLAMA_PID" 2>/dev/null || true
}

trap cleanup INT TERM

until ollama list >/dev/null 2>&1; do
  sleep 2
done

ollama pull "$MODEL_NAME"

wait "$OLLAMA_PID"
