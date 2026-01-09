#!/bin/bash
# SPLADE API     

API_URL="${SPLADE_API_URL:-http://localhost:8001}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"

echo " SPLADE API    "
echo "   API URL: $API_URL"
echo "    : ${CHECK_INTERVAL}"
echo "   : Ctrl+C"
echo ""

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    if curl -s --max-time 5 "$API_URL/health" > /dev/null 2>&1; then
        echo "[$TIMESTAMP]   "
    else
        echo "[$TIMESTAMP]   "
        echo "    :"
        echo "   1. SSH    "
        echo "   2. RunPod API    "
        echo "   3.     (8001 -> 8000)"
    fi
    
    sleep "$CHECK_INTERVAL"
done
