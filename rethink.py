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

# Unique listing lookup
unique_listings = {l['listing_id']: l for l in all_listings}
unique_projects = {p['project_id']: p for p in all_projects}

print("=== RETHINKING THE DATA MODEL ===")
print(f"Total records: {len(all_listings)}")
print(f"Unique listing_ids: {len(unique_listings)}")
print(f"= {len(all_listings) / len(unique_listings):.0f}x duplication factor")
print(f"Total projects: {len(all_projects)}")
print(f"Unique project_ids: {len(unique_projects)}")

# Is the duplication the "duplicate" finding? Or is each listing genuinely unique?
# Let's look at whether the same listing_id has different data each time it appears
print("\n=== CHECKING IF DUPLICATES HAVE DIFFERENT DATA ===")
for lid, l in list(unique_listings.items())[:3]:
    occurrences = [x for x in all_listings if x['listing_id'] == lid]
    print(f"\n{lid} appears {len(occurrences)} times:")
    for occ in occurrences[:3]:
        print(f"  website={occ.get('website')}, price={occ.get('price')}, is_live={occ.get('is_live')}")
    # Are they all identical?
    all_same = all(occ == occurrences[0] for occ in occurrences)
    print(f"  All identical: {all_same}")

# What are the websites?
websites = set(l.get('website') for l in all_listings)
print(f"\nWebsites in listings: {websites}")
website_counts = defaultdict(set)
for l in all_listings:
    website_counts[l.get('website')].add(l['listing_id'])
for ws, ids in sorted(website_counts.items(), key=lambda x: -len(x[1])):
    print(f"  {ws}: {len(ids)} unique listing_ids")

# The description says "each listing corresponds to exactly one physical property"
# But if same listing_id appears 73 times... that's the duplication finding!
# Q2 "distinct properties" = 50

# For Q1: total_listing_records = 3650 (all, including duplicates)
# But wait - do these duplicates have the SAME is_live value?
print("\n=== IS_LIVE CONSISTENCY IN DUPLICATES ===")
for lid in list(unique_listings.keys())[:5]:
    occurrences = [l for l in all_listings if l['listing_id'] == lid]
    live_vals = set(l.get('is_live') for l in occurrences)
    print(f"  {lid}: is_live values = {live_vals}, count = {len(occurrences)}")

# Q3: How many records have is_live=True (all records, not just unique)
q3_all_records = sum(1 for l in all_listings if l.get('is_live') is True)
q3_unique = sum(1 for l in unique_listings.values() if l.get('is_live') is True)
print(f"\nQ3 is_live=True in ALL records: {q3_all_records}")
print(f"Q3 is_live=True in UNIQUE records: {q3_unique}")

# From Q3's perspective: question asks about "retrievable listing records" 
# with is_live=True - so it's about records, not unique properties
# If 2920/3650 are is_live=True, then Q3=2920

# Q8: similarly - listings posted in last 7 days (records, not unique)
recent_all = set()
recent_unique = set()
for l in all_listings:
    posted_str = l.get('posted_at', '')
    if not posted_str:
        continue
    try:
        dt = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            recent_all.add(l['listing_id'])  # count unique IDs posted recently
    except:
        pass

# But the question says "how many retrievable listing records were posted" - could mean count of records
recent_records = 0
for l in all_listings:
    posted_str = l.get('posted_at', '')
    if not posted_str:
        continue
    try:
        dt = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            recent_records += 1
    except:
        pass

print(f"\nQ8 recent listing records (count, all): {recent_records}")
print(f"Q8 recent unique listing_ids: {len(recent_all)}")

# What's one of the recent listings?
for l in all_listings[:100]:
    posted_str = l.get('posted_at', '')
    try:
        dt = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            print(f"  Recent: {l['listing_id']}, posted={posted_str}, ist={dt_ist.isoformat()}")
            break
    except:
        pass

# ===== Q9 REVISITED: What makes a listing FAKE? =====
print("\n=== Q9 FAKE LISTING ANALYSIS (REVISITED) ===")
# The problem says "generate enquiries" - real estate bait listings
# They exist to attract buyers then substitute with other properties
# Key signature: 
# - Suspiciously low price for the area
# - Contact is same for many similar listings  
# - Description is templated/generic
# - Multiple portals have same listing with same contact

# All contacts have exactly 73 listings. This is because each unique listing
# is duplicated 73 times - the contact doesn't change.
# So the fake signal must be something about the UNIQUE listings themselves.

# What makes a unique listing fake?
# 1. Price that doesn't match area/locality
# 2. Description that generates enquiries (hints)
# 3. Properties that don't really exist

# Let's examine each unique listing more carefully
print("\nAll 50 unique listings:")
for lid, l in sorted(unique_listings.items()):
    price = l.get('price', 0)
    area = l.get('carpet_area', 1)
    ppsqft = price / area if area else 0
    is_live = l.get('is_live')
    locality = l.get('locality', '')
    bedroom = l.get('bedroom')
    print(f"  {lid}: is_live={is_live}, loc={locality}, bed={bedroom}, price={price}, area={area}, p/sqft={ppsqft:.0f}")

