"""
checkpoint.py — SQLite-backed state tracker.
Tracks which player pages have been fetched so scraper can resume safely.
"""

import sqlite3
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


def _conn():
    return sqlite3.connect(config.CHECKPOINT_DB)


def init():
    """Create checkpoint table if it doesn't exist."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS fetch_state (
                player_id   TEXT PRIMARY KEY,
                url_slug    TEXT,
                status      TEXT NOT NULL DEFAULT 'pending',
                fetched_at  TEXT,
                error       TEXT
            )
        """)
        c.commit()


def init_from_seed(players: list):
    """
    Bulk-insert players as 'pending'.
    Each element is a dict with at least 'player_id' and optionally 'url_slug'.
    Skips any that already exist (safe to call multiple times).
    """
    init()
    rows = [(p["player_id"], p.get("url_slug")) for p in players]
    with _conn() as c:
        c.executemany(
            """INSERT OR IGNORE INTO fetch_state (player_id, url_slug, status)
               VALUES (?, ?, 'pending')""",
            rows
        )
        # Also update url_slug for existing rows that don't have one yet
        c.executemany(
            """UPDATE fetch_state SET url_slug = ?
               WHERE player_id = ? AND (url_slug IS NULL OR url_slug = '')""",
            [(p.get("url_slug"), p["player_id"]) for p in players]
        )
        c.commit()
    logger.info(f"Checkpoint seeded with {len(players)} player records")


def get_pending() -> list:
    """Return list of (player_id, url_slug) tuples with status = 'pending'."""
    with _conn() as c:
        rows = c.execute(
            "SELECT player_id, url_slug FROM fetch_state WHERE status = 'pending' ORDER BY player_id"
        ).fetchall()
    return [{"player_id": r[0], "url_slug": r[1]} for r in rows]


def get_failed() -> list:
    """Return list of (player_id, url_slug) dicts with status = 'failed'."""
    with _conn() as c:
        rows = c.execute(
            "SELECT player_id, url_slug FROM fetch_state WHERE status = 'failed' ORDER BY player_id"
        ).fetchall()
    return [{"player_id": r[0], "url_slug": r[1]} for r in rows]


def mark_done(player_id: str):
    with _conn() as c:
        c.execute(
            "UPDATE fetch_state SET status = 'done', fetched_at = ?, error = NULL WHERE player_id = ?",
            (datetime.utcnow().isoformat(), player_id)
        )
        c.commit()


def mark_failed(player_id: str, error: str):
    with _conn() as c:
        c.execute(
            "UPDATE fetch_state SET status = 'failed', fetched_at = ?, error = ? WHERE player_id = ?",
            (datetime.utcnow().isoformat(), str(error)[:500], player_id)
        )
        c.commit()


def reset_failed():
    """Reset all failed entries back to pending for a retry pass."""
    with _conn() as c:
        c.execute("UPDATE fetch_state SET status = 'pending', error = NULL WHERE status = 'failed'")
        c.commit()


def summary():
    """Print counts by status."""
    with _conn() as c:
        rows = c.execute(
            "SELECT status, COUNT(*) FROM fetch_state GROUP BY status"
        ).fetchall()
    total = sum(r[1] for r in rows)
    print(f"\n{'='*35}")
    print(f"  CHECKPOINT SUMMARY ({total} total)")
    print(f"{'='*35}")
    for status, count in sorted(rows):
        pct = 100 * count / total if total else 0
        print(f"  {status:<10} {count:>6}  ({pct:.1f}%)")
    print(f"{'='*35}\n")
