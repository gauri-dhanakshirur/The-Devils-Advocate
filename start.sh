#!/bin/bash
set -e

echo "🦞 Starting OpenClaw Gateway..."
# Configure OpenClaw if a Groq key is provided via env
if [ ! -z "$GROQ_API_KEY" ]; then
    echo "Configuring OpenClaw with provided GROQ_API_KEY..."
    # A simple way to configure models is to pass JSON patch
    openclaw config patch --stdin <<< "{\"models\":{\"providers\":{\"groq\":{\"baseUrl\":\"https://api.groq.com/openai/v1\",\"apiKey\":\"$GROQ_API_KEY\",\"models\":[\"llama-3.1-8b-instant\"]}}}}"
fi

# Start OpenClaw in the background
openclaw gateway --port 18789 --host 0.0.0.0 &
OPENCLAW_PID=$!

echo "🚀 Starting FastAPI Backend..."
# Wait a few seconds for OpenClaw to bind
sleep 3
uvicorn main:app --host 0.0.0.0 --port 8000

# If uvicorn exits, kill OpenClaw
kill $OPENCLAW_PID
