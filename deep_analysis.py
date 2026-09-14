#!/usr/bin/env python3
"""
Ivy Homes - Deep Analysis
Based on: 3650 total listings, prices appear to be in lakhs/crores
"""

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

# Load cached data
with open("all_listings.json") as f:
    all_listings = json.load(f)
with open("all_rentals.json") as f:
    all_rentals = json.load(f)
with open("all_projects.json") as f:
    all_projects = json.load(f)

print(f"Loaded: {len(all_listings)} listings, {len(all_rentals)} rentals, {len(all_projects)} projects")

# ===== PRICE UNIT INVESTIGATION =====
print("\n" + "=" * 60)
print("PRICE UNIT INVESTIGATION")
print("=" * 60)

# Sort output showed NEGATIVE prices! Let's check
prices = [l.get("price") for l in all_listings if l.get("price") is not None]
neg_prices = [p for p in prices if p < 0]
pos_prices = [p for p in prices if p >= 0]
print(f"\nNegative prices: {len(neg_prices)}")
print(f"Positive prices: {len(pos_prices)}")
print(f"Sample prices (first 10): {sorted(prices)[:10]}")
print(f"Sample prices (top 10): {sorted(prices, reverse=True)[:10]}")

# Check if prices are in lakhs (actual Pune prices should be 30L-3Cr for apartments)
# 30L = 3,000,000; 3Cr = 30,000,000
reasonable_prices = [p for p in pos_prices if 1_000_000 <= p <= 200_000_000]
print(f"\nPrices between 10L and 20Cr: {len(reasonable_prices)}")
print(f"Sample reasonable prices: {sorted(reasonable_prices)[:5]}")

# Check project prices
proj_prices = [(p.get("project_id"), p.get("price_min"), p.get("price_max")) for p in all_projects[:5]]
print(f"\nProject prices (first 5):")
for pid, pmin, pmax in proj_prices:
    print(f"  {pid}: min={pmin}, max={pmax}")
    # If these are in crores, 97.8 crore = 97,80,00,000
    if pmax and pmax < 1000:
        print(f"    → Likely in crores: max = {pmax * 1e7:.0f} rupees")

# Figure out price unit for projects
all_proj_maxes = [p.get("price_max", 0) for p in all_projects if p.get("price_max")]
print(f"\nProject price_max range: {min(all_proj_maxes):.2f} to {max(all_proj_maxes):.2f}")
print(f"Average project price_max: {sum(all_proj_maxes)/len(all_proj_maxes):.2f}")

# ===== DUPLICATE ANALYSIS =====
print("\n" + "=" * 60)
print("DUPLICATE ANALYSIS (Q2)")
print("=" * 60)

# Find truly unique properties
# Group by (lat, lon, floor, bedroom, carpet_area)
prop_groups = defaultdict(list)
no_location = []
for l in all_listings:
    lat = l.get("latitude")
    lon = l.get("longitude")
    if lat is not None and lon is not None:
        key = (round(float(lat), 5), round(float(lon), 5), l.get("floor"), l.get("bedroom"), l.get("carpet_area"))
        prop_groups[key].append(l["listing_id"])
    else:
        no_location.append(l["listing_id"])

print(f"Listings with location: {len(all_listings) - len(no_location)}")
print(f"Listings without location: {len(no_location)}")
print(f"Unique (lat,lon,floor,bed,area) combinations: {len(prop_groups)}")

multi_listing_props = {k: v for k, v in prop_groups.items() if len(v) > 1}
print(f"Properties with multiple listings: {len(multi_listing_props)}")

# How many unique listing_ids are in multi-listing groups?
all_multi_ids = [lid for v in multi_listing_props.values() for lid in v]
print(f"Total listing records for multi-listing properties: {len(all_multi_ids)}")
print(f"Unique listing_ids across all: {len(set(l['listing_id'] for l in all_listings))}")

# Check if same listing_id appears multiple times
lid_counts = defaultdict(int)
for l in all_listings:
    lid_counts[l["listing_id"]] += 1
