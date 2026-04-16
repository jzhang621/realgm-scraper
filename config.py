import os

# Seasons to scrape (ending year of season)
# Temporarily testing 2024 only
SEASONS = [2024]

BASE_URL = "https://basketball.realgm.com"

# Paths
ROOT_DIR        = os.path.dirname(os.path.abspath(__file__))
RAW_DIR         = os.path.join(ROOT_DIR, "data", "raw")
RAW_LISTINGS    = os.path.join(RAW_DIR, "listings")
RAW_PLAYERS     = os.path.join(RAW_DIR, "players")
PROCESSED_DIR   = os.path.join(ROOT_DIR, "data", "processed")
CHECKPOINT_DB   = os.path.join(ROOT_DIR, "data", "checkpoint.db")

# Output CSVs
CSV_PLAYERS         = os.path.join(PROCESSED_DIR, "players.csv")
CSV_SEASON_ROSTERS  = os.path.join(PROCESSED_DIR, "season_rosters.csv")
CSV_PERGAME         = os.path.join(PROCESSED_DIR, "player_stats_pergame.csv")
CSV_TOTALS          = os.path.join(PROCESSED_DIR, "player_stats_totals.csv")
CSV_ADVANCED        = os.path.join(PROCESSED_DIR, "player_stats_advanced.csv")
CSV_MISC            = os.path.join(PROCESSED_DIR, "player_stats_misc.csv")
CSV_AWARDS          = os.path.join(PROCESSED_DIR, "player_awards.csv")
CSV_TRANSACTIONS    = os.path.join(PROCESSED_DIR, "player_transactions.csv")
CSV_EVENTS          = os.path.join(PROCESSED_DIR, "player_events.csv")

# Rate limiting
SLEEP_MIN           = 2.0
SLEEP_MAX           = 4.0
BURST_EVERY         = 50       # take a long pause every N requests
BURST_SLEEP_MIN     = 15.0
BURST_SLEEP_MAX     = 30.0

# Retry
MAX_RETRIES         = 4
RETRY_BASE_SLEEP    = 5.0      # doubles each retry: 5, 10, 20, 40

# Level enum values (stored in CSVs)
LEVEL_NCAA_DI           = "NCAA_DI"
LEVEL_NCAA_JUCO         = "NCAA_JUCO"
LEVEL_INTERNATIONAL     = "INTERNATIONAL"
LEVEL_NBA               = "NBA"
LEVEL_NBA_SUMMER        = "NBA_SUMMER"
LEVEL_G_LEAGUE          = "G_LEAGUE"
LEVEL_G_LEAGUE_EVENTS   = "G_LEAGUE_EVENTS"
LEVEL_HIGH_SCHOOL       = "HIGH_SCHOOL"
LEVEL_NATIONAL          = "NATIONAL"
LEVEL_AAU               = "AAU"
