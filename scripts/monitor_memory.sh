#!/bin/bash

# Monitor memory usage of claude-mpm processes

echo "🔍 Monitoring claude-mpm memory usage..."
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "=== Claude MPM Memory Usage ==="
    echo "Time: $(date)"
    echo ""

    # Find all Python processes related to claude-mpm
    ps aux | grep -E "(claude[-_]mpm|hook_handler)" | grep -v grep | while read line; do
        PID=$(echo $line | awk '{print $2}')
        RSS_KB=$(echo $line | awk '{print $6}')
        RSS_MB=$((RSS_KB / 1024))
        CMD=$(echo $line | awk '{for(i=11;i<=NF;i++) printf "%s ", $i}')

        echo "PID: $PID | Memory: ${RSS_MB}MB | Command: ${CMD:0:80}"
    done

    echo ""
    echo "Total Memory Used: $(ps aux | grep -E "(claude[-_]mpm|hook_handler)" | grep -v grep | awk '{sum+=$6} END {printf "%.1f MB", sum/1024}')"

    sleep 5
done
