#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  📡 lovepitchingpolar — Story News Agent"
echo "  ──────────────────────────────────────────────"
echo ""

# Check Ollama is running
if ! curl -sf http://localhost:11434 > /dev/null 2>&1; then
  echo "  ⚠  Ollama is not running. Starting with CPU-only mode..."
  OLLAMA_NO_GPU=1 ollama serve &>/tmp/ollama.log &
  sleep 3
  echo "  ✓  Ollama started (CPU mode)"
else
  echo "  ✓  Ollama is running"
fi

echo ""
echo "  Starting Streamlit on port 8501..."
echo ""

streamlit run app.py \
  --server.port 8501 \
  --server.headless true \
  --browser.gatherUsageStats false \
  --theme.base dark \
  --theme.backgroundColor "#0D0D0D" \
  --theme.secondaryBackgroundColor "#111111" \
  --theme.textColor "#E8E8E8" \
  --theme.primaryColor "#4B9EFF" &

STREAMLIT_PID=$!
sleep 2

echo "  ✓  Streamlit running at http://localhost:8501"
echo ""
echo "  ──────────────────────────────────────────────"
echo "  To share remotely (phone / laptop):"
echo "  Open a NEW terminal and run:"
echo ""
echo "      ngrok http 8501"
echo ""
echo "  Then share the https://xxxxx.ngrok-free.app URL"
echo "  ──────────────────────────────────────────────"
echo ""
echo "  Login credentials:"
echo "    Username: $(grep APP_USERNAME .env | cut -d= -f2)"
echo "    Password: (see .env)"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait $STREAMLIT_PID
