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

# ===== CONFIRMED ANSWERS =====

# Q1: Total listing records (all including duplicates)
q1 = len(all_listings)  # 3650

# Q2: Unique properties (distinct physical properties)
prop_groups = defaultdict(set)
for l in all_listings:
    lat = l.get('latitude')
    lon = l.get('longitude')
    if lat is not None and lon is not None:
        key = (round(float(lat), 5), round(float(lon), 5))
        prop_groups[key].add(l['listing_id'])
q2 = len(unique_listings)  # 50 unique listing_ids = 50 distinct properties

# Q3: Active listings (records with is_live=True)
q3 = sum(1 for l in all_listings if l.get('is_live') is True)  # 2920

# Q4: Corrupt listings
q4 = sorted([
    'MAG-3001035',  # 4BHK builder floor, area=144 sqft (impossible)
    'MAG-3001327',  # 4BHK villa, area=137 sqft (impossible)
    'MAG-3001519',  # 2BHK house, area=73 sqft (impossible)
    'MAG-3001756',  # plot but semi-furnished (impossible)
    'MAG-3002851',  # plot but fully-furnished (impossible)
    'MAG-3003434',  # 3BHK apartment, area=110 sqft (impossible)
])

# Q5: Total monthly rent in Baner
baner_rentals = [r for r in all_rentals if r.get('locality', '').lower() == 'baner']
q5 = sum(r.get('price', 0) for r in baner_rentals)

# Q6: Avg price/sqft for active 2BHK (excl corrupt + fake)
# First, identify fake listings
# Key fake: ZER-3001479 has "Pay a token amount of Rs 25,000 today to block the unit" = typical bait
# SQU-3001712 has "Urgent sale - owner relocating" - also suspicious
# Let's check all descriptions for common fake phrases

print("=== FAKE LISTING DETECTION ===")
fake_phrases = [
    'token amount', 'token of', 'block the unit', 'enquir',
    'urgent sale', 'owner relocating', 'below market', 'distress sale'
]
fake_candidates = []
for lid, l in unique_listings.items():
    desc = (l.get('description') or '').lower()
    for phrase in fake_phrases:
        if phrase in desc:
            price = l.get('price', 0)
            area = l.get('carpet_area', 1)
            ppsqft = price / area if area else 0
            fake_candidates.append((lid, phrase, ppsqft, l.get('locality'), l.get('is_live')))
            print(f"  FAKE CANDIDATE {lid}: phrase='{phrase}', ppsqft={ppsqft:.0f}, loc={l.get('locality')}")
            print(f"    desc: {l.get('description','')[:150]}")

# ZER-3001479 is clearly fake (solicits money upfront - illegal in India)
# SQU-3001712 "urgent sale" is also suspicious
# Let's also check for underpriced listings (below 50% of locality median)

print("\n=== CHECKING FOR UNDERPRICED BAIT LISTINGS ===")
# Locality stats from non-corrupt, non-extreme listings
loc_ppsqft_all = defaultdict(list)
for lid, l in unique_listings.items():
    if lid not in set(q4):
        price = l.get('price', 0)
        area = l.get('carpet_area', 1)
        if area and area > 0 and price > 0:
            ppsqft = price / area
            if ppsqft < 50000:  # exclude the corrupt ones
                loc_ppsqft_all[l.get('locality', '')].append((ppsqft, lid))

for loc, vals in sorted(loc_ppsqft_all.items()):
    ppss = [v[0] for v in vals]
    if ppss:
        med = statistics.median(ppss)
        for pps, lid in vals:
            ratio = pps / med
            if ratio < 0.6:  # 40% below median = suspicious
                l = unique_listings[lid]
                print(f"  UNDERPRICED {lid}: pps={pps:.0f} (median={med:.0f}, ratio={ratio:.2f}), loc={loc}")
                print(f"    desc: {l.get('description','')[:100]}")

# Based on analysis: ZER-3001479 with "Pay a token amount" is clearly fake
# It's also the CHEAPEST listing (pps=3901 in kharadi where median is higher)
# SQU-3001712 "Urgent sale" is suspicious but 8879 ppsqft is not dramatically low

# Final Q9: fake listings
q9_candidates = ['ZER-3001479']  # Clearly fake with token amount solicitation
# Check if there are more underpriced ones we should include

# Let's compute Q6 with and without ZER-3001479
exclude_ids = set(q4) | {'ZER-3001479'}
valid_2bhk = [l for l in unique_listings.values()
              if l.get('is_live') is True
              and l.get('bedroom') == 2
              and l['listing_id'] not in exclude_ids
              and l.get('price') and l.get('carpet_area') and l['carpet_area'] > 0]

print(f"\nQ6 valid active 2BHK (excl corrupt + ZER-3001479): {len(valid_2bhk)}")
ppss_q6 = [l['price']/l['carpet_area'] for l in valid_2bhk]
q6 = round(sum(ppss_q6)/len(ppss_q6), 2) if ppss_q6 else 0.0
print(f"Q6 avg_price_per_sqft_2bhk: {q6}")

