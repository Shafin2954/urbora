#!/bin/bash
# AgriSense — start backend (port 8000) and frontend (port 5000) together.
# Backend runs in background; frontend's process is the foreground process
# that keeps the workflow alive.

set -e

echo "Starting AgriSense backend on port 8000..."
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Give the backend a moment to initialise before Vite tries to proxy it.
sleep 2

echo "Starting AgriSense frontend on port 5000..."
cd frontend && npm run dev

# If the frontend exits for any reason, clean up the backend.
kill $BACKEND_PID 2>/dev/null || true
