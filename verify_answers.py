import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
REFERENCE = datetime(2026, 9, 10, 0, 0, 0, tzinfo=IST)
REF_MINUS_7 = REFERENCE - timedelta(days=7)

with open('all_listings.json') as f:
    listings = json.load(f)
with open('all_rentals.json') as f:
    rentals = json.load(f)
with open('all_projects.json') as f:
    projects = json.load(f)

print("="*50)
print("VERIFYING ALL 10 QUESTIONS")
print("="*50)

# Q1: total_listing_records
# "How many listing records are retrievable from /v1/listings?"
# Retrievable means every record your key can obtain from that endpoint with no filters applied, having paged all the way to the end.
q1 = len(listings)
print(f"Q1: {q1}")

# Q2: unique_properties
# "Among those records, genuine or not, how many distinct properties do they describe? A property described by several records counts once."
# Let's inspect all 50 unique listing_ids and check if any two describe the SAME physical property.
unique_listings = {}
for l in listings:
    if l['listing_id'] not in unique_listings:
        unique_listings[l['listing_id']] = l

# Check physical property fingerprint across all 50 unique listings:
# (apartment_name, locality, floor, bedroom, carpet_area, bathroom, latitude, longitude)
prop_fingerprints = defaultdict(list)
for lid, l in unique_listings.items():
    fp = (
        l.get('apartment_name', '').strip().lower(),
        l.get('locality', '').strip().lower(),
        l.get('bedroom'),
        l.get('floor'),
        l.get('carpet_area'),
        round(l.get('latitude', 0), 4),
        round(l.get('longitude', 0), 4)
    )
    prop_fingerprints[fp].append(lid)

print(f"Unique listing_ids: {len(unique_listings)}")
print(f"Distinct physical property fingerprints: {len(prop_fingerprints)}")
for fp, lids in prop_fingerprints.items():
    if len(lids) > 1:
        print(f"  Duplicate property: {fp} -> {lids}")

q2 = len(prop_fingerprints) # 50 distinct properties
print(f"Q2: {q2}")

# Q3: active_listings
# "How many retrievable listing records have is_live true?"
q3 = sum(1 for l in listings if l.get('is_live') is True)
print(f"Q3: {q3}")

# Q4: corrupt_listing_ids
# "A small number of listing records describe something that cannot exist. List their listing_ids, sorted."
# Let's list all candidate corrupt listings and verify each thoroughly.
corrupt_reasons = {}
for lid, l in unique_listings.items():
    ca = l.get('carpet_area')
    sba = l.get('super_built_up_area')
    bed = l.get('bedroom', 0)
    ptype = l.get('property_type')
    furnishing = l.get('furnishing')
    floor = l.get('floor')
    tot_floors = l.get('total_floors')
    
    # 1. Plots with furnishing / modular kitchen (plots are bare land without buildings/furniture)
    if ptype == 'plot' and furnishing not in [None, 'unfurnished']:
        corrupt_reasons[lid] = f"Plot cannot be '{furnishing}' with interior amenities"
    
    # 2. Impossible carpet area for BHK (e.g. 73 sqft for 2BHK, 110 sqft for 3BHK, 137 sqft for 4BHK, 144 sqft for 4BHK)
    if bed >= 2 and ca < 200 and ptype != 'plot':
        corrupt_reasons[lid] = f"Impossible carpet area {ca} sqft for {bed} BHK {ptype}"
    
    # 3. Floor > total floors
    if floor is not None and tot_floors is not None and floor > tot_floors:
        corrupt_reasons[lid] = f"Floor {floor} > Total floors {tot_floors}"

for lid, r in sorted(corrupt_reasons.items()):
    print(f"  Corrupt: {lid} -> {r}")

q4 = sorted(list(corrupt_reasons.keys()))
print(f"Q4: {q4}")

# Q5: total_monthly_rent in assigned locality: baner
# "Sum of monthly rent across all retrievable rental records in your assigned locality"
baner_rentals = [r for r in rentals if r.get('locality', '').lower() == 'baner']
q5 = sum(r.get('price', 0) for r in baner_rentals)
print(f"Q5: {q5} (across {len(baner_rentals)} Baner rental records)")

# Q7: costliest_project
# "The project with the highest maximum price, as {'project_id': ..., 'price_max_inr': ...}."
# Note: project prices in API are in Lakhs INR (e.g. 97.8 = 97.8 Lakhs = 9,780,000 INR).
# Also note that 36 projects have price_min and price_max inverted/swapped.
unique_projects = {}
for p in projects:
    if p['project_id'] not in unique_projects:
        unique_projects[p['project_id']] = p

proj_max_list = []
for pid, p in unique_projects.items():
    pmin = p.get('price_min') or 0
    pmax = p.get('price_max') or 0
    effective_max_lakhs = max(pmin, pmax)
    effective_max_inr = int(effective_max_lakhs * 100000)
    proj_max_list.append((effective_max_inr, effective_max_lakhs, pid, p.get('apartment_name')))

proj_max_list.sort(reverse=True)
print("Top 5 costliest projects:")
for inr, lakhs, pid, name in proj_max_list[:5]:
    print(f"  {pid} ({name}): {lakhs} L = Rs. {inr:,}")

q7 = {"project_id": proj_max_list[0][2], "price_max_inr": proj_max_list[0][0]}
print(f"Q7: {q7}")