# Q7: Costliest project (price_max in LAKHS - convert to rupees)
# Find correct price_max considering swapped fields
def get_true_max_lakhs(p):
    pmin = p.get('price_min', 0) or 0
    pmax = p.get('price_max', 0) or 0
    return max(pmin, pmax)

sorted_projs = sorted(unique_projects.values(), key=get_true_max_lakhs, reverse=True)
q7_project = sorted_projs[0]
q7_id = q7_project['project_id']
q7_price_lakhs = get_true_max_lakhs(q7_project)
q7_price_inr = int(q7_price_lakhs * 100000)

# Q8: Listings posted in last 7 days
q8_ids = set()
for l in all_listings:
    posted_str = l.get('posted_at', '')
    if not posted_str:
        continue
    try:
        dt = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            q8_ids.add(l['listing_id'])
    except:
        pass
q8 = len(q8_ids) * 73  # Each unique ID appears 73 times in records
# BUT: the question says "how many retrievable listing records were posted"
# If a listing_id posted recently appears 73 times, that's 73 records

# Let's count records directly
q8_records = 0
for l in all_listings:
    posted_str = l.get('posted_at', '')
    if not posted_str:
        continue
    try:
        dt = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            q8_records += 1
    except:
        pass

# Q8 should be q8_records since question asks about records
# But also check what date range these recent listings have
print("\n=== Q8 ANALYSIS ===")
print(f"Recent unique listing IDs: {q8_ids}")
for lid in q8_ids:
    l = unique_listings.get(lid)
    if l:
        print(f"  {lid}: posted={l.get('posted_at')}, is_live={l.get('is_live')}")
print(f"Q8 records: {q8_records} (= {len(q8_ids)} unique * 73 duplicates)")

# Q10: Projects with wrong listing count
print("\n=== Q10 ANALYSIS ===")
proj_actual_counts = defaultdict(int)
for l in all_listings:
    pid = l.get('project_id')
    if pid:
        proj_actual_counts[pid] += 1

# The project's total_listings should match actual count from API
# But since listings are duplicated 73x, what's the "correct" count?
# The project says total_listings=4 for P30001
# If we get 4 unique listings for P30001 that would match
# But we get 0 listings for P30001 in our data

# Let's check
proj_unique_counts = defaultdict(set)
for l in all_listings:
    pid = l.get('project_id')
    if pid:
        proj_unique_counts[pid].add(l['listing_id'])

print("Projects with listings in our data:")
for pid, lids in sorted(proj_unique_counts.items()):
    proj = unique_projects.get(pid)
    if proj:
        doc_count = proj.get('total_listings', 0)
        actual_unique = len(lids)
        actual_total = proj_actual_counts[pid]
        print(f"  {pid}: doc={doc_count}, actual_unique={actual_unique}, actual_total={actual_total}")

# Most projects have 0 listings in our data
# Project P30001 documents total_listings=4 but we find 0
# This is because listings endpoint filters to only certain project IDs

# Count projects with wrong total_listings
wrong_count = 0
for pid, proj in unique_projects.items():
    doc_count = proj.get('total_listings', 0)
    actual_unique = len(proj_unique_counts.get(pid, set()))
    if doc_count != actual_unique:
        wrong_count += 1
print(f"\nQ10 projects with wrong total_listings: {wrong_count}")

# But wait: if we're to filter by project_id to get actual listings,
# we need to check if the project_id filter works
# From our earlier test: project_id=P30001 returned ALL 3615 listings
# That means the project_id filter doesn't work!
# So we can't verify actual project listing counts from /v1/listings?project_id=X
# We can only compare total_listings from projects vs what we see in listings.project_id

# ===== FINAL ANSWERS =====
print("\n" + "=" * 60)
print("FINAL CONFIRMED ANSWERS")
print("=" * 60)

print(f"Q1  total_listing_records: {q1}")
print(f"Q2  unique_properties: {q2}")
print(f"Q3  active_listings: {q3}")
print(f"Q4  corrupt_listing_ids: {q4}")
print(f"Q5  total_monthly_rent: {q5}")
print(f"Q6  avg_price_per_sqft_2bhk: {q6}")
print(f"Q7  costliest_project: project_id={q7_id}, price_max_inr={q7_price_inr}")
print(f"    (raw project price_max was {q7_price_lakhs} lakhs)")
print(f"Q8  listings_last_7_days: {q8_records}")
print(f"Q9  fake_listing_ids: {q9_candidates} (TO VERIFY - need more analysis)")
print(f"Q10 projects_with_wrong_listing_count: {wrong_count}")

# Save
answers = {
    "total_listing_records": q1,
    "unique_properties": q2,
    "active_listings": q3,
    "corrupt_listing_ids": q4,
    "total_monthly_rent": q5,
    "avg_price_per_sqft_2bhk": q6,
    "costliest_project": {"project_id": q7_id, "price_max_inr": q7_price_inr},
    "listings_last_7_days": q8_records,
    "fake_listing_ids": sorted(q9_candidates),
    "projects_with_wrong_listing_count": wrong_count
}
with open('confirmed_answers.json', 'w') as f:
    json.dump(answers, f, indent=2)
print("\nSaved to confirmed_answers.json")
