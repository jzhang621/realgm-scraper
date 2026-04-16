#!/bin/bash
while true; do
    clear
    echo "================================================"
    echo "  REALGM SCRAPER - LIVE PROGRESS"
    echo "================================================"
    echo ""
    
    # Check if scraper is running
    if pgrep -f "main.py --scrape-only" > /dev/null; then
        echo "✅ Scraper is RUNNING"
    else
        echo "❌ Scraper is STOPPED"
    fi
    echo ""
    
    # Show checkpoint status
    python3 main.py --status 2>/dev/null | tail -7
    
    echo ""
    echo "Recent activity:"
    tail -5 scraper_2026.log 2>/dev/null | grep -E "\[[0-9]+/[0-9]+\]|Progress:" || echo "  (no recent logs)"
    
    echo ""
    echo "Press Ctrl+C to exit monitor"
    sleep 5
done
