import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
REFERENCE = datetime(2026, 9, 10, 0, 0, 0, tzinfo=IST)
REF_MINUS_7 = REFERENCE - timedelta(days=7)

with open('all_listings.json') as f:
    all_listings = json.load(f)
with open('all_rentals.json') as f:
    all_rentals = json.load(f)
with open('all_projects.json') as f:
    all_projects = json.load(f)

unique_listings = {l['listing_id']: l for l in all_listings}
unique_projects = {p['project_id']: p for p in all_projects}

print("=== IDENTIFYING FAKE AND CORRUPT LISTINGS ===")

# Price/sqft extreme outliers (4 listings with p/sqft > 90000)
extreme_ppsqft = []
for lid, l in unique_listings.items():
    price = l.get('price', 0)
    area = l.get('carpet_area', 1)
    if area and area > 0:
        ppsqft = price / area
        if ppsqft > 50000:  # extreme outlier
            extreme_ppsqft.append((ppsqft, lid, price, area, l.get('locality')))

extreme_ppsqft.sort(reverse=True)
print("\nExtreme price/sqft outliers (>50000):")
for pps, lid, price, area, loc in extreme_ppsqft:
    l = unique_listings[lid]
    print(f"  {lid}: pps={pps:.0f}, price={price}, area={area}, loc={loc}, bed={l.get('bedroom')}")
    print(f"    apartment={l.get('apartment_name')}, is_live={l.get('is_live')}")
    print(f"    desc: {l.get('description', '')[:100]}")

# MAG-3001519: area=73 - check this
print("\nChecking MAG-3001519:")
l = unique_listings.get('MAG-3001519')
if l:
    print(json.dumps(l, indent=2))

# Check if these listings are 'corrupt' (impossible) or 'fake' (deliberate fraud)
# Corrupt = physically impossible data
# Fake = real listing data but fabricated property

# MAG-3001519 has carpet_area=73 for "2 BHK independent house" - impossible
# The extreme price/sqft listings - are these corrupt or fake?

# Looking at the extreme outliers:
# - area=73 for 2BHK = physically impossible -> CORRUPT
# - What about the price/sqft outliers? Price could be real if area is tiny
# - Let's check all fields carefully

print("\n=== CHECKING IMPOSSIBLE COMBINATIONS ===")
corrupt_ids = []
for lid, l in unique_listings.items():
    ca = l.get('carpet_area')
    sba = l.get('super_built_up_area') or l.get('super_builtup_area')
    price = l.get('price')
    floor_ = l.get('floor')
    total_f = l.get('total_floors')
    bed = l.get('bedroom')
    bath = l.get('bathroom')
    balcony = l.get('balcony')
    ptype = l.get('property_type')
    
    issues = []
    
    # Area checks
    if ca is not None and ca <= 0:
        issues.append(f"carpet_area={ca} (non-positive)")
    if ca is not None and bed is not None and bed >= 2:
        # 2BHK must have at least 400 sqft
        if ca < 200:
            issues.append(f"carpet_area={ca} too small for {bed}BHK")
    
    # Price checks  
    if price is not None and price <= 0:
        issues.append(f"price={price}")
    
    # Floor checks
    if floor_ is not None and total_f is not None and floor_ > total_f:
        issues.append(f"floor({floor_}) > total_floors({total_f})")
    
    # Carpet > super built-up
    if ca and sba and ca > sba:
        issues.append(f"carpet_area({ca}) > super_built_up_area({sba})")
    
    # Plot/land cannot be furnished
    if ptype == 'plot' and l.get('furnishing') not in [None, '', 'unfurnished']:
        issues.append(f"plot is furnished ({l.get('furnishing')})")
    
    if issues:
        corrupt_ids.append(lid)
        print(f"  CORRUPT {lid}: {', '.join(issues)}")

q4 = sorted(set(corrupt_ids))
print(f"\nQ4 corrupt_listing_ids: {q4}")

# Now for FAKE listings - not corrupt but deliberately fraudulent
# From the statement: "They exist to generate enquiries"
# Key patterns for fake listings in real estate:
# 1. Price way below market (bait)
# 2. Listed by a "power user" contact (same contact for many listings)
# 3. Or: price_per_sqft is extreme outlier within locality

# Let's check: are the extreme p/sqft outliers potentially bait listings?
# In real estate scams: very low prices attract enquiries
# Very high prices per sqft could be mistakes/spam

# Aundh has avg p/sqft around 9000-10000 for genuine listings
# But 92406 and 128541 are 10x higher
# These are not "too good to be true" (not underpriced), they're overpriced
# Overpriced bait is less common

# Actually, looking at the descriptions again:
# SQU-3001712: 'Urgent sale - owner relocating.' - this is a common fake phrase!
# Let me look at all descriptions containing suspicious patterns

print("\n=== DESCRIPTION ANALYSIS FOR FAKE SIGNALS ===")
fake_phrases = ['urgent', 'relocating', 'must sell', 'below market', 'negotiable', 'immediate', 'motivated seller']
for lid, l in sorted(unique_listings.items()):
    desc = (l.get('description') or '').lower()
    for phrase in fake_phrases:
        if phrase in desc:
            print(f"  {lid}: phrase='{phrase}', p/sqft={l.get('price',0)/l.get('carpet_area',1):.0f}")
            print(f"    desc: {l.get('description', '')[:120]}")
            break

