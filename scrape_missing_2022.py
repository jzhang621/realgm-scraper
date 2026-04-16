"""
scrape_missing_2022.py

Seeds the players who appear in the 2021-22 season roster but were never
scraped, then fetches their profiles.

Run:
  python3 scrape_missing_2022.py --use-browser
"""

import argparse
import csv
import logging
import os
import sys

import config
import checkpoint
import storage
from parsers.profile import parse_player_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.ROOT_DIR, "scrape_missing_2022.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

fetcher = None


def find_missing_players():
    """Return player dicts for 2021-22 roster players not yet in the checkpoint."""
    roster = {}
    with open(config.CSV_SEASON_ROSTERS) as f:
        for row in csv.DictReader(f):
            if row["season"] == "2022":
                pid = row["player_id"]
                if pid not in roster and row.get("url_slug"):
                    roster[pid] = row["url_slug"]

    import sqlite3
    conn = sqlite3.connect(config.CHECKPOINT_DB)
    existing = set(
        r[0] for r in conn.execute("SELECT player_id FROM fetch_state").fetchall()
    )
    conn.close()

    return [
        {"player_id": pid, "url_slug": slug}
        for pid, slug in roster.items()
        if pid not in existing
    ]


def scrape_player(player_id, url_slug):
    url = f"{config.BASE_URL}/player/{url_slug}/Summary/{player_id}"
    try:
        html = fetcher.get(url)
    except FileNotFoundError:
        logger.warning(f"Player {player_id}: 404 — skipping")
        checkpoint.mark_failed(player_id, "404 Not Found")
        return False
    except Exception as e:
        logger.error(f"Player {player_id}: fetch error — {e}")
        checkpoint.mark_failed(player_id, str(e))
        return False

    try:
        parsed = parse_player_page(html, player_id)
    except Exception as e:
        logger.error(f"Player {player_id}: parse error — {e}", exc_info=True)
        checkpoint.mark_failed(player_id, f"parse error: {e}")
        return False

    try:
        storage.flush_player_data(parsed)
    except Exception as e:
        logger.error(f"Player {player_id}: storage error — {e}", exc_info=True)
        checkpoint.mark_failed(player_id, f"storage error: {e}")
        return False

    checkpoint.mark_done(player_id)
    return True


def main():
    global fetcher
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-browser", action="store_true", required=True)
    args = parser.parse_args()

    import fetcher_browser as fetcher_module
    fetcher = fetcher_module

    missing = find_missing_players()
    logger.info(f"Found {len(missing)} players to seed and scrape")

    if not missing:
        logger.info("Nothing to do.")
        return

    checkpoint.init_from_seed(missing)
    logger.info(f"Seeded {len(missing)} players into checkpoint as pending")

    done = failed = 0
    for i, entry in enumerate(missing, 1):
        pid = entry["player_id"]
        slug = entry["url_slug"]
        logger.info(f"[{i}/{len(missing)}] Player {pid} ({slug})")
        if scrape_player(pid, slug):
            done += 1
        else:
            failed += 1

        if i % 100 == 0:
            logger.info(f"Progress: {done} done, {failed} failed out of {i}")

    logger.info(f"Complete. {done} done, {failed} failed.")
    checkpoint.summary()


if __name__ == "__main__":
    try:
        main()
    finally:
        if fetcher and hasattr(fetcher, "close"):
            fetcher.close()
