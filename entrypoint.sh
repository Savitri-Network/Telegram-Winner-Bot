#!/usr/bin/env bash
set -e

echo "Starting Savitri bot with auto-restart loop..."
while true; do
  python /app/main.py || true
  echo "Bot crashed, restarting in 5s..."
  sleep 5
done
