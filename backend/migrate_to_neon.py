"""
Migrate data from local PostgreSQL to Neon
"""
from sqlalchemy import create_engine, text
import os

# Local database
LOCAL_DB = "postgresql://localhost:5432/ncaa_basketball"

# Neon database
NEON_DB = "postgresql://neondb_owner:npg_fnWsN5LlozA7@ep-still-mode-am6nrcz1-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

print("Connecting to databases...")
local_engine = create_engine(LOCAL_DB)
neon_engine = create_engine(NEON_DB)

print("\n=== Step 1: Creating schema in Neon ===")
with open('schema.sql', 'r') as f:
    schema_sql = f.read()

# Use execution_options to set isolation level to AUTOCOMMIT
with neon_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    # Set search path to public schema
    conn.execute(text("SET search_path TO public;"))

    # Execute schema creation in chunks (to handle errors better)
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                conn.execute(text(statement))
            except Exception as e:
                # Skip errors for DROP statements and tables/views that might not exist
                if 'does not exist' not in str(e) and 'DROP' not in statement.upper():
                    print(f"Warning: {e}")

    print("✓ Schema created successfully")

print("\n=== Step 2: Clearing existing data ===")
# Clear existing data in reverse order (to respect foreign keys)
with neon_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    for table in ['player_ratings', 'player_stats_misc', 'player_stats_advanced', 'player_stats_pergame', 'teams', 'players']:
        try:
            conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            print(f"  Cleared {table}")
        except Exception as e:
            print(f"  Warning: {e}")

print("\n=== Step 3: Migrating data ===")

# Table migration order (respecting foreign keys)
tables = [
    'players',
    'teams',
    'player_stats_pergame',
    'player_stats_advanced',
    'player_stats_misc',
    'player_ratings'
]

with local_engine.connect() as local_conn, neon_engine.connect() as neon_conn:
    for table in tables:
        print(f"\nMigrating {table}...")

        # Get data from local
        result = local_conn.execute(text(f"SELECT * FROM {table}"))
        rows = result.fetchall()
        columns = result.keys()

        if not rows:
            print(f"  No data in {table}")
            continue

        print(f"  Found {len(rows)} rows")

        # Prepare insert statement
        cols = ', '.join(columns)
        placeholders = ', '.join([f':{col}' for col in columns])
        insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

        # Insert data in batches
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            batch_dicts = [dict(zip(columns, row)) for row in batch]
            neon_conn.execute(text(insert_sql), batch_dicts)
            print(f"  Inserted {min(i+batch_size, len(rows))}/{len(rows)} rows", end='\r')

        print(f"  ✓ Migrated {len(rows)} rows")

    neon_conn.commit()

print("\n\n=== Step 4: Verifying migration ===")
with neon_engine.connect() as conn:
    for table in tables:
        result = conn.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
        count = result.fetchone()[0]
        print(f"{table}: {count} rows")

print("\n✅ Migration complete!")
