"""
main.py — Orchestrator for the RealGM NCAA scraper.

Phases
------
1. Seed  — Fetch all season listing pages → season_rosters.csv + checkpoint DB
2. Scrape — For each pending player → fetch profile page → parse → write CSVs

Usage
-----
  # Full run (seed + scrape):
  python3 main.py

  # Seed only (build player list, don't fetch profiles yet):
  python3 main.py --seed-only

  # Scrape only (skip seed, assume checkpoint already initialised):
  python3 main.py --scrape-only

  # Retry failed players (reset failed → pending, then scrape):
  python3 main.py --retry-failed

  # Test mode: scrape first N players then stop:
  python3 main.py --limit 10

  # Show checkpoint status and exit:
  python3 main.py --status
"""

import argparse
import logging
import os
import sys

import config
import checkpoint
import storage
from parsers.listing import parse_listing, check_pagination, stats_listing_url
from parsers.profile import parse_player_page

# Fetcher module (will be set based on --use-browser flag)
fetcher = None

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(config.ROOT_DIR, "scraper.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1 — Seed
# ---------------------------------------------------------------------------

def phase_seed():
    """
    Fetch all season listing pages.
    Writes season_rosters.csv.
    Initialises checkpoint DB with every unique player found.
    Returns the de-duplicated set of player_ids.
    """
    logger.info("=== PHASE 1: SEED ===")

    # Track best known url_slug per player_id (slug is needed to build profile URLs)
    slug_map = {}   # player_id -> url_slug

    for season in config.SEASONS:
        # Use the stats listing URL — returns ALL players for the season (~5000+)
        # /ncaa/players/{year} is a bio directory that only shows ~263 non-US players
        url = stats_listing_url(season)
        logger.info(f"Fetching listing: {url}")

        try:
            # 2026+ uses JavaScript pagination - need to click through pages
            if season >= 2026:
                logger.info(f"  Season {season} uses JS pagination, fetching all pages...")
                html_pages = fetcher.get_paginated_listing(url, max_pages=60)

                if not html_pages:
                    logger.error(f"No pages fetched for season {season}")
                    continue

                # Parse all pages
                season_players = []
                for page_idx, html in enumerate(html_pages, 1):
                    page_players = parse_listing(html, season)
                    logger.info(f"  Page {page_idx}: parsed {len(page_players)} players")
                    season_players.extend(page_players)

                players = season_players
            else:
                # Older seasons return all players in one page
                html = fetcher.get(url)
                players = parse_listing(html, season)

        except Exception as e:
            logger.error(f"Failed to fetch listing for season {season}: {e}")
            continue

        if not players:
            logger.warning(f"No players parsed for season {season} — check HTML")
            continue

        # Write season roster rows
        storage.write_season_roster(players)

        # Accumulate slug map
        for p in players:
            pid = p["player_id"]
            slug = p.get("url_slug")
            if pid not in slug_map and slug:
                slug_map[pid] = slug

        logger.info(f"Season {season}: {len(players)} players (total unique so far: {len(slug_map)})")

    logger.info(f"Seed complete. {len(slug_map)} unique player IDs found.")

    # Build list of player dicts for checkpoint (with url_slug)
    seed_players = [{"player_id": pid, "url_slug": slug} for pid, slug in slug_map.items()]
    checkpoint.init_from_seed(seed_players)

    return set(slug_map.keys())


# ---------------------------------------------------------------------------
# Phase 2 — Scrape player profiles
# ---------------------------------------------------------------------------

def _player_url(player_id: str, url_slug: str = None) -> str:
    """Build the canonical player summary URL."""
    if url_slug:
        return f"{config.BASE_URL}/player/{url_slug}/Summary/{player_id}"
    # Fallback: ID-only URL (works but misses slug — use if slug unavailable)
    return f"{config.BASE_URL}/player/Summary/{player_id}"


def _scrape_player(player_id: str, url_slug: str = None) -> bool:
    """Fetch + parse + write one player. Returns True on success."""
    url = _player_url(player_id, url_slug)
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


def phase_scrape(limit=None):
    """
    Scrape all pending players.
    If limit is set, stop after that many players (for test runs).
    """
    logger.info("=== PHASE 2: SCRAPE ===")

    pending = checkpoint.get_pending()   # list of {"player_id": ..., "url_slug": ...}
    logger.info(f"{len(pending)} players pending")

    if limit is not None:
        pending = pending[:limit]
        logger.info(f"Limiting to {limit} players")

    done = 0
    failed = 0

    for i, entry in enumerate(pending, 1):
        player_id = entry["player_id"]
        url_slug = entry.get("url_slug")
        logger.info(f"[{i}/{len(pending)}] Player {player_id} ({url_slug})")
        success = _scrape_player(player_id, url_slug)
        if success:
            done += 1
        else:
            failed += 1

        # Periodic summary every 100 players
        if i % 100 == 0:
            logger.info(f"Progress: {done} done, {failed} failed out of {i} processed")

    logger.info(f"Scrape complete. {done} done, {failed} failed.")
    checkpoint.summary()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="RealGM NCAA Basketball Scraper")
    p.add_argument("--seed-only",    action="store_true", help="Only run Phase 1 (seed)")
    p.add_argument("--scrape-only",  action="store_true", help="Only run Phase 2 (scrape profiles)")
    p.add_argument("--retry-failed", action="store_true", help="Reset failed → pending, then scrape")
    p.add_argument("--limit",        type=int, default=None, help="Stop after N players (test mode)")
    p.add_argument("--status",       action="store_true", help="Print checkpoint summary and exit")
    p.add_argument("--use-browser",  action="store_true", help="Use Playwright browser automation (bypasses Cloudflare)")
    return p.parse_args()


def main():
    global fetcher
    args = parse_args()

    # Select fetcher module based on --use-browser flag
    if args.use_browser:
        import fetcher_browser as fetcher_module
        logger.info("Using browser-based fetcher (Playwright)")
    else:
        import fetcher as fetcher_module
        logger.info("Using standard fetcher (cloudscraper)")

    fetcher = fetcher_module

    # Ensure output directories exist
    os.makedirs(config.RAW_LISTINGS, exist_ok=True)
    os.makedirs(config.RAW_PLAYERS, exist_ok=True)
    os.makedirs(config.PROCESSED_DIR, exist_ok=True)

    if args.status:
        checkpoint.init()
        checkpoint.summary()
        return

    if args.retry_failed:
        checkpoint.init()
        failed = checkpoint.get_failed()
        checkpoint.reset_failed()
        logger.info(f"Reset {len(failed)} failed entries to pending")
        phase_scrape(limit=args.limit)
        return

    if args.scrape_only:
        phase_scrape(limit=args.limit)
        return

    if args.seed_only:
        phase_seed()
        return

    # Default: full run
    phase_seed()
    phase_scrape(limit=args.limit)


if __name__ == "__main__":
    try:
        main()
    finally:
        # Cleanup browser resources if using browser fetcher
        if fetcher and hasattr(fetcher, 'close'):
            fetcher.close()