# Check locality-level analysis for price outliers
# Group by locality, find which listings are outliers
print("\n=== LOCALITY PRICE/SQFT ANALYSIS ===")
loc_listings = defaultdict(list)
for lid, l in unique_listings.items():
    if lid not in set(q4):  # exclude corrupt
        price = l.get('price', 0)
        area = l.get('carpet_area', 1)
        if area and area > 0:
            ppsqft = price / area
            loc_listings[l.get('locality', '')].append((ppsqft, lid))

# For each locality, find outliers
fake_candidates = []
for loc, vals in sorted(loc_listings.items()):
    ppss = [v[0] for v in vals]
    if len(ppss) < 2:
        continue
    med = statistics.median(ppss)
    
    if len(ppss) >= 3:
        std = statistics.stdev(ppss)
        for pps, lid in vals:
            z = (pps - med) / std if std > 0 else 0
            if abs(z) > 2.5:  # 2.5 sigma outlier
                l = unique_listings[lid]
                print(f"  {loc}: OUTLIER {lid} pps={pps:.0f} (med={med:.0f}, z={z:.1f}), is_live={l.get('is_live')}")
                fake_candidates.append((abs(z), lid, pps, med, loc))
    else:
        print(f"  {loc}: only {len(ppss)} listings, no outlier detection")

# Looking at the data:
# The 5 extreme outliers (>90000 ppsqft) are in: aundh, hadapsar, hinjewadi, kothrud, wakad
# These appear to be in areas where other listings are 8000-14000 ppsqft
# They're clear outliers

# What about ZER-3001479: pps=3901 (lowest) in kharadi?
# kharadi avg seems to be around 9000-14000
# 3901 is also an outlier (on the low side = underpriced = more typical of bait)

print("\n=== FAKE LISTING CANDIDATES ===")
print("Top outliers (most suspicious):")
fake_candidates.sort(reverse=True)
for z, lid, pps, med, loc in fake_candidates[:10]:
    l = unique_listings[lid]
    print(f"  z={z:.1f} {lid}: pps={pps:.0f} (med={med:.0f}), loc={loc}, is_live={l.get('is_live')}, price={l.get('price')}, area={l.get('carpet_area')}")

# ZER-3001479 specific check
print("\nZER-3001479:")
l = unique_listings.get('ZER-3001479')
if l:
    print(json.dumps(l, indent=2))

# What if ALL the extreme outliers (pps > 90000) are just corrupt (area=137 for 4BHK villa)?
# Let's check them
for pps, lid, price, area, loc in extreme_ppsqft:
    l = unique_listings[lid]
    print(f"\nExtreme outlier {lid} (pps={pps:.0f}):")
    print(f"  bed={l.get('bedroom')}, area={area}, price={price}, type={l.get('property_type')}, loc={loc}")
    # 137 sqft for 4BHK villa = IMPOSSIBLE
    if l.get('bedroom') and l.get('bedroom') >= 2 and area < 200:
        print(f"  --> CORRUPT: {l.get('bedroom')}BHK but only {area} sqft!")

# FINAL Q4 and Q9
print("\n=== FINAL Q4 and Q9 ===")

# Q4: Corrupt listings - impossible physical combinations
# - MAG-3001519: 2BHK but area=73 sqft (impossible)
# - MAG-3001327: 4BHK villa but area=137 sqft (impossible) -> pps=98321
# - What others?

# Check all listings for impossible area for bedroom count
for lid, l in sorted(unique_listings.items()):
    bed = l.get('bedroom')
    ca = l.get('carpet_area')
    ptype = l.get('property_type')
    
    if bed and ca:
        # Minimum reasonable area per BHK
        min_area = bed * 150  # 150 sqft per bedroom minimum
        if ca < min_area and ptype not in ['plot']:
            print(f"  AREA TOO SMALL: {lid} - {bed}BHK but area={ca} (min expected ~{min_area})")

# Also check: plot can't have bedrooms
for lid, l in sorted(unique_listings.items()):
    ptype = l.get('property_type')
    bed = l.get('bedroom')
    if ptype == 'plot' and bed and bed > 0:
        print(f"  PLOT WITH BEDROOMS: {lid} - type={ptype}, bed={bed}")

# Plot checks for furnishing
for lid, l in sorted(unique_listings.items()):
    ptype = l.get('property_type')
    furnishing = l.get('furnishing')
    if ptype == 'plot' and furnishing and furnishing != 'unfurnished':
        print(f"  FURNISHED PLOT: {lid} - type={ptype}, furnishing={furnishing}")
        print(f"    desc: {l.get('description','')[:100]}")

# Bathroom anomalies
for lid, l in sorted(unique_listings.items()):
    bed = l.get('bedroom') or 0
    bath = l.get('bathroom') or 0
    if bath > bed + 2:
        print(f"  BATH >> BED: {lid} - bed={bed}, bath={bath}")

print(f"\nFINAL Q4 corrupt: {sorted(set(q4))}")
print(f"FINAL Q9 fake: Need more context. Outlier candidates: {[x[1] for x in fake_candidates[:5]]}")
