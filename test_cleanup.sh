#!/bin/bash

# Test script to simulate the cleanup behavior
echo "🧪 Testing cleanup mechanism..."

# Simulate starting a background process
echo "1. Starting test background process..."
nohup python3 -c "
import time
import sys
print('Test process started', flush=True)
while True:
    print('Test process running...', flush=True)
    time.sleep(2)
" > test_process.log 2>&1 &

TEST_PID=$!
echo "Test process PID: $TEST_PID"
echo "$TEST_PID" > test_process.pid

# Wait a moment
sleep 3

# Test the cleanup
echo "2. Testing cleanup mechanism..."
if [[ -f "test_process.pid" ]]; then
    local pid=$(cat "test_process.pid" 2>/dev/null)
    if [[ -n "$pid" ]]; then
        echo "Killing test process $pid"
        kill -9 "$pid" 2>/dev/null || true
        rm -f "test_process.pid"
    fi
fi

# Verify cleanup
sleep 1
if ps -p "$TEST_PID" > /dev/null 2>&1; then
    echo "❌ Test process still running after cleanup"
else
    echo "✅ Test process successfully terminated"
fi

# Cleanup
rm -f test_process.log test_process.pid
