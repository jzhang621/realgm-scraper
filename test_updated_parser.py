"""
Test the updated parser with A.C. Bryant's page
"""
from parsers.profile import parse_player_page

# Read the saved HTML
with open("ac_bryant_debug.html", "r") as f:
    html = f.read()

print("Testing updated parser with A.C. Bryant (212898)...")
print("=" * 60)

result = parse_player_page(html, "212898")

print(f"\nProfile data:")
print(f"  Name: {result['profile'].get('full_name')}")
print(f"  Position: {result['profile'].get('position')}")

print(f"\nStats counts:")
print(f"  Per Game rows: {len(result['per_game'])}")
print(f"  Totals rows: {len(result['totals'])}")
print(f"  Advanced rows: {len(result['advanced'])}")
print(f"  Misc rows: {len(result['misc'])}")
print(f"  Awards: {len(result['awards'])}")

if result['per_game']:
    print(f"\nSample Per Game stats (first 3 rows):")
    for i, row in enumerate(result['per_game'][:3]):
        print(f"  {row.get('season')}: {row.get('team')} - " +
              f"{row.get('gp')}GP, {row.get('pts')}PPG, " +
              f"{row.get('trb')}RPG, {row.get('ast')}APG")
else:
    print("\n✗ NO PER GAME STATS FOUND!")

if result['awards']:
    print(f"\nAwards:")
    for award in result['awards']:
        print(f"  {award.get('award_name')} ({award.get('award_date')})")
