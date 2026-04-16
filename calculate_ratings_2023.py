"""
Calculate player ratings for 2022-23 NCAA D1 season using RealGM data.
Based on the NextOnes rating system formula.
"""
import csv

print("Loading data...")

team_games = {}
with open('data/processed/team_games_2023.csv', 'r') as f:
    for row in csv.DictReader(f):
        team_games[row['team']] = int(row['total_games'])
print(f"✓ Loaded {len(team_games)} teams")

stats_data = []
non_d1_teams = set()
with open('data/processed/player_stats_pergame.csv', 'r') as f:
    for row in csv.DictReader(f):
        if row['season'] == '2022-23':
            if row['team'] in team_games:
                stats_data.append(row)
            else:
                non_d1_teams.add(row['team'])
print(f"✓ Loaded {len(stats_data)} player stat records (D1 only)")
print(f"✓ Filtered out {len(non_d1_teams)} non-D1 teams")

misc_data = {}
with open('data/processed/player_stats_misc.csv', 'r') as f:
    for row in csv.DictReader(f):
        if row['season'] == '2022-23' and row['team'] in team_games:
            misc_data[row['player_id']] = row
print(f"✓ Loaded misc stats for {len(misc_data)} players")

player_bio = {}
with open('data/processed/players.csv', 'r') as f:
    for row in csv.DictReader(f):
        player_bio[row['player_id']] = row
print(f"✓ Loaded bio data for {len(player_bio)} players\n")

print("Calculating percentiles...")

all_stats = {
    'minutes': [], 'points': [], 'three_points_made': [], 'three_points_perc': [],
    'field_goals_made': [], 'field_goals_perc': [], 'free_throw_perc': [],
    'assists': [], 'rebounds': [], 'blocks': [], 'steals': []
}

for row in stats_data:
    try:
        all_stats['minutes'].append(float(row['min']) if row['min'] else 0)
        all_stats['points'].append(float(row['pts']) if row['pts'] else 0)
        all_stats['three_points_made'].append(float(row['fg3m']) if row['fg3m'] else 0)
        all_stats['three_points_perc'].append(float(row['fg3_pct']) if row['fg3_pct'] else 0)
        all_stats['field_goals_made'].append(float(row['fgm']) if row['fgm'] else 0)
        all_stats['field_goals_perc'].append(float(row['fg_pct']) if row['fg_pct'] else 0)
        all_stats['free_throw_perc'].append(float(row['ft_pct']) if row['ft_pct'] else 0)
        all_stats['assists'].append(float(row['ast']) if row['ast'] else 0)
        all_stats['rebounds'].append(float(row['trb']) if row['trb'] else 0)
        all_stats['blocks'].append(float(row['blk']) if row['blk'] else 0)
        all_stats['steals'].append(float(row['stl']) if row['stl'] else 0)
    except (ValueError, KeyError):
        pass

for key in all_stats:
    all_stats[key].sort()

def get_percentile(value, sorted_list):
    if not sorted_list or value is None:
        return 0
    count = sum(1 for x in sorted_list if x < value)
    return max(1, min(100, int((count / len(sorted_list)) * 100 + 0.5)))

print("Calculating ratings...")

