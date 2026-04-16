"""
compute_similarity.py — precompute top-8 similar player-seasons for the
top 100 rated players in 2025-26, across 3 segments:
  - production: all player-seasons, production stats only
  - position:   same pos_group, production stats only
  - age:        same age group (±1 year or same class), production stats only
"""

import psycopg2
import numpy as np

PG_DSN = 'postgresql://localhost:5432/ncaa_basketball'

PROD_FEATURES = [
    'pts', 'reb', 'ast', 'stl', 'blk',
    'fg3a', 'fg3_pct', 'fg_pct', 'ft_pct',
    'usg_pct', 'ts_pct', 'min',
]

CLASS_AGE = {'Fr': 18, 'RS-Fr': 18, 'So': 19, 'RS-So': 19,
             'Jr': 20, 'RS-Jr': 20, 'Sr': 21, 'RS-Sr': 22}

def height_to_inches(h):
    if not h:
        return None
    try:
        parts = h.split('-')
        return int(parts[0]) * 12 + int(parts[1])
    except Exception:
        return None

def effective_age(row):
    if row['age'] is not None:
        return row['age']
    return CLASS_AGE.get(row['class_year'])

def load_all(conn):
    cur = conn.cursor()
    cols = ['player_id', 'season', 'full_name', 'team', 'position', 'pos_group',
            'class_year', 'age', 'final_rating', 'height', 'weight'] + PROD_FEATURES
    cur.execute(f"SELECT {', '.join(cols)} FROM player_season_stats")
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return rows

def load_targets(conn, season='2025-26'):
    cur = conn.cursor()
    cur.execute("""
        SELECT player_id, season FROM player_season_stats
        WHERE season = %s
        ORDER BY final_rating DESC
    """, (season,))
    result = [(r[0], r[1]) for r in cur.fetchall()]
    cur.close()
    return result

def build_matrix(rows):
    """Return (matrix, valid_mask) after min-max scaling production features."""
    raw = []
    for r in rows:
        vals = [r[f] if r[f] is not None else np.nan for f in PROD_FEATURES]
        raw.append(vals)
    raw = np.array(raw, dtype=float)

    # Column-wise min-max, ignoring NaN
    col_min = np.nanmin(raw, axis=0)
    col_max = np.nanmax(raw, axis=0)
    span = col_max - col_min
    span[span == 0] = 1  # avoid div/0
    scaled = (raw - col_min) / span
    # fill remaining NaN with 0.5 (neutral)
    scaled = np.where(np.isnan(scaled), 0.5, scaled)
    return scaled

def top8_similar(target_idx, matrix, rows, exclude_pid, segment_mask):
    target_vec = matrix[target_idx]
    candidates = np.where(segment_mask)[0]
    # exclude same player entirely
    candidates = [i for i in candidates if rows[i]['player_id'] != exclude_pid]
    if not candidates:
        return []
    cand_matrix = matrix[candidates]
    diffs = cand_matrix - target_vec
    dists = np.sqrt((diffs ** 2).sum(axis=1))
    top = np.argsort(dists)[:8]
    return [(candidates[i], float(dists[i])) for i in top]

def setup_table(conn):
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS player_similarity")
    cur.execute("""
        CREATE TABLE player_similarity (
            player_id      TEXT,
            season         TEXT,
            segment        TEXT,
            rank           INT,
            sim_player_id  TEXT,
            sim_season     TEXT,
            sim_name       TEXT,
            sim_team       TEXT,
            sim_pos        TEXT,
            sim_rating     NUMERIC(6,2),
            score          NUMERIC(8,6),
            PRIMARY KEY (player_id, season, segment, rank)
        )
    """)
    conn.commit()
    cur.close()

def main():
    conn = psycopg2.connect(PG_DSN)
    print("Loading all player-seasons...")
    rows = load_all(conn)
    print(f"  {len(rows)} rows loaded")

    top100 = load_targets(conn, '2025-26')
    print(f"  {len(top100)} targets for 2025-26 loaded")

    print("Building feature matrix...")
    matrix = build_matrix(rows)

    # Build lookup: (player_id, season) -> index
    idx_map = {(r['player_id'], r['season']): i for i, r in enumerate(rows)}

    # Precompute effective age for all rows
    ages = [effective_age(r) for r in rows]

    setup_table(conn)
    cur = conn.cursor()

    print("Computing similarities...")
    for n, (pid, season) in enumerate(top100):
        key = (pid, season)
        if key not in idx_map:
            print(f"  [{n+1}] {pid} not found, skipping")
            continue

        ti = idx_map[key]
        tr = rows[ti]
        t_age = ages[ti]
        t_pos = tr['pos_group']

        # Masks
        all_mask       = np.ones(len(rows), dtype=bool)
        pos_mask       = np.array([r['pos_group'] == t_pos for r in rows])

        if t_age is not None:
            age_mask = np.array([
                a is not None and abs(a - t_age) <= 1
                for a in ages
            ])
        else:
            t_class = tr['class_year']
            age_mask = np.array([r['class_year'] == t_class for r in rows])

        segments = [
            ('production', all_mask),
            ('position',   pos_mask),
            ('age',        age_mask),
        ]

        for seg_name, mask in segments:
            results = top8_similar(ti, matrix, rows, pid, mask)
            for rank, (ci, score) in enumerate(results, 1):
                cr = rows[ci]
                cur.execute("""
                    INSERT INTO player_similarity
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                """, (
                    pid, season, seg_name, rank,
                    cr['player_id'], cr['season'],
                    cr['full_name'], cr['team'], cr['position'],
                    cr['final_rating'], round(score, 6)
                ))

        conn.commit()
        if (n + 1) % 100 == 0:
            print(f"  [{n+1}/{len(top100)}] done")

    cur.close()
    conn.close()
    print("\nDone. Verifying...")

    conn2 = psycopg2.connect(PG_DSN)
    cur2 = conn2.cursor()
    cur2.execute("SELECT segment, count(*) FROM player_similarity GROUP BY segment ORDER BY segment")
    for row in cur2.fetchall():
        print(f"  {row[0]}: {row[1]} rows")
    conn2.close()

if __name__ == '__main__':
    main()
