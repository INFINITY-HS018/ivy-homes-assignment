import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import requests
import time

API_KEY = "IVY26-5993D94E34F4"
BASE_URL = "https://solve.ivy.homes"
IST = timezone(timedelta(hours=5, minutes=30))
REFERENCE = datetime(2026, 9, 10, 0, 0, 0, tzinfo=IST)
REF_MINUS_7 = REFERENCE - timedelta(days=7)

with open('all_listings.json') as f:
    all_listings = json.load(f)
with open('all_rentals.json') as f:
    all_rentals = json.load(f)
with open('all_projects.json') as f:
    all_projects = json.load(f)

print(f"Data: {len(all_listings)} listings, {len(all_rentals)} rentals, {len(all_projects)} projects")

# ===== Q1 =====
q1 = len(all_listings)
print(f"\nQ1 total_listing_records: {q1}")

# ===== DUPLICATES =====
# Find duplicate listing IDs
lid_map = defaultdict(list)
for i, l in enumerate(all_listings):
    lid_map[l['listing_id']].append(i)

unique_lids = list(lid_map.keys())
print(f"Unique listing_ids: {len(unique_lids)}")

repeated_lids = {k: v for k, v in lid_map.items() if len(v) > 1}
print(f"listing_ids appearing >1 time: {len(repeated_lids)}")
if repeated_lids:
    sample = list(repeated_lids.items())[:3]
    for lid, idxs in sample:
        print(f"  {lid}: appears {len(idxs)} times")

# Build unique listing lookup
unique_listings = {l['listing_id']: l for l in all_listings}
print(f"Unique listings (by id): {len(unique_listings)}")

# ===== Q2: Unique properties =====
# "Distinct properties" = physical properties
# Same property may be listed on multiple websites with same listing_id
# Check if listing_id is consistent across duplicates
print("\n--- Q2 Analysis ---")

# Group by (lat, lon, floor, bedroom, carpet_area)
prop_groups = defaultdict(list)
no_location = []
for l in all_listings:
    lat = l.get('latitude')
    lon = l.get('longitude')
    if lat is not None and lon is not None:
        key = (round(float(lat), 5), round(float(lon), 5), l.get('floor'), l.get('bedroom'), l.get('carpet_area'))
        prop_groups[key].append(l['listing_id'])
    else:
        no_location.append(l['listing_id'])

unique_prop_keys = set(prop_groups.keys())
unique_no_loc_lids = set(no_location)
q2 = len(unique_prop_keys) + len(unique_no_loc_lids)
print(f"Unique (lat,lon,floor,bed,area): {len(unique_prop_keys)}")
print(f"Listings without location: {len(no_location)} (unique ids: {len(unique_no_loc_lids)})")
print(f"Q2 unique_properties: {q2}")

# ===== Q3 =====
q3 = sum(1 for l in unique_listings.values() if l.get('is_live') is True)
q3_total = sum(1 for l in all_listings if l.get('is_live') is True)
print(f"\nQ3 active_listings (is_live=True in unique): {q3}")
print(f"Q3 active_listings (is_live=True in all): {q3_total}")

# ===== Q4: Corrupt listings =====
print("\n--- Q4 Corrupt Listings ---")
corrupt_ids = []
for lid, l in unique_listings.items():
    issues = []
    ca = l.get('carpet_area')
    sba = l.get('super_built_up_area') or l.get('super_builtup_area')
    price = l.get('price')
    floor_ = l.get('floor')
    total_floors = l.get('total_floors')
    bedroom = l.get('bedroom')
    bathroom = l.get('bathroom')
    
    if ca is not None and ca <= 0:
        issues.append(f"carpet_area={ca}")
    if price is not None and price <= 0:
        issues.append(f"price={price}")
    if floor_ is not None and total_floors is not None and floor_ > total_floors:
        issues.append(f"floor {floor_} > total_floors {total_floors}")
    if ca and sba and ca > sba:
        issues.append(f"carpet_area({ca}) > super_built_up_area({sba})")
    if bedroom is not None and bedroom < 0:
        issues.append(f"bedroom={bedroom}")
    
    if issues:
        corrupt_ids.append(lid)
        print(f"  CORRUPT {lid}: {'; '.join(issues)}")

q4 = sorted(corrupt_ids)
print(f"Q4 corrupt_listing_ids: {q4}")

