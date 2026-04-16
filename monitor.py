import sqlite3
import psycopg2
import time
import os

CHECKPOINT_DB = 'data/checkpoint.db'
PG_DSN = 'postgresql://localhost:5432/ncaa_basketball'
TOTAL_PLAYERS = 12749

def get_stats():
    ck = sqlite3.connect(CHECKPOINT_DB)
    rows = dict(ck.execute("SELECT status, count(*) FROM fetch_state GROUP BY status").fetchall())
    ck.close()

    pg = psycopg2.connect(PG_DSN)
    cur = pg.cursor()
    cur.execute("SELECT count(*) FROM players WHERE birthdate IS NOT NULL")
    with_dob = cur.fetchone()[0]
    pg.close()

    done = rows.get('done', 0)
    failed = rows.get('failed', 0)
    remaining = TOTAL_PLAYERS - done - failed
    return done, failed, remaining, with_dob

os.system('clear')
print("Birthdate scraper monitor — Ctrl+C to exit\n")

prev_done = None
while True:
    done, failed, remaining, with_dob = get_stats()
    speed = ''
    if prev_done is not None and done > prev_done:
        speed = f'  (+{done - prev_done}/30s)'
    prev_done = done

    pct = done / TOTAL_PLAYERS * 100
    bar_len = 40
    filled = int(bar_len * done / TOTAL_PLAYERS)
    bar = '█' * filled + '░' * (bar_len - filled)

    print(f'\r[{bar}] {pct:.1f}%  |  done={done:,}  failed={failed}  left={remaining:,}  dob={with_dob:,}{speed}   ', end='', flush=True)
    time.sleep(30)