repeated_lids = {k: v for k, v in lid_counts.items() if v > 1}
print(f"\nRepeated listing_ids: {len(repeated_lids)}")
if repeated_lids:
    print("  First 5:")
    for lid, cnt in list(repeated_lids.items())[:5]:
        print(f"    {lid}: appears {cnt} times")
        sample = next(l for l in all_listings if l["listing_id"] == lid)
        print(f"    website={sample.get('website')}, price={sample.get('price')}")

# Q2: unique properties = unique (lat,lon,floor,bed,area) combos + no_location count
q2 = len(prop_groups) + len(no_location)
print(f"\nQ2 unique_properties estimate: {q2}")
# But repeated_lids means same listing_id appears multiple times
# A listing_id is unique per physical listing per portal
# Q2 asks: how many DISTINCT PROPERTIES (physical)
# Method: deduplicate by (lat,lon,floor,bed,area)
print(f"Q2 better estimate (unique location groups + unloc): {len(prop_groups) + len(set(no_location))}")

# Check sample groups
print("\nSample multi-listing groups (same property, multiple listings):")
for k, v in list(multi_listing_props.items())[:3]:
    print(f"  {k}:")
    for lid in v[:4]:
        l = next(x for x in all_listings if x["listing_id"] == lid)
        print(f"    {lid}: website={l.get('website')}, price={l.get('price')}, is_live={l.get('is_live')}")

# ===== FAKE LISTING DETECTION (Q9) =====
print("\n" + "=" * 60)
print("FAKE LISTING DETECTION (Q9)")
print("=" * 60)

# Key finding: multiple contacts each with exactly 73 listings and SAME price/sqft
contact_map = defaultdict(list)
for l in all_listings:
    c = l.get("posted_by_contact", "")
    if c:
        contact_map[c].append(l)

# Find contacts with exactly the same listing count
contact_counts = defaultdict(list)
for c, ls in contact_map.items():
    contact_counts[len(ls)].append(c)

print("Contact count distribution (top counts):")
for cnt in sorted(contact_counts.keys(), reverse=True)[:10]:
    contacts = contact_counts[cnt]
    print(f"  {cnt} listings: {len(contacts)} contacts")

# Contacts with exactly 73 listings
suspicious_cnt = max(contact_counts.keys())
suspicious_contacts = contact_counts.get(suspicious_cnt, [])
print(f"\nSuspicious contacts ({suspicious_cnt} listings each): {len(suspicious_contacts)}")

# Get all fake listing IDs
fake_candidate_ids = set()
for c in suspicious_contacts:
    for l in contact_map[c]:
        fake_candidate_ids.add(l["listing_id"])

print(f"Total fake candidate listing IDs: {len(fake_candidate_ids)}")

# Verify: do these share same price/sqft?
print("\nFake contact analysis:")
for c in suspicious_contacts[:3]:
    ls = contact_map[c]
    ppss = [(l["price"] / l["carpet_area"] if l.get("carpet_area") else None) for l in ls]
    ppss_clean = [x for x in ppss if x]
    print(f"  {c}: {len(ls)} listings, price/sqft range: {min(ppss_clean):.0f}-{max(ppss_clean):.0f}")
    # All same p/sqft within contact?
    if ppss_clean and max(ppss_clean) - min(ppss_clean) < 1:
        print(f"    → IDENTICAL price/sqft for all listings!")
    print(f"    Sample listing_ids: {[l['listing_id'] for l in ls[:3]]}")

# Are these all active or mixed?
live_fake = [lid for lid in fake_candidate_ids 
             for l in all_listings if l["listing_id"] == lid and l.get("is_live")]
print(f"\nFake candidates that are is_live=True: {len(live_fake)}")

# Are fake listing ids unique?
unique_fake_ids = sorted(set(fake_candidate_ids))
print(f"Unique fake candidate IDs: {len(unique_fake_ids)}")
print(f"Sample: {unique_fake_ids[:10]}")

# ===== CORRUPT LISTINGS (Q4) =====
print("\n" + "=" * 60)
print("CORRUPT LISTINGS (Q4)")
print("=" * 60)