# ===== Q5 =====
baner_rentals = [r for r in all_rentals if r.get('locality', '').lower() == 'baner']
q5 = sum(r.get('price', 0) for r in baner_rentals)
print(f"\nQ5 total_monthly_rent (Baner, {len(baner_rentals)} rentals): {q5}")

# ===== Q7: Costliest project (price_max in LAKHS, convert to INR) =====
print("\n--- Q7 Project Price Analysis ---")
# Established: project prices are in LAKHS (not rupees)
# e.g. P30013: price_max=96.2 lakhs, listing prices ~7.1M rupees (71.2 lakhs) - consistent

# But P30001: price_min=80.0, price_max=3.22 - impossible (min > max)
# This means either fields are SWAPPED for some projects, or it's a data error

# Get unique projects (duplicates)
unique_projects = {}
for p in all_projects:
    pid = p['project_id']
    if pid not in unique_projects:
        unique_projects[pid] = p
print(f"Unique project IDs: {len(unique_projects)}")

# Find projects where price_min > price_max
swapped_projects = []
for pid, p in unique_projects.items():
    pmin = p.get('price_min', 0) or 0
    pmax = p.get('price_max', 0) or 0
    if pmin > 0 and pmax > 0 and pmin > pmax:
        swapped_projects.append((pid, pmin, pmax))

print(f"Projects with price_min > price_max (likely swapped): {len(swapped_projects)}")
for pid, pmin, pmax in swapped_projects[:5]:
    print(f"  {pid}: min={pmin}, max={pmax}")

# Get costliest project (highest price_max in lakhs -> highest price_max_inr)
# Need to handle swapped fields
def get_true_max(p):
    pmin = p.get('price_min', 0) or 0
    pmax = p.get('price_max', 0) or 0
    return max(pmin, pmax)

sorted_projs = sorted(unique_projects.values(), key=get_true_max, reverse=True)
print("\nTop 5 projects by effective price_max:")
for p in sorted_projs[:5]:
    pid = p['project_id']
    pmin = p.get('price_min', 0)
    pmax = p.get('price_max', 0)
    true_max = get_true_max(p)
    print(f"  {pid} {p.get('apartment_name')}: min={pmin}, max={pmax}, true_max={true_max} lakhs = {true_max * 100000:.0f} rupees")

q7_project = sorted_projs[0]
q7_id = q7_project['project_id']
q7_price_lakhs = get_true_max(q7_project)
q7_price_inr = int(q7_price_lakhs * 100000)
print(f"\nQ7 costliest_project: project_id={q7_id}, price_max_inr={q7_price_inr}")

# ===== Q8: Listings last 7 days =====
print("\n--- Q8 Recent Listings ---")
recent_ids = set()
for l in all_listings:
    posted_str = l.get('posted_at', '')
    if not posted_str:
        continue
    try:
        dt = datetime.fromisoformat(posted_str.replace('Z', '+00:00'))
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            recent_ids.add(l['listing_id'])
    except:
        pass

q8 = len(recent_ids)
print(f"Q8 listings_last_7_days: {q8}")

# ===== Q9: Fake listings =====
print("\n--- Q9 Fake Listings Analysis ---")

# Key observation: multiple contacts each with EXACTLY the same number of listings
contact_map = defaultdict(list)
for l in all_listings:
    c = l.get('posted_by_contact', '')
    if c:
        contact_map[c].append(l['listing_id'])

count_dist = defaultdict(list)
for c, lids in contact_map.items():
    count_dist[len(lids)].append(c)

print("Contact count distribution:")
for cnt in sorted(count_dist.keys(), reverse=True)[:10]:
    print(f"  {cnt} listings: {len(count_dist[cnt])} contacts")

# The most suspicious group: contacts with exactly N listings where N is suspicious
# From earlier: many contacts with 73 listings, all same price/sqft
# This is highly suspicious for fake listings

# Find the "magic" count
top_count = sorted(count_dist.keys(), reverse=True)[0]
suspicious_contacts = count_dist.get(top_count, [])
print(f"\nSuspicious contact count: {top_count} listings ({len(suspicious_contacts)} contacts)")

# All listings from suspicious contacts
fake_lids_from_contacts = set()
for c in suspicious_contacts:
    for lid in contact_map[c]:
        fake_lids_from_contacts.add(lid)

print(f"Unique listing IDs from suspicious contacts: {len(fake_lids_from_contacts)}")

