import json
with open('all_projects.json') as f:
    projects = json.load(f)
with open('all_listings.json') as f:
    listings = json.load(f)

print('First project:')
print(json.dumps(projects[0], indent=2))

print('\nTop 5 projects by price_max:')
top = sorted(projects, key=lambda x: x.get('price_max', 0) or 0, reverse=True)[:5]
for p in top:
    pid = p['project_id']
    pmax = p.get('price_max')
    pmin = p.get('price_min')
    name = p.get('apartment_name')
    print(f'  {pid} {name}: min={pmin}, max={pmax}')

print('\nProject P30001 detail:')
p1 = next(p for p in projects if p['project_id'] == 'P30001')
print(f'  price_min={p1.get("price_min")}, price_max={p1.get("price_max")}')
proj_listings = [l for l in listings if l.get('project_id') == 'P30001'][:3]
print(f'  Project listings ({len(proj_listings)} shown):')
for l in proj_listings:
    print(f'    {l["listing_id"]}: price={l.get("price")}, area={l.get("carpet_area")}')

# If listing price=4090000 rupees and project price_min=80
# Then project is in lakhs: 80 lakhs = 8,000,000 rupees
# But 4090000 / 100000 = 40.9 lakhs - plausible range
# 4090000 rupees = 40.9 lakhs

# Check if project price_max makes sense if in lakhs
print('\nProject price analysis (if in lakhs):')
for p in top[:3]:
    pmax = p.get('price_max') or 0
    pmin = p.get('price_min') or 0
    print(f'  {p["project_id"]}: max={pmax} lakhs = {pmax * 100000:.0f} rupees')

# Distribution of listing prices
prices = sorted([l.get('price', 0) for l in listings if l.get('price')])
print(f'\nListing price stats:')
print(f'  Min: {min(prices)}')
print(f'  Max: {max(prices)}')
print(f'  Median: {prices[len(prices)//2]}')

# All project price_max values
proj_maxes = sorted([p.get('price_max', 0) or 0 for p in projects], reverse=True)
print(f'\nProject price_max values:')
print(f'  Min: {min(proj_maxes)}')
print(f'  Max: {max(proj_maxes)}')
print(f'  Top 10: {proj_maxes[:10]}')

# Q7: The problem says price_max_inr - which unit is it?
# Let's check: if project price_max = 97.8 and listing prices are 4-21M rupees
# 97.8 crore = 978,000,000 rupees - too expensive for Pune
# 97.8 lakh = 9,780,000 rupees - plausible for 1BHK in good area
# But for a PROJECT max, 97.8 lakh is quite low
# More likely: project price_max is in LAKHS
# 97.8 lakh = 97,80,000 rupees for max of project
# But top listings are 21M = 2.1 crore - so project max should be at least 2.1 crore = 210 lakhs
# Hmm. So 97.8 might actually be something else

# Actually: P30001 has price_min=80.0 and price_max=3.22
# That means MIN > MAX? Unless they're in different units...
# Or perhaps price_max=3.22 means something else

# Let's look at project with listing prices
print('\nChecking project P30030 (if it has listings):')
for proj in projects[:20]:
    pid = proj['project_id']
    plistings = [l for l in listings if l.get('project_id') == pid]
    if plistings:
        listing_prices = [l.get('price', 0) for l in plistings if l.get('price')]
        print(f'  {pid}: proj_min={proj.get("price_min")}, proj_max={proj.get("price_max")}')
        print(f'    Listing prices: {sorted(listing_prices)[:5]}')
        break
