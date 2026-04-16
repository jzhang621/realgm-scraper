"""
storage.py — Append-safe CSV writers for all output files.

Column definitions exactly match what parsers/profile.py produces.

Each writer:
  - Opens in append mode
  - Writes the header row only if the file is new / empty
  - Accepts None values gracefully (written as empty string)
  - Is thread-UNsafe (single-threaded scraper only)
"""

import csv
import os
import logging

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Column definitions — order matters for CSV column layout
# Exactly matches parsers/profile.py output keys.
# ---------------------------------------------------------------------------

PLAYERS_COLS = [
    "player_id",
    "full_name",
    "position",
    "jersey_number",
    "height_raw",
    "height_ft",
    "height_cm",
    "weight_raw",
    "weight_lbs",
    "weight_kg",
    "dob_raw",
    "dob",
    "hometown",
    "nationality",
    "nba_status",
    "draft_raw",
    "draft_year",
    "draft_round",
    "draft_pick",
    "draft_team",
    "pre_draft_raw",
    "pre_draft_team",
    "pre_draft_class",
    "high_school_raw",
    "high_school",
    "high_school_location",
    "current_team",
    "current_team_level",
]

SEASON_ROSTERS_COLS = [
    "player_id",
    "player_name",
    "url_slug",
    "season",
    "team",
    "conference",
    "position",
    "class_year",
]

# Shared base columns for all stat types
_STAT_BASE_COLS = [
    "player_id",
    "season",
    "age",
    "level",
    "league_name",
    "team",
    "class_year",
    "stat_type",
    "gp",
    "gs",
]

PERGAME_COLS = _STAT_BASE_COLS + [
    "min",
    "pts",
    "fgm",
    "fga",
    "fg_pct",
    "fg3m",
    "fg3a",
    "fg3_pct",
    "ftm",
    "fta",
    "ft_pct",
    "off_reb",
    "def_reb",
    "trb",
    "ast",
    "stl",
    "blk",
    "tov",
    "pf",
]

TOTALS_COLS = PERGAME_COLS  # same shape, different values (totals vs per-game)

ADVANCED_COLS = _STAT_BASE_COLS + [
    "ts_pct",
    "efg_pct",
    "orb_pct",
    "drb_pct",
    "trb_pct",
    "ast_pct",
    "tov_pct",
    "stl_pct",
    "blk_pct",
    "usg_pct",
    "total_s_pct",
    "ppr",
    "pps",
    "ortg",
    "drtg",
    "per",
]

MISC_COLS = _STAT_BASE_COLS + [
    "dbl_dbl",
    "tpl_dbl",
    "pts_40",
    "reb_20",
    "ast_20",
    "techs",
    "hob",
    "ast_to_ratio",
    "stl_to_ratio",
    "ft_per_fga",
    "wins",
    "losses",
    "win_pct",
    "ows",
    "dws",
    "ws",
]

AWARDS_COLS = [
    "player_id",
    "level",
    "award_name",
    "award_date",
]

TRANSACTIONS_COLS = [
    "player_id",
    "level",
    "transaction_date",
    "transaction_text",
]

EVENTS_COLS = [
    "player_id",
    "level",
    "event_name",
    "year",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _write_rows(filepath: str, cols: list, rows: list):
    """
    Append rows to a CSV file.
    Writes header if file is new or empty.
    Each row is a dict; missing keys written as empty string.
    """
    if not rows:
        return

    _ensure_dir(filepath)
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=cols,
            extrasaction="ignore",   # silently drop unknown keys
            restval="",              # None / missing → empty string
        )
        if not file_exists:
            writer.writeheader()
        for row in rows:
            # Normalise None → ""
            clean = {k: ("" if v is None else v) for k, v in row.items()}
            writer.writerow(clean)

    logger.debug(f"Wrote {len(rows)} rows to {filepath}")


def _write_one(filepath: str, cols: list, row: dict):
    _write_rows(filepath, cols, [row])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_player(player: dict):
    """Write one row to players.csv (player bio / profile)."""
    _write_one(config.CSV_PLAYERS, PLAYERS_COLS, player)


def write_season_roster(rows: list):
    """Write season listing rows to season_rosters.csv."""
    _write_rows(config.CSV_SEASON_ROSTERS, SEASON_ROSTERS_COLS, rows)


def write_pergame(rows: list):
    """Write per-game stat rows."""
    _write_rows(config.CSV_PERGAME, PERGAME_COLS, rows)


def write_totals(rows: list):
    """Write totals stat rows."""
    _write_rows(config.CSV_TOTALS, TOTALS_COLS, rows)


def write_advanced(rows: list):
    """Write advanced stat rows."""
    _write_rows(config.CSV_ADVANCED, ADVANCED_COLS, rows)


def write_misc(rows: list):
    """Write misc stat rows."""
    _write_rows(config.CSV_MISC, MISC_COLS, rows)


def write_awards(rows: list):
    """Write award rows."""
    _write_rows(config.CSV_AWARDS, AWARDS_COLS, rows)


def write_transactions(rows: list):
    """Write transaction rows."""
    _write_rows(config.CSV_TRANSACTIONS, TRANSACTIONS_COLS, rows)


def write_events(rows: list):
    """Write event rows."""
    _write_rows(config.CSV_EVENTS, EVENTS_COLS, rows)


def flush_player_data(parsed: dict):
    """
    Convenience: write all sections returned by parse_player_page() in one call.

    parsed = {
        "profile":      dict | None,
        "per_game":     [...],
        "totals":       [...],
        "advanced":     [...],
        "misc":         [...],
        "awards":       [...],
        "transactions": [...],
        "events":       [...],
    }
    """
    if parsed.get("profile"):
        write_player(parsed["profile"])

    write_pergame(parsed.get("per_game", []))
    write_totals(parsed.get("totals", []))
    write_advanced(parsed.get("advanced", []))
    write_misc(parsed.get("misc", []))
    write_awards(parsed.get("awards", []))
    write_transactions(parsed.get("transactions", []))
    write_events(parsed.get("events", []))
