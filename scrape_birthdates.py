"""
scrape_birthdates.py — scrape birthdates for rated players missing them.

Uses non-headless Playwright to bypass Cloudflare.
Saves HTML to cache, extracts birthdate, updates local DB.
Skips players already in checkpoint (their pages have no birthdate on RealGM).
"""

import asyncio
import hashlib
import os
import re
import sqlite3
import time
import random
import unicodedata

import psycopg2
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

RAW_PLAYERS = 'data/raw/players'
CHECKPOINT_DB = 'data/checkpoint.db'
PG_DSN = 'postgresql://localhost:5432/ncaa_basketball'

os.makedirs(RAW_PLAYERS, exist_ok=True)


def slugify(name: str) -> str:
    """Convert 'First Last Jr.' -> 'First-Last-Jr'"""
    name = unicodedata.normalize('NFD', name)
    name = name.encode('ascii', 'ignore').decode()
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '-', name.strip())
    return name


def get_targets():
    """Get player_id + full_name for rated players missing birthdate, not yet in checkpoint."""
    pg = psycopg2.connect(PG_DSN)
    pgcur = pg.cursor()
    pgcur.execute("""
        SELECT DISTINCT r.player_id::text, p.full_name
        FROM player_ratings r
        JOIN players p ON p.player_id = r.player_id::text
        WHERE p.birthdate IS NULL
        ORDER BY 1
    """)
    missing = pgcur.fetchall()
    pg.close()

    conn = sqlite3.connect(CHECKPOINT_DB)
    already = {row[0] for row in conn.execute('SELECT player_id FROM fetch_state').fetchall()}
    conn.close()

    targets = [(pid, name) for pid, name in missing if pid not in already]
    print(f'Total missing birthdate: {len(missing)}')
    print(f'Already in checkpoint (skip): {len(missing) - len(targets)}')
    print(f'To scrape: {len(targets)}')
    return targets


def cache_path(url: str) -> str:
    return os.path.join(RAW_PLAYERS, hashlib.md5(url.encode()).hexdigest() + '.html')


def mark_done(conn, player_id, url_slug):
    conn.execute(
        "INSERT OR REPLACE INTO fetch_state (player_id, url_slug, status, fetched_at) VALUES (?, ?, 'done', datetime('now'))",
        (player_id, url_slug)
    )
    conn.commit()


def mark_failed(conn, player_id, url_slug, error):
    conn.execute(
        "INSERT OR REPLACE INTO fetch_state (player_id, url_slug, status, error) VALUES (?, ?, 'failed', ?)",
        (player_id, url_slug, str(error)[:200])
    )
    conn.commit()


def extract_birthdate(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    born = soup.find('strong', string='Born:')
    if not born:
        return None
    try:
        from datetime import datetime
        text = born.find_next('a').text.strip()
        return datetime.strptime(text, '%b %d, %Y').date()
    except Exception:
        return None


async def scrape(targets):
    pg = psycopg2.connect(PG_DSN)
    pgcur = pg.cursor()
    ck = sqlite3.connect(CHECKPOINT_DB)

    found = 0
    failed = 0
    no_dob = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        for i, (player_id, full_name) in enumerate(targets):
            url_slug = slugify(full_name)
            url = f'https://basketball.realgm.com/player/{url_slug}/Summary/{player_id}'
            cp = cache_path(url)

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(random.uniform(2.5, 4.5))
                html = await page.content()

                # Save to cache
                with open(cp, 'w', encoding='utf-8') as f:
                    f.write(html)

                dob = extract_birthdate(html)
                if dob:
                    pgcur.execute(
                        "UPDATE players SET birthdate = %s WHERE player_id = %s AND birthdate IS NULL",
                        (str(dob), player_id)
                    )
                    pg.commit()
                    found += 1
                else:
                    no_dob += 1

                mark_done(ck, player_id, url_slug)

                if (i + 1) % 50 == 0:
                    print(f'[{i+1}/{len(targets)}] found={found} no_dob={no_dob} failed={failed}')

                # Burst pause every 100
                if (i + 1) % 100 == 0:
                    print(f'  Burst pause...')
                    await asyncio.sleep(random.uniform(15, 25))

            except Exception as e:
                failed += 1
                mark_failed(ck, player_id, url_slug, e)
                print(f'  FAIL {player_id} {full_name}: {e}')

        await browser.close()

    pg.close()
    ck.close()
    print(f'\nDone. found={found} no_dob={no_dob} failed={failed}')

    # Final coverage
    pg2 = psycopg2.connect(PG_DSN)
    pgcur2 = pg2.cursor()
    pgcur2.execute("SELECT count(*) FROM players WHERE birthdate IS NOT NULL")
    print(f'Total players with birthdate: {pgcur2.fetchone()[0]} / 12749')
    pg2.close()


if __name__ == '__main__':
    targets = get_targets()
    if targets:
        asyncio.run(scrape(targets))
    else:
        print('Nothing to scrape.')
