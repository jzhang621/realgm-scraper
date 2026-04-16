import pandas as pd
from sqlalchemy import create_engine

# Read CSV from parent directory
df = pd.read_csv('../data/processed/player_ratings_2026.csv')

# Add season column  
df['season'] = '2025-26'

# Create DB engine
engine = create_engine('postgresql://localhost:5432/ncaa_basketball')

# Load to database (append)
df.to_sql('player_ratings', engine, if_exists='append', index=False, method='multi', chunksize=1000)

print(f"✓ Loaded {len(df)} ratings to database")
