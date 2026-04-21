"""
geocode_hometowns.py — geocode unique player hometowns via Nominatim (OSM).
Rate limited to 1 req/sec. Resumable — skips already-processed hometowns.
"""

import psycopg2
import requests
import time

PG_DSN = 'postgresql://localhost:5432/ncaa_basketball'
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
HEADERS = {'User-Agent': 'nilpro-basketball-app/1.0'}

def main():
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()

    # Get hometowns not yet processed
    cur.execute("""
        SELECT DISTINCT p.hometown
        FROM players p
        WHERE p.hometown IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM hometown_coords hc WHERE hc.hometown = p.hometown
          )
        ORDER BY p.hometown
    """)
    hometowns = [r[0] for r in cur.fetchall()]
    print(f"{len(hometowns)} hometowns to geocode")

    found = 0
    failed = 0

    for i, hometown in enumerate(hometowns):
        try:
            resp = requests.get(NOMINATIM_URL, params={
                'q': hometown,
                'format': 'json',
                'limit': 1,
            }, headers=HEADERS, timeout=10)
            results = resp.json()

            if results:
                lat = float(results[0]['lat'])
                lng = float(results[0]['lon'])
                cur.execute(
                    "INSERT INTO hometown_coords (hometown, lat, lng, failed) VALUES (%s, %s, %s, FALSE) ON CONFLICT DO NOTHING",
                    (hometown, lat, lng)
                )
                found += 1
            else:
                cur.execute(
                    "INSERT INTO hometown_coords (hometown, lat, lng, failed) VALUES (%s, NULL, NULL, TRUE) ON CONFLICT DO NOTHING",
                    (hometown,)
                )
                failed += 1

            conn.commit()

        except Exception as e:
            print(f"  ERROR {hometown}: {e}")
            failed += 1

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(hometowns)}] found={found} failed={failed}")

        time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

    cur.close()
    conn.close()
    print(f"\nDone. found={found} failed={failed}")

if __name__ == '__main__':
    main()