# Q8: listings_last_7_days
# "How many retrievable listing records were posted in the seven days before REFERENCE, i.e. in [REFERENCE - 7 days, REFERENCE), in IST?"
# Reference = 2026-09-10T00:00:00+05:30
# Window = [2026-09-03T00:00:00+05:30, 2026-09-10T00:00:00+05:30)
recent_records_count = 0
recent_lids = set()
for l in listings:
    posted = l.get('posted_at')
    if not posted:
        continue
    # parse ISO 8601 UTC
    dt = datetime.fromisoformat(posted.replace('Z', '+00:00'))
    dt_ist = dt.astimezone(IST)
    if REF_MINUS_7 <= dt_ist < REFERENCE:
        recent_records_count += 1
        recent_lids.add(l['listing_id'])

print(f"Recent unique listing IDs: {recent_lids}")
print(f"Total matching records: {recent_records_count}")
q8 = recent_records_count
print(f"Q8: {q8}")

# Q9: fake_listing_ids
# "Some of these listings are not real. They exist to generate enquiries. List their listing_ids, sorted."
# Let's inspect all descriptions and prices across all 50 unique listings.
print("\nExamining all 50 listing descriptions for fake/lead-gen signals:")
fake_ids = set()
for lid, l in sorted(unique_listings.items()):
    desc = l.get('description', '')
    price = l.get('price', 0)
    ca = l.get('carpet_area', 1)
    ppsqft = price / ca if ca else 0
    # Check for token advance request, lead gen, bait-and-switch phrases
    if 'token' in desc.lower() or 'block the unit' in desc.lower() or 'enquir' in desc.lower():
        print(f"  [TOKEN/BAIT] {lid}: {desc}")
        fake_ids.add(lid)

# Let's also check ZER-3001479 and any other bait listings:
# ZER-3001479: "Pay a token amount of Rs 25,000 today to block the unit." - Kharadi 4BHK for only 61.6 Lakhs (3901/sqft)!
print(f"Identified fake_listing_ids: {sorted(list(fake_ids))}")
q9 = sorted(list(fake_ids))
print(f"Q9: {q9}")

# Q6: avg_price_per_sqft_2bhk
# "Across retrievable listing records where is_live is true and bedroom is 2, leaving out the records in your answers to 4 and 9: the mean of price divided by carpet area, in rupees per square foot, to 2 decimals."
# Note: "Across retrievable listing records..." - whether we compute mean over all retrievable records or unique listing IDs, since every listing is duplicated exactly 73 times, the mean of records equals the mean of unique listings!
q6_records = [
    l for l in listings
    if l.get('is_live') is True
    and l.get('bedroom') == 2
    and l['listing_id'] not in set(q4)
    and l['listing_id'] not in set(q9)
]

print(f"Total records for Q6 calculation: {len(q6_records)}")
q6_ratios = [l['price'] / l['carpet_area'] for l in q6_records]
q6 = round(statistics.mean(q6_ratios), 2)
print(f"Q6: {q6}")

# Q10: projects_with_wrong_listing_count
# "Every project reports how many listings it has. For how many projects is that number wrong?"
# Check across all 50 unique projects
# Let's check: total_listings in project object vs actual number of listings linked to project_id in /v1/listings
proj_listing_map_unique = defaultdict(set)
proj_listing_map_records = defaultdict(int)
for l in listings:
    pid = l.get('project_id')
    if pid:
        proj_listing_map_unique[pid].add(l['listing_id'])
        proj_listing_map_records[pid] += 1

wrong_projects_unique = 0
wrong_projects_records = 0

for pid, p in unique_projects.items():
    doc_count = p.get('total_listings', 0)
    actual_unique = len(proj_listing_map_unique.get(pid, set()))
    actual_records = proj_listing_map_records.get(pid, 0)
    if doc_count != actual_unique:
        wrong_projects_unique += 1
    if doc_count != actual_records:
        wrong_projects_records += 1

print(f"Unique projects count: {len(unique_projects)}")
print(f"Projects with wrong count compared to unique listings: {wrong_projects_unique}")
print(f"Projects with wrong count compared to listing records: {wrong_projects_records}")
# Note that if compared across all 450 project records vs 50 unique:
# Let's check how many project records in /v1/projects have wrong total_listings:
wrong_proj_records_total = 0
for p in projects:
    pid = p['project_id']
    doc_count = p.get('total_listings', 0)
    actual_unique = len(proj_listing_map_unique.get(pid, set()))
    if doc_count != actual_unique:
        wrong_proj_records_total += 1

print(f"Across 50 distinct projects: {wrong_projects_unique} have wrong total_listings (out of 50).")
q10 = wrong_projects_unique
print(f"Q10: {q10}")

print("="*50)
print("FINAL SUMMARY OF ANSWERS")
print("="*50)
final_answers = {
    "total_listing_records": q1,
    "unique_properties": q2,
    "active_listings": q3,
    "corrupt_listing_ids": q4,
    "total_monthly_rent": q5,
    "avg_price_per_sqft_2bhk": q6,
    "costliest_project": q7,
    "listings_last_7_days": q8,
    "fake_listing_ids": q9,
    "projects_with_wrong_listing_count": q10
}
print(json.dumps(final_answers, indent=2))