ratings = []
for row in stats_data:
    try:
        player_id = row['player_id']
        team = row['team']

        gp       = int(row['gp'])   if row['gp']      else 0
        minutes  = float(row['min']) if row['min']     else 0
        pts      = float(row['pts']) if row['pts']     else 0
        fg3m     = float(row['fg3m']) if row['fg3m']   else 0
        fg3_pct  = float(row['fg3_pct']) if row['fg3_pct'] else 0
        fgm      = float(row['fgm']) if row['fgm']     else 0
        fg_pct   = float(row['fg_pct']) if row['fg_pct'] else 0
        ft_pct   = float(row['ft_pct']) if row['ft_pct'] else 0
        ast      = float(row['ast']) if row['ast']     else 0
        reb      = float(row['trb']) if row['trb']     else 0
        blk      = float(row['blk']) if row['blk']     else 0
        stl      = float(row['stl']) if row['stl']     else 0

        misc = misc_data.get(player_id, {})
        double_doubles = int(misc.get('dbl_dbl', 0)) if misc.get('dbl_dbl') else 0
        triple_doubles = int(misc.get('tpl_dbl', 0)) if misc.get('tpl_dbl') else 0

        if gp == 0 or minutes == 0:
            continue

        min_per    = get_percentile(minutes, all_stats['minutes'])
        pts_per    = get_percentile(pts,     all_stats['points'])
        pm3_per    = get_percentile(fg3m,    all_stats['three_points_made'])
        p3_pct_per = get_percentile(fg3_pct, all_stats['three_points_perc'])
        fgm_per    = get_percentile(fgm,     all_stats['field_goals_made'])
        fg_pct_per = get_percentile(fg_pct,  all_stats['field_goals_perc'])
        ft_pct_per = get_percentile(ft_pct,  all_stats['free_throw_perc'])
        ast_per    = get_percentile(ast,     all_stats['assists'])
        reb_per    = get_percentile(reb,     all_stats['rebounds'])
        blk_per    = get_percentile(blk,     all_stats['blocks'])
        stl_per    = get_percentile(stl,     all_stats['steals'])

        base_rating = (
            pts_per * 0.575 +
            ast_per * 0.100 +
            reb_per * 0.050 +
            blk_per * 0.150 +
            stl_per * 0.125
        )

        team_total_games = team_games.get(team, 32)
        games_played_pct = gp / team_total_games if team_total_games > 0 else 1.0
        game_adj = -((base_rating / 15) * (1 - games_played_pct)) ** 2

        min_boost = ((100 - base_rating) / 1250 * min_per) ** 2

        three_product = pm3_per * p3_pct_per
        if three_product <= 2500:
            three_boost = -((base_rating / 50) * (1 - three_product / 10000))
        else:
            three_boost = ((100 - base_rating) / 1500 * (three_product / 100)) ** 2

        fg_product = fgm_per * fg_pct_per
        if fg_product <= 2500:
            fg_boost = -(fg_product / 1000)
        else:
            fg_boost = ((100 - base_rating) / 1000 * (fg_product / 100)) ** 2

        ast_boost          = ((100 - base_rating) / 1500 * ast_per) ** 2
        blk_boost          = ((100 - base_rating) / 1250 * blk_per) ** 2
        dd_rate            = double_doubles / gp if gp > 0 else 0
        double_double_boost = ((100 - base_rating) / 10 * dd_rate) ** 2
        td_rate            = triple_doubles / gp if gp > 0 else 0
        triple_double_boost = ((100 - base_rating) / 5 * td_rate) ** 2

        if ft_pct < 0.7:
            free_throw_boost = -2 * ft_pct * ((100 - base_rating) / 25)
        else:
            free_throw_boost = ft_pct * ((100 - base_rating) / 25)

        final_rating = (
            base_rating + game_adj + three_boost + fg_boost + min_boost +
            ast_boost + blk_boost + double_double_boost + triple_double_boost +
            free_throw_boost
        )

        if final_rating < 60:
            final_rating = final_rating / 1000 + 60

        two_way = 'Y' if pts_per >= 85 and stl_per >= 50 and blk_per >= 50 else 'N'
        bio = player_bio.get(player_id, {})

        ratings.append({
            'player_id': player_id,
            'full_name': bio.get('full_name', ''),
            'team': team,
            'position': bio.get('position', ''),
            'height': bio.get('height_ft', ''),
            'weight': bio.get('weight_lbs', ''),
            'hometown': bio.get('hometown', ''),
            'gp': gp,
            'minutes': round(minutes, 1),
            'pts': round(pts, 1),
            'fg3m': round(fg3m, 1),
            'fg3_pct': round(fg3_pct, 3),
            'fgm': round(fgm, 1),
            'fg_pct': round(fg_pct, 3),
            'ft_pct': round(ft_pct, 3),
            'ast': round(ast, 1),
            'reb': round(reb, 1),
            'blk': round(blk, 1),
            'stl': round(stl, 1),
            'double_doubles': double_doubles,
            'triple_doubles': triple_doubles,
            'MIN_PER': min_per, 'PTS_PER': pts_per, 'PM3_PER': pm3_per,
            'P3PCT_PER': p3_pct_per, 'FGM_PER': fgm_per, 'FGPCT_PER': fg_pct_per,
            'FTPCT_PER': ft_pct_per, 'AST_PER': ast_per, 'REB_PER': reb_per,
            'BLK_PER': blk_per, 'STL_PER': stl_per,
            'base_rating': round(base_rating, 2),
            'game_adj': round(game_adj, 2),
            'min_boost': round(min_boost, 2),
            'three_boost': round(three_boost, 2),
            'fg_boost': round(fg_boost, 2),
            'ast_boost': round(ast_boost, 2),
            'blk_boost': round(blk_boost, 2),
            'double_double_boost': round(double_double_boost, 2),
            'triple_double_boost': round(triple_double_boost, 2),
            'free_throw_boost': round(free_throw_boost, 2),
            'final_rating': round(final_rating, 2),
            'two_way': two_way
        })

    except Exception as e:
        print(f"Error processing player {player_id}: {e}")
        continue

ratings.sort(key=lambda x: x['final_rating'], reverse=True)
print(f"✓ Calculated ratings for {len(ratings)} players\n")

output_file = 'data/processed/player_ratings_2023.csv'
with open(output_file, 'w', newline='') as f:
    if ratings:
        writer = csv.DictWriter(f, fieldnames=ratings[0].keys())
        writer.writeheader()
        writer.writerows(ratings)

print(f"{'='*70}")
print(f"✓ Saved ratings to {output_file}")
print(f"{'='*70}\n")

print("TOP 10 PLAYERS (2022-23):")
print(f"{'Rank':<5} {'Player':<25} {'Team':<20} {'Rating':<8}")
print("-" * 70)
for i, p in enumerate(ratings[:10], 1):
    print(f"{i:<5} {p['full_name']:<25} {p['team']:<20} {p['final_rating']:<8}")

print(f"\n{'='*70}")
print(f"Rating distribution:")
print(f"  90+:     {sum(1 for p in ratings if p['final_rating'] >= 90)} players")
print(f"  80-89:   {sum(1 for p in ratings if 80 <= p['final_rating'] < 90)} players")
print(f"  70-79:   {sum(1 for p in ratings if 70 <= p['final_rating'] < 80)} players")
print(f"  60-69:   {sum(1 for p in ratings if 60 <= p['final_rating'] < 70)} players")
print(f"  Two-way: {sum(1 for p in ratings if p['two_way'] == 'Y')} players")
print(f"{'='*70}\n")
