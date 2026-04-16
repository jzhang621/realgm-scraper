"""
test_ncaa_page_parse.py

Verify that the /NCAA/{player_id} page for an NBA player (Tristan Da Silva, id=150739)
is fetchable and that parse_player_page extracts NCAA stats from it.

Run:
  python3 test_ncaa_page_parse.py --use-browser
"""

import argparse
import logging
import sys

import config
from parsers.profile import parse_player_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

PLAYER_ID = "150739"
URL_SLUG  = "Tristan-Da-Silva"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--use-browser", action="store_true", help="Use Playwright fetcher")
    args = parser.parse_args()

    if args.use_browser:
        import fetcher_browser as fetcher
        logger.info("Using browser fetcher")
    else:
        import fetcher as fetcher_module
        fetcher = fetcher_module
        logger.info("Using standard fetcher")

    summary_url = f"{config.BASE_URL}/player/{URL_SLUG}/Summary/{PLAYER_ID}"
    ncaa_url    = f"{config.BASE_URL}/player/{URL_SLUG}/NCAA/{PLAYER_ID}"

    # ── 1. Parse Summary page ──────────────────────────────────────────────────
    logger.info(f"Fetching Summary page: {summary_url}")
    summary_html = fetcher.get(summary_url)
    summary_parsed = parse_player_page(summary_html, PLAYER_ID)

    ncaa_from_summary = [r for r in summary_parsed["totals"] if r.get("level") == config.LEVEL_NCAA_DI]
    logger.info(f"Summary page — NCAA totals rows: {len(ncaa_from_summary)}")
    for row in ncaa_from_summary:
        logger.info(f"  {row}")

    # ── 2. Parse NCAA-specific page ────────────────────────────────────────────
    logger.info(f"\nFetching NCAA page: {ncaa_url}")
    ncaa_html = fetcher.get(ncaa_url)
    ncaa_parsed = parse_player_page(ncaa_html, PLAYER_ID)

    ncaa_totals  = [r for r in ncaa_parsed["totals"]   if r.get("level") == config.LEVEL_NCAA_DI]
    ncaa_pergame = [r for r in ncaa_parsed["per_game"] if r.get("level") == config.LEVEL_NCAA_DI]
    ncaa_adv     = [r for r in ncaa_parsed["advanced"] if r.get("level") == config.LEVEL_NCAA_DI]

    logger.info(f"NCAA page — NCAA totals rows:   {len(ncaa_totals)}")
    logger.info(f"NCAA page — NCAA per_game rows: {len(ncaa_pergame)}")
    logger.info(f"NCAA page — NCAA advanced rows: {len(ncaa_adv)}")

    if ncaa_totals:
        logger.info("\nSample totals rows:")
        for row in ncaa_totals:
            logger.info(f"  season={row.get('season')}  team={row.get('team')}  pts={row.get('pts')}  gp={row.get('gp')}")
    else:
        logger.warning("No NCAA totals found on NCAA page — parser may need adjustment for this page structure.")

    # ── 3. Summary ─────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    if ncaa_totals:
        # Check for 2023-24 specifically
        season_2024 = [r for r in ncaa_totals if r.get("season") == "2023-24"]
        if season_2024:
            print(f"SUCCESS: Found 2023-24 NCAA stats for {URL_SLUG}")
            for row in season_2024:
                print(f"  {row}")
        else:
            seasons = [r.get("season") for r in ncaa_totals]
            print(f"WARNING: NCAA stats found but not 2023-24. Seasons present: {seasons}")
    else:
        print("FAIL: No NCAA stats extracted from NCAA page. Parser needs updating.")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            import fetcher_browser
            fetcher_browser.close()
        except Exception:
            pass
