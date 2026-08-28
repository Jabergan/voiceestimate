#!/bin/bash
# VoiceEstimate — Hackyard 2026
# Start script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for .env
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Email sending will not work."
    echo "Create .env with: GMAIL_APP_PASSWORD=your_app_password"
fi

# Load env if present
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Error: Ollama is not running. Start it with: ollama serve"
    exit 1
fi

# Check qwen3:8b is available
if ! ollama list | grep -q "qwen3:8b"; then
    echo "Pulling qwen3:8b model (this may take a while)..."
    ollama pull qwen3:8b
fi

echo "Starting VoiceEstimate on port 5055..."
python3 app.py