# The duplicate issue means we're seeing same listing multiple times
# Let's analyze unique listings only
unique_listings = {}
for l in all_listings:
    lid = l["listing_id"]
    if lid not in unique_listings:
        unique_listings[lid] = l

print(f"Unique listing_ids: {len(unique_listings)}")

corrupt_ids = []
for lid, l in unique_listings.items():
    issues = []
    
    ca = l.get("carpet_area")
    sba = l.get("super_built_up_area") or l.get("super_builtup_area")
    price = l.get("price")
    floor_ = l.get("floor")
    total_floors = l.get("total_floors")
    bedroom = l.get("bedroom")
    bathroom = l.get("bathroom")
    
    # Carpet > super built-up (physically impossible)
    if ca and sba and ca > sba:
        issues.append(f"carpet_area({ca}) > super_built_up_area({sba})")
    
    # Zero or negative area
    if ca is not None and ca <= 0:
        issues.append(f"carpet_area={ca}")
    
    # Negative price (if prices are supposed to be positive)
    if price is not None and price < 0:
        issues.append(f"price={price} (negative)")
    
    # Floor > total floors
    if floor_ is not None and total_floors is not None and floor_ > total_floors:
        issues.append(f"floor({floor_}) > total_floors({total_floors})")
    
    # Bedroom = 0 for apartment type (impossible)
    if bedroom == 0 and l.get("property_type") in ["apartment", "villa", "builder floor"]:
        issues.append(f"bedroom=0 for {l.get('property_type')}")
    
    if issues:
        corrupt_ids.append(lid)
        print(f"  CORRUPT: {lid}: {', '.join(issues)}")
        # Show full record
        print(f"    {json.dumps({k: l[k] for k in ['price', 'carpet_area', 'super_built_up_area', 'bedroom', 'floor', 'total_floors', 'property_type', 'locality']}, default=str)}")

q4 = sorted(corrupt_ids)
print(f"\nQ4 corrupt_listing_ids ({len(q4)}): {q4}")

# ===== Q6 COMPUTATION =====
print("\n" + "=" * 60)
print("Q6: AVG PRICE/SQFT FOR ACTIVE 2BHK")
print("=" * 60)

# Need unique listings only
unique_active_2bhk = [l for lid, l in unique_listings.items()
                      if l.get("is_live") is True 
                      and l.get("bedroom") == 2
                      and lid not in set(q4)
                      and lid not in fake_candidate_ids]

print(f"Active 2BHK unique listings (excl corrupt + fake): {len(unique_active_2bhk)}")

valid_for_q6 = [l for l in unique_active_2bhk
                if l.get("price") and l.get("carpet_area") and l["carpet_area"] > 0]

# Are prices in the right unit? Need to check
sample_prices = sorted([l["price"] / l["carpet_area"] for l in valid_for_q6])
print(f"Price/sqft range for valid 2BHK: {min(sample_prices):.0f} to {max(sample_prices):.0f}")
print(f"Median: {statistics.median(sample_prices):.0f}")

# For Pune apartments, realistic price/sqft is 5000-20000 INR
# If we see values like 97.8, those are in crore-like units
# Let's check the actual listing prices
sample_prices_raw = sorted([(l["price"], l["carpet_area"], l["price"]/l["carpet_area"]) for l in valid_for_q6])
print(f"\nSample valid 2BHK listings:")
for price, area, pps in sample_prices_raw[:5]:
    print(f"  price={price}, area={area}, p/sqft={pps:.0f}")
for price, area, pps in sample_prices_raw[-5:]:
    print(f"  price={price}, area={area}, p/sqft={pps:.0f}")

q6 = round(sum(l["price"] / l["carpet_area"] for l in valid_for_q6) / len(valid_for_q6), 2)
print(f"\nQ6 avg_price_per_sqft_2bhk: {q6}")

# ===== Q7 INVESTIGATION =====
print("\n" + "=" * 60)
print("Q7: COSTLIEST PROJECT - PRICE UNIT INVESTIGATION")
print("=" * 60)

