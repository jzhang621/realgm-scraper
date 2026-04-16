#!/usr/bin/env python3
"""
Simple API endpoint to serve scraper status as JSON.
Usage: python3 api_status.py
Access: http://localhost:8001/status
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os

CHECKPOINT_DB = os.path.join(os.path.dirname(__file__), "data", "checkpoint.db")

class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            try:
                conn = sqlite3.connect(CHECKPOINT_DB)
                cursor = conn.cursor()

                # Get counts
                cursor.execute("SELECT status, COUNT(*) FROM fetch_state GROUP BY status")
                status_counts = dict(cursor.fetchall())

                total = sum(status_counts.values())
                done = status_counts.get('done', 0)
                failed = status_counts.get('failed', 0)
                pending = status_counts.get('pending', 0)

                # Get recent successes
                cursor.execute("""
                    SELECT player_id, url_slug
                    FROM fetch_state
                    WHERE status = 'done'
                    ORDER BY rowid DESC
                    LIMIT 10
                """)
                recent = [{'player_id': row[0], 'slug': row[1]} for row in cursor.fetchall()]

                conn.close()

                data = {
                    'total': total,
                    'done': done,
                    'failed': failed,
                    'pending': pending,
                    'progress_pct': round(done / total * 100, 2) if total > 0 else 0,
                    'recent': recent
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress log messages
        pass

if __name__ == '__main__':
    PORT = 8001
    server = HTTPServer(('localhost', PORT), StatusHandler)
    print(f"✅ Status API running on http://localhost:{PORT}/status")
    print("   Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 API stopped")