# Analyze price/sqft by locality for unique listings
loc_ppsqft = defaultdict(list)
for lid, l in unique_listings.items():
    price = l.get('price', 0)
    area = l.get('carpet_area', 1)
    ppsqft = price / area if area else 0
    locality = l.get('locality', '')
    loc_ppsqft[locality].append((ppsqft, lid))

print("\nLocality price/sqft:")
for loc in sorted(loc_ppsqft.keys()):
    vals = loc_ppsqft[loc]
    ppss = [v[0] for v in vals]
    print(f"  {loc}: n={len(ppss)}, avg={sum(ppss)/len(ppss):.0f}, range={min(ppss):.0f}-{max(ppss):.0f}")

# Maybe Q9 is about something else: listings that use generated/bait content?
# Or maybe the fake ones are specifically the ones where same property appears
# at impossibly good price compared to market?

# Let me compute per-locality averages from ALL valid listings
# and find which of our 50 are outliers
# Actually with only 50 unique listings, we have ~5 per locality
# Hard to detect within-locality outliers

# Alternative: look at the descriptions for patterns
print("\nDescriptions of all 50 unique listings:")
for lid, l in sorted(unique_listings.items()):
    desc = l.get('description', '')
    print(f"  {lid}: '{desc[:80]}'")

# Check for price outliers - some contacts post at exactly same p/sqft
contact_ppsqft = {}
for l in unique_listings.values():
    contact = l.get('posted_by_contact', '')
    price = l.get('price', 0)
    area = l.get('carpet_area', 1)
    ppsqft = price / area if area else 0
    contact_ppsqft[contact] = ppsqft

ppsqft_vals = list(contact_ppsqft.values())
print(f"\nAll unique p/sqft values: {sorted(ppsqft_vals)}")
print(f"Mean: {sum(ppsqft_vals)/len(ppsqft_vals):.0f}")
print(f"Stdev: {statistics.stdev(ppsqft_vals):.0f}")

# ===== Q4 REVISITED =====
print("\n=== Q4 CORRUPT LISTINGS (REVISITED) ===")
# Let's look at ALL fields for all 50 unique listings
for lid, l in sorted(unique_listings.items()):
    ca = l.get('carpet_area')
    sba = l.get('super_built_up_area') or l.get('super_builtup_area')
    price = l.get('price')
    floor_ = l.get('floor')
    total_f = l.get('total_floors')
    bed = l.get('bedroom')
    bath = l.get('bathroom')
    
    issues = []
    if ca and sba and ca > sba:
        issues.append(f"carpet({ca})>sba({sba})")
    if ca is not None and ca <= 0:
        issues.append(f"ca={ca}")
    if price is not None and price <= 0:
        issues.append(f"price={price}")
    if floor_ is not None and total_f is not None and floor_ > total_f:
        issues.append(f"floor({floor_})>total({total_f})")
    if bed is not None and bed < 0:
        issues.append(f"bed={bed}")
    
    if issues:
        print(f"  CORRUPT {lid}: {', '.join(issues)}")
        print(f"    Full: {json.dumps({k:v for k,v in l.items() if k not in ['description', 'listing_url']})}")

# Check for other impossible values
print("\nChecking ALL numeric fields:")
for lid, l in sorted(unique_listings.items()):
    bed = l.get('bedroom')
    bath = l.get('bathroom')
    balcony = l.get('balcony')
    floor_ = l.get('floor')
    total_f = l.get('total_floors')
    ca = l.get('carpet_area')
    sba = l.get('super_built_up_area') or l.get('super_builtup_area')
    cov_pk = l.get('covered_parking')
    
    if any(v is not None and v < 0 for v in [bed, bath, balcony, floor_, ca, sba, cov_pk]):
        print(f"  NEGATIVE VALUE in {lid}: bed={bed}, bath={bath}, bal={balcony}, floor={floor_}, ca={ca}, sba={sba}")
    
    # Bedroom=0 for apartment type?
    ptype = l.get('property_type', '')
    if bed == 0 and ptype in ['apartment', 'villa', 'builder floor']:
        print(f"  STUDIO/0BHK apartment? {lid}: bed={bed}, type={ptype}")

# ===== Q6 FIX =====
print("\n=== Q6 COMPUTATION ===")
# Q9 fake IDs
contact_map = defaultdict(list)
for l in all_listings:
    c = l.get('posted_by_contact', '')
    if c:
        contact_map[c].append(l['listing_id'])

# Find the suspicious contacts (all 50 have 73 listings)
# But if all unique listings come from suspicious contacts, Q9 might be 0
# OR we need to determine which are fake from content

# Let's see: Q6 needs active 2BHK excluding corrupt (Q4) and fake (Q9)
# If Q9 = 0, then:
active_2bhk_unique = [l for l in unique_listings.values() 
                      if l.get('is_live') is True and l.get('bedroom') == 2]
print(f"Active 2BHK unique: {len(active_2bhk_unique)}")
for l in active_2bhk_unique[:5]:
    print(f"  {l['listing_id']}: price={l.get('price')}, area={l.get('carpet_area')}")

if active_2bhk_unique:
    ppss = [l['price']/l['carpet_area'] for l in active_2bhk_unique if l.get('price') and l.get('carpet_area')]
    if ppss:
        q6 = round(sum(ppss)/len(ppss), 2)
        print(f"Q6 (if Q9=0): {q6}")