# Project prices look like 97.8 which is clearly wrong if supposed to be rupees
# For Pune luxury apartments: max could be ~3-5 crore = 30,000,000 - 50,000,000 rupees
# 97.8 in crores = 978,000,000 rupees = about 97.8 crore - reasonable for luxury project!
# So price_max in projects is likely in CRORES, not rupees!

print("Project price analysis (looking for unit clues):")
all_proj_maxes_raw = sorted([(p.get("price_max", 0), p.get("project_id"), p.get("apartment_name")) 
                              for p in all_projects if p.get("price_max")], reverse=True)
print("Top 10 projects by price_max:")
for pmax, pid, name in all_proj_maxes_raw[:10]:
    print(f"  {pid} {name}: price_max={pmax} → if crore = {pmax * 1e7:.0f} rupees")

print("\nBottom 5 projects by price_max:")
for pmax, pid, name in all_proj_maxes_raw[-5:]:
    print(f"  {pid} {name}: price_max={pmax}")

# Check listing prices for same project
if all_projects:
    test_proj = all_projects[0]["project_id"]
    proj_listings = [l for l in all_listings if l.get("project_id") == test_proj]
    if proj_listings:
        sample_proj_listing = proj_listings[0]
        print(f"\nFor project {test_proj}:")
        print(f"  Project price_min={all_projects[0].get('price_min')}, price_max={all_projects[0].get('price_max')}")
        print(f"  Sample listing price: {sample_proj_listing.get('price')}")
        print(f"  → If listing price is rupees and project is crores, ratio = {sample_proj_listing.get('price', 0) / (all_projects[0].get('price_max', 1) or 1):.0f}")

# ===== FILTER INVESTIGATION =====
print("\n" + "=" * 60)  
print("FILTER INVESTIGATION")
print("=" * 60)

# Login first
auth_resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "demo1@ivy.homes", "password": "b9895dbe7f"},
    headers={"X-API-Key": API_KEY}
)
token = auth_resp.json().get("access_token", "")
session = requests.Session()
session.headers["X-API-Key"] = API_KEY
session.headers["Authorization"] = f"Bearer {token}"

# Test price filter more carefully
resp = session.get(f"{BASE_URL}/v1/listings", params={"limit": 20, "min_price": 10000000, "max_price": 11000000})
if resp.status_code == 200:
    d = resp.json()
    prices = [(r.get("price"), r.get("listing_id")) for r in d.get("results", [])]
    out_of_range = [(p, lid) for p, lid in prices if p is not None and (p < 10000000 or p > 11000000)]
    print(f"Price filter [10M, 11M]: total={d.get('total')}, out_of_range count={len(out_of_range)}")
    print(f"All prices: {[p for p, _ in prices]}")

# Test furnishing filter
resp = session.get(f"{BASE_URL}/v1/listings", params={"limit": 10, "furnishing": "fully-furnished"})
if resp.status_code == 200:
    d = resp.json()
    furnishings = [r.get("furnishing") for r in d.get("results", [])]
    non_match = [f for f in furnishings if f != "fully-furnished"]
    print(f"\nfurnishing=fully-furnished: total={d.get('total')}, non-matching: {non_match}")

# Test property_type filter
resp = session.get(f"{BASE_URL}/v1/listings", params={"limit": 10, "property_type": "apartment"})
if resp.status_code == 200:
    d = resp.json()
    types = [r.get("property_type") for r in d.get("results", [])]
    non_match = [t for t in types if t != "apartment"]
    print(f"\nproperty_type=apartment: total={d.get('total')}, non-matching: {non_match}")

# Test offset-based pagination (vs page-based)
resp1 = session.get(f"{BASE_URL}/v1/listings", params={"limit": 5, "page": 1})
resp2 = session.get(f"{BASE_URL}/v1/listings", params={"limit": 5, "offset": 0})
if resp1.status_code == 200:
    d1 = resp1.json()
    print(f"\nPage-based pagination fields: {[k for k in d1.keys() if k != 'results']}")
    print(f"Response structure: { {k: d1[k] for k in d1 if k != 'results'} }")