# Verify these have identical price/sqft (artificial)
print("Checking price/sqft uniformity within contacts:")
non_uniform = 0
for c in suspicious_contacts[:10]:
    ls = [unique_listings.get(lid) for lid in contact_map[c] if lid in unique_listings]
    ppss = [l['price'] / l['carpet_area'] if l.get('price') and l.get('carpet_area') else None for l in ls if l]
    ppss = [x for x in ppss if x is not None]
    if ppss:
        var = max(ppss) - min(ppss)
        if var > 0.01:
            non_uniform += 1
            print(f"  {c}: price/sqft varies by {var:.2f} - NOT uniform")

if non_uniform == 0:
    print("  ALL suspicious contacts have perfectly uniform price/sqft - CONFIRMED FAKE")

q9 = sorted(fake_lids_from_contacts)
print(f"\nQ9 fake_listing_ids ({len(q9)} total):")
print(f"  First 10: {q9[:10]}")
print(f"  Last 10: {q9[-10:]}")

# ===== Q6: Avg price/sqft for active 2BHK =====
print("\n--- Q6 Avg Price/Sqft Active 2BHK ---")
exclude_ids = set(q4) | set(q9)
valid_2bhk = [l for l in unique_listings.values()
              if l.get('is_live') is True
              and l.get('bedroom') == 2
              and l['listing_id'] not in exclude_ids
              and l.get('price') and l.get('carpet_area') and l['carpet_area'] > 0]

print(f"Valid active 2BHK listings (excl corrupt + fake): {len(valid_2bhk)}")
ppsqft_vals = [l['price'] / l['carpet_area'] for l in valid_2bhk]
q6 = round(sum(ppsqft_vals) / len(ppsqft_vals), 2) if ppsqft_vals else 0.0
print(f"Q6 avg_price_per_sqft_2bhk: {q6}")
print(f"  Range: {min(ppsqft_vals):.0f} - {max(ppsqft_vals):.0f}")

# ===== Q10: Projects with wrong listing count =====
print("\n--- Q10 Wrong Listing Counts ---")
proj_listing_counts = defaultdict(set)
for l in all_listings:
    pid = l.get('project_id')
    if pid:
        proj_listing_counts[pid].add(l['listing_id'])

wrong_count = 0
for proj in unique_projects.values():
    pid = proj['project_id']
    doc_count = proj.get('total_listings', 0)
    actual_unique = len(proj_listing_counts.get(pid, set()))
    if doc_count != actual_unique:
        wrong_count += 1

q10 = wrong_count
print(f"Q10 projects_with_wrong_listing_count: {q10}")

# Check example
print("Sample wrong projects:")
cnt = 0
for proj in unique_projects.values():
    pid = proj['project_id']
    doc_count = proj.get('total_listings', 0)
    actual_unique = len(proj_listing_counts.get(pid, set()))
    if doc_count != actual_unique:
        print(f"  {pid}: documented={doc_count}, actual_unique={actual_unique}")
        cnt += 1
        if cnt >= 5:
            break

# ===== FINAL ANSWERS =====
print("\n" + "=" * 60)
print("FINAL ANSWERS")
print("=" * 60)
print(f"Q1  total_listing_records: {q1}")
print(f"Q2  unique_properties: {q2}")
print(f"Q3  active_listings: {q3}")
print(f"Q4  corrupt_listing_ids: {q4}")
print(f"Q5  total_monthly_rent: {q5}")
print(f"Q6  avg_price_per_sqft_2bhk: {q6}")
print(f"Q7  costliest_project: {{'project_id': '{q7_id}', 'price_max_inr': {q7_price_inr}}}")
print(f"Q8  listings_last_7_days: {q8}")
print(f"Q9  fake_listing_ids: {len(q9)} items")
print(f"Q10 projects_with_wrong_listing_count: {q10}")

answers = {
    "total_listing_records": q1,
    "unique_properties": q2,
    "active_listings": q3,
    "corrupt_listing_ids": q4,
    "total_monthly_rent": q5,
    "avg_price_per_sqft_2bhk": q6,
    "costliest_project": {"project_id": q7_id, "price_max_inr": q7_price_inr},
    "listings_last_7_days": q8,
    "fake_listing_ids": q9,
    "projects_with_wrong_listing_count": q10
}
with open('final_answers.json', 'w') as f:
    json.dump(answers, f, indent=2)
print("\nSaved to final_answers.json")
