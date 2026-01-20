#!/bin/bash
# Stop all running services

echo "Stopping all services..."

# Kill Python app.py processes
for pid in $(ps aux | grep -E "python.*app\.py" | grep -v grep | awk '{print $2}'); do
    kill $pid 2>/dev/null || true
done

# Kill npm processes
for pid in $(ps aux | grep -E "npm run dev" | grep -v grep | awk '{print $2}'); do
    kill $pid 2>/dev/null || true
done

# Kill next dev processes
for pid in $(ps aux | grep -E "next dev" | grep -v grep | awk '{print $2}'); do
    kill $pid 2>/dev/null || true
done

sleep 1

echo "✓ All services stopped"