if resp2.status_code == 200:
    d2 = resp2.json()
    print(f"Offset-based pagination (offset=0): status 200, fields: { {k: d2[k] for k in d2 if k != 'results'} }")

# Check /auth/logout
resp_logout = session.post(f"{BASE_URL}/auth/logout")
print(f"\n/auth/logout: {resp_logout.status_code} - {resp_logout.text[:100]}")

# Test favourites paths
for fav_path in ["/v1/favourites", "/v1/favorites", "/favourites", "/favorites"]:
    r = session.get(f"{BASE_URL}{fav_path}")
    print(f"  {fav_path}: {r.status_code}")

# Check /v1/listings/{id}/similar more carefully
lid = unique_listings and list(unique_listings.keys())[0]
r = session.get(f"{BASE_URL}/v1/listings/{lid}/similar")
print(f"\n/v1/listings/{lid}/similar: {r.status_code} - {r.text[:100]}")

# ===== FINAL SUMMARY =====
print("\n" + "=" * 60)
print("FINAL ANSWERS (UPDATED)")
print("=" * 60)

q1 = len(all_listings)
q2 = len(prop_groups) + len(set(no_location))
q3 = len([l for l in all_listings if l.get("is_live") is True])
q4_final = sorted(set(q4))
q5 = sum(r.get("price", 0) for r in all_rentals if r.get("locality", "").lower() == "baner")
# q6 computed above
q7_id = all_proj_maxes_raw[0][1] if all_proj_maxes_raw else ""
q7_price_raw = all_proj_maxes_raw[0][0] if all_proj_maxes_raw else 0
q7_price_inr = int(q7_price_raw * 1e7)  # Convert crores to rupees

recent_ids = []
for l in all_listings:
    posted_str = l.get("posted_at", "")
    if not posted_str:
        continue
    try:
        dt = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            recent_ids.append(l["listing_id"])
    except:
        pass
q8 = len(set(recent_ids))  # unique

q9 = sorted(unique_fake_ids)
q10_wrong = 0
for proj in all_projects:
    pid = proj["project_id"]
    doc_count = proj.get("total_listings", 0)
    # Count from our data (using all listings, even duplicates, since that's what API returns)
    actual_count = sum(1 for l in all_listings if l.get("project_id") == pid)
    # But unique listing ids?
    actual_unique = len(set(l["listing_id"] for l in all_listings if l.get("project_id") == pid))
    if doc_count != actual_count:
        q10_wrong += 1
q10 = q10_wrong

print(f"Q1 total_listing_records: {q1}")
print(f"Q2 unique_properties: {q2}")
print(f"Q3 active_listings: {q3}")
print(f"Q4 corrupt_listing_ids: {q4_final}")
print(f"Q5 total_monthly_rent: {q5}")
print(f"Q6 avg_price_per_sqft_2bhk: {q6}")
print(f"Q7 costliest_project: {{'project_id': '{q7_id}', 'price_max_inr': {q7_price_inr}}}")
print(f"  (raw project price_max was {q7_price_raw}, converted to rupees: {q7_price_inr})")
print(f"Q8 listings_last_7_days: {q8}")
print(f"Q9 fake_listing_ids ({len(q9)}): first 10 = {q9[:10]}")
print(f"Q10 projects_with_wrong_listing_count: {q10}")

# Save
final_answers = {
    "total_listing_records": q1,
    "unique_properties": q2,
    "active_listings": q3,
    "corrupt_listing_ids": q4_final,
    "total_monthly_rent": q5,
    "avg_price_per_sqft_2bhk": q6,
    "costliest_project": {"project_id": q7_id, "price_max_inr": q7_price_inr},
    "listings_last_7_days": q8,
    "fake_listing_ids": q9,
    "projects_with_wrong_listing_count": q10
}
with open("final_answers.json", "w") as f:
    json.dump(final_answers, f, indent=2)
print("\nSaved to final_answers.json")
