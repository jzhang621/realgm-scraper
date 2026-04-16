#!/bin/bash
while true; do
    clear
    echo "================================================"
    echo "  2023-24 SCRAPER PROGRESS MONITOR"
    echo "================================================"
    date
    echo ""
    
    # Checkpoint status
    python3 main.py --status 2>/dev/null | tail -7
    
    echo ""
    echo "Latest activity:"
    tail -3 scrape_2024_full.log | grep -E "\[[0-9]+/[0-9]+\]" || echo "  (waiting for log update...)"
    
    echo ""
    echo "Refresh every 10 seconds (Ctrl+C to exit)"
    sleep 10
done
