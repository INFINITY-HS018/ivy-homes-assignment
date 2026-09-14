#!/usr/bin/env python3
"""
Ivy Homes - Complete Data Fetcher & Analyzer
Auth: X-API-Key header + Bearer token required
"""

import requests
import json
import time
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import math

API_KEY = "IVY26-5993D94E34F4"
BASE_URL = "https://solve.ivy.homes"
ASSIGNED_LOCALITY = "baner"
IST = timezone(timedelta(hours=5, minutes=30))
REFERENCE = datetime(2026, 9, 10, 0, 0, 0, tzinfo=IST)
REF_MINUS_7 = REFERENCE - timedelta(days=7)
EMAIL = "demo1@ivy.homes"
PASSWORD = "b9895dbe7f"

# Step 1: Login to get access token
print("=" * 60)
print("IVY HOMES DATA FETCHER v3")
print("=" * 60)

print("\n[Step 1: Login]")
auth_resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": EMAIL, "password": PASSWORD},
    headers={"X-API-Key": API_KEY}
)
print(f"  Status: {auth_resp.status_code}")
auth_data = auth_resp.json()
print(json.dumps(auth_data, indent=2))

access_token = auth_data.get("access_token") or auth_data.get("token", "")
refresh_token = auth_data.get("refresh_token", "")

# Setup session with both headers
session = requests.Session()
session.headers["X-API-Key"] = API_KEY
session.headers["Authorization"] = f"Bearer {access_token}"

def refresh_if_needed():
    """Refresh the access token using refresh_token."""
    global access_token
    print("  [Refreshing token...]")
    r = requests.post(
        f"{BASE_URL}/auth/refresh",
        headers={"X-API-Key": API_KEY, "Authorization": f"Bearer {refresh_token}"}
    )
    if r.status_code == 200:
        data = r.json()
        access_token = data.get("access_token", "")
        session.headers["Authorization"] = f"Bearer {access_token}"
        print(f"  Token refreshed: {access_token[:30]}...")
    else:
        print(f"  Refresh failed: {r.status_code} {r.text}")

# Test auth refresh endpoint
print("\n[Testing /auth/refresh]")
r = requests.post(f"{BASE_URL}/auth/refresh", 
    headers={"X-API-Key": API_KEY, "Authorization": f"Bearer {refresh_token}"})
print(f"  /auth/refresh status: {r.status_code} - {r.text[:200]}")

def fetch_all(endpoint, extra_params=None, verbose=True):
    """Fetch all pages from an endpoint."""
    all_results = []
    page = 1
    limit = 200
    total = None
    
    while True:
        p = {"page": page, "limit": limit}
        if extra_params:
            p.update(extra_params)
        
        resp = session.get(f"{BASE_URL}{endpoint}", params=p)
        
        if resp.status_code == 401:
            refresh_if_needed()
            resp = session.get(f"{BASE_URL}{endpoint}", params=p)
        
        if resp.status_code != 200:
            print(f"  ERROR {resp.status_code} on {endpoint} p{page}: {resp.text[:200]}")
            break
        
        data = resp.json()
        
        if isinstance(data, dict) and "results" in data:
            results = data["results"]
            if total is None:
                total = data.get("total", 0)
                if verbose:
                    print(f"  {endpoint}: total={total}, pages={math.ceil(total/limit) if limit else '?'}")
            
            all_results.extend(results)
            
            if verbose and (page % 5 == 0 or len(all_results) >= total):
                print(f"    page={page}, fetched={len(all_results)}/{total}")
            
            if len(all_results) >= total:
                break
            if len(results) == 0:
                break
            page += 1
        else:
            return data
        
        time.sleep(0.02)
    
    return all_results

# Test a single listing first
print("\n[Quick test]")
r = session.get(f"{BASE_URL}/v1/listings", params={"limit": 1})
print(f"  /v1/listings status: {r.status_code} - {r.text[:300]}")

# Fetch all data
print("\n[Fetching ALL Listings]")
all_listings = fetch_all("/v1/listings")
print(f"Total listings: {len(all_listings)}")
with open("all_listings.json", "w") as f:
    json.dump(all_listings, f, indent=2)

print("\n[Fetching ALL Rentals]")
all_rentals = fetch_all("/v1/rentals")
print(f"Total rentals: {len(all_rentals)}")
with open("all_rentals.json", "w") as f:
    json.dump(all_rentals, f, indent=2)

print("\n[Fetching ALL Projects]")
all_projects = fetch_all("/v1/projects")
print(f"Total projects: {len(all_projects)}")
with open("all_projects.json", "w") as f:
    json.dump(all_projects, f, indent=2)

# Check analytics
print("\n[Analytics endpoints]")
for ep in ["/v1/analytics/summary", "/v1/analytics", "/analytics/summary"]:
    r = session.get(f"{BASE_URL}{ep}")
    print(f"  {ep}: {r.status_code} - {r.text[:100]}")

if not all_listings:
    print("ERROR: No listings fetched!")
    exit(1)

# ===== SHOW SAMPLE DATA =====
print("\n" + "=" * 60)
print("SAMPLE DATA")
print("=" * 60)
print("\nSample listing:")
print(json.dumps(all_listings[0], indent=2))
print("\nAll listing fields:", list(all_listings[0].keys()))

if all_rentals:
    print("\nSample rental:")
    print(json.dumps(all_rentals[0], indent=2))
    print("All rental fields:", list(all_rentals[0].keys()))

if all_projects:
    print("\nSample project:")
    print(json.dumps(all_projects[0], indent=2))
    print("All project fields:", list(all_projects[0].keys()))

# ===== ANALYSIS =====
print("\n" + "=" * 60)
print("ANALYSIS")
print("=" * 60)

# Q1
q1 = len(all_listings)
print(f"\nQ1 total_listing_records: {q1}")

# Q3: Active listings
is_live_dist = defaultdict(int)
for l in all_listings:
    is_live_dist[str(l.get("is_live"))] += 1
print(f"\nQ3 is_live distribution: {dict(is_live_dist)}")
active_listings = [l for l in all_listings if l.get("is_live") is True]
q3 = len(active_listings)
print(f"Q3 active_listings: {q3}")

# Q2: Unique properties
print("\n[Q2: Unique properties]")
# Same property = listed on multiple portals but same physical unit
# Use (lat, lon, floor, bedroom, area) as fingerprint
seen_by_precise_loc = defaultdict(list)
for l in all_listings:
    lat = l.get("latitude")
    lon = l.get("longitude")
    if lat and lon:
        key = (round(float(lat), 5), round(float(lon), 5), l.get("bedroom"), l.get("floor"), l.get("carpet_area"))
        seen_by_precise_loc[key].append(l["listing_id"])

# Alternative: same name + locality + floor + bedroom + area
seen_by_attrs = defaultdict(list)
for l in all_listings:
    key = (
        l.get("apartment_name", "").strip().lower(),
        l.get("locality", "").strip().lower(), 
        l.get("bedroom"),
        l.get("floor"),
        l.get("bathroom"),
        l.get("carpet_area")
    )
    seen_by_attrs[key].append(l["listing_id"])

prop_dupes_loc = {k: v for k, v in seen_by_precise_loc.items() if len(v) > 1}
prop_dupes_attr = {k: v for k, v in seen_by_attrs.items() if len(v) > 1}
print(f"  Prop groups by (lat,lon,bed,floor,area): {len(seen_by_precise_loc)}")
print(f"  Duplicate groups (same prop, multiple listings): {len(prop_dupes_loc)}")
print(f"  Duplicate groups (by attrs): {len(prop_dupes_attr)}")
total_extra_records = sum(len(v) - 1 for v in prop_dupes_loc.values())
print(f"  Extra records from duplicates: {total_extra_records}")
# Q2 = total - extra records from same property
q2 = q1 - total_extra_records
print(f"Q2 unique_properties (estimate): {q2}")

# Show some duplicate groups
print("  Sample duplicate groups:")
for k, v in list(prop_dupes_loc.items())[:5]:
    print(f"    {k} -> {v}")
    for lid in v[:2]:
        l = next(x for x in all_listings if x["listing_id"] == lid)
        print(f"      {lid}: website={l.get('website')}, price={l.get('price')}")

# Q4: Corrupt listings
print("\n[Q4: Corrupt listings]")
corrupt_ids = []
for l in all_listings:
    lid = l["listing_id"]
    issues = []
    
    ca = l.get("carpet_area")
    sba = l.get("super_built_up_area") or l.get("super_builtup_area")
    price = l.get("price")
    floor_ = l.get("floor")
    total_floors = l.get("total_floors")
    bedroom = l.get("bedroom")
    bathroom = l.get("bathroom")
    
    if ca is not None and ca <= 0:
        issues.append(f"carpet_area={ca} (non-positive)")
    if price is not None and price <= 0:
        issues.append(f"price={price} (non-positive)")
    if bedroom is not None and bedroom < 0:
        issues.append(f"bedroom={bedroom} (negative)")
    if floor_ is not None and total_floors is not None and floor_ > total_floors:
        issues.append(f"floor({floor_}) > total_floors({total_floors})")
    if ca and sba and ca > sba:
        issues.append(f"carpet_area({ca}) > super_built_up_area({sba})")
    
    if issues:
        corrupt_ids.append(lid)
        print(f"  CORRUPT: {lid}: {', '.join(issues)}")

q4 = sorted(corrupt_ids)
print(f"\nQ4 corrupt_listing_ids ({len(q4)}): {q4}")

# Q5: Total monthly rent in Baner
print("\n[Q5: Rentals in Baner]")
baner_rentals = [r for r in all_rentals if r.get("locality", "").lower() == "baner"]
print(f"  Rentals in Baner: {len(baner_rentals)}")
# What's the price field?
if baner_rentals:
    sample = baner_rentals[0]
    print(f"  Price-related fields: { {k: sample[k] for k in sample if 'price' in k.lower() or 'rent' in k.lower()} }")
q5 = sum(r.get("price", 0) for r in baner_rentals)
print(f"Q5 total_monthly_rent (Baner): {q5}")

# All localities in rentals
rental_locs = defaultdict(int)
for r in all_rentals:
    rental_locs[r.get("locality", "").lower()] += 1
print(f"  Rental localities: {dict(sorted(rental_locs.items(), key=lambda x: -x[1]))}")

# Q6: Avg price/sqft for active 2BHK (excl corrupt + fake - compute after Q9)
# Pre-compute for active 2BHK
active_2bhk = [l for l in active_listings if l.get("bedroom") == 2]
print(f"\n[Q6: Active 2BHK listings: {len(active_2bhk)}]")

# Q7: Costliest project
print("\n[Q7: Costliest project]")
if all_projects:
    proj_fields = [k for k in all_projects[0].keys() if "price" in k.lower()]
    print(f"  Price fields in projects: {proj_fields}")
    costliest = max(all_projects, key=lambda p: p.get("price_max", 0))
    q7_id = costliest.get("project_id", "")
    q7_price = costliest.get("price_max", 0)
    print(f"Q7 costliest: {{'project_id': '{q7_id}', 'price_max_inr': {q7_price}}}")
    print(f"  Name: {costliest.get('apartment_name')}, locality: {costliest.get('locality')}")
    
    # Top 5
    sorted_projects = sorted(all_projects, key=lambda p: p.get("price_max", 0), reverse=True)
    print(f"  Top 5 projects:")
    for p in sorted_projects[:5]:
        print(f"    {p['project_id']}: {p.get('apartment_name')} - price_max={p.get('price_max')}")

# Q8: Listings in [REFERENCE-7, REFERENCE)
print("\n[Q8: Listings in last 7 days before reference]")
print(f"  Window: [{REF_MINUS_7.isoformat()}, {REFERENCE.isoformat()})")
recent_ids = []
ts_formats_seen = set()
for l in all_listings:
    posted_str = l.get("posted_at", "")
    if not posted_str:
        continue
    try:
        if posted_str.endswith("Z"):
            ts_formats_seen.add("UTC-Z")
            dt = datetime.fromisoformat(posted_str[:-1]).replace(tzinfo=timezone.utc)
        else:
            ts_formats_seen.add("offset")
            dt = datetime.fromisoformat(posted_str)
        dt_ist = dt.astimezone(IST)
        if REF_MINUS_7 <= dt_ist < REFERENCE:
            recent_ids.append(l["listing_id"])
    except Exception as e:
        print(f"  Error parsing '{posted_str}': {e}")

q8 = len(recent_ids)
print(f"  Timestamp formats seen: {ts_formats_seen}")
print(f"  Sample posted_at values: {[l.get('posted_at') for l in all_listings[:3]]}")
print(f"Q8 listings_last_7_days: {q8}")

# Q9: Fake listings
print("\n[Q9: Fake listings - deep analysis]")

# Strategy 1: Same contact with very many listings (likely an agent spamming)
# Strategy 2: Price per sqft as extreme outlier within locality
# Strategy 3: Listings that describe enquiry generation (from problem statement hint)

# Compute per-locality price/sqft stats
locality_stats = defaultdict(list)
for l in all_listings:
    if l.get("price") and l.get("carpet_area") and l["carpet_area"] > 0 and l["listing_id"] not in q4:
        ppsqft = l["price"] / l["carpet_area"]
        locality_stats[l.get("locality", "")].append((ppsqft, l["listing_id"], l.get("price"), l.get("carpet_area")))

print(f"  Locality price/sqft stats:")
locality_median = {}
locality_stdev = {}
for loc, vals in sorted(locality_stats.items()):
    ppss = [v[0] for v in vals]
    if len(ppss) >= 2:
        med = statistics.median(ppss)
        std = statistics.stdev(ppss)
        locality_median[loc] = med
        locality_stdev[loc] = std

# Find outliers (>3 sigma from median within locality)
outliers = []
for loc, vals in locality_stats.items():
    ppss = [v[0] for v in vals]
    if len(ppss) < 3:
        continue
    med = statistics.median(ppss)
    std = statistics.stdev(ppss) if len(ppss) > 1 else 0
    if std == 0:
        continue
    for pps, lid, price, area in vals:
        z = abs(pps - med) / std
        if z > 3:
            outliers.append((z, lid, pps, med, std, loc, price, area))

outliers.sort(reverse=True)
print(f"\n  Price/sqft outliers (>3 sigma within locality):")
for z, lid, pps, med, std, loc, price, area in outliers[:20]:
    print(f"    z={z:.1f} {lid}: pps={pps:.0f} (median={med:.0f}, std={std:.0f}) loc={loc} price={price} area={area}")

# Check for suspiciously round prices or patterns
print(f"\n  Contact volume analysis:")
contact_map = defaultdict(list)
for l in all_listings:
    c = l.get("posted_by_contact", "")
    if c:
        contact_map[c].append(l["listing_id"])

top_contacts = sorted(contact_map.items(), key=lambda x: -len(x[1]))[:10]
for c, ids in top_contacts:
    print(f"    {c}: {len(ids)} listings")
    # Check price/sqft variation for this contact
    pps_vals = []
    for lid in ids:
        l = next((x for x in all_listings if x["listing_id"] == lid), None)
        if l and l.get("price") and l.get("carpet_area") and l["carpet_area"] > 0:
            pps_vals.append(l["price"] / l["carpet_area"])
    if pps_vals:
        print(f"      price/sqft range: {min(pps_vals):.0f} - {max(pps_vals):.0f}")

# Check descriptions for "generated" content
print(f"\n  Checking descriptions for anomalies:")
desc_lens = [(len(l.get("description", "") or ""), l["listing_id"]) for l in all_listings]
desc_lens.sort()
print(f"  Shortest descriptions:")
for length, lid in desc_lens[:5]:
    l = next(x for x in all_listings if x["listing_id"] == lid)
    print(f"    {lid}: len={length}, desc='{l.get('description', '')[:100]}'")

# Look for listings where price is extremely low (possible bait)
all_valid = [(l.get("price", 0) / l.get("carpet_area", 1) if l.get("carpet_area") else 0, l) 
             for l in all_listings if l["listing_id"] not in q4 and l.get("carpet_area")]
all_valid.sort(key=lambda x: x[0])
print(f"\n  10 cheapest listings (price/sqft):")
for pps, l in all_valid[:10]:
    print(f"    {l['listing_id']}: pps={pps:.0f}, price={l.get('price')}, area={l.get('carpet_area')}, loc={l.get('locality')}")

# Q10: Projects with wrong listing count
print("\n[Q10: Projects with wrong listing count]")
project_count_in_listings = defaultdict(int)
for l in all_listings:
    pid = l.get("project_id")
    if pid:
        project_count_in_listings[pid] += 1

wrong_projects = []
for proj in all_projects:
    pid = proj["project_id"]
    doc_count = proj.get("total_listings", 0)
    actual_count = project_count_in_listings.get(pid, 0)
    if doc_count != actual_count:
        wrong_projects.append({
            "project_id": pid,
            "documented": doc_count,
            "actual": actual_count,
            "diff": doc_count - actual_count
        })

q10 = len(wrong_projects)
print(f"Q10 projects_with_wrong_listing_count: {q10}")
print(f"  Sample wrong projects:")
for wp in wrong_projects[:10]:
    print(f"    {wp}")

# Filter tests for documentation discrepancy detection
print("\n" + "=" * 60)
print("FILTER & ENDPOINT TESTS")
print("=" * 60)

# Test: does bhk actually filter?
r1 = session.get(f"{BASE_URL}/v1/listings", params={"limit": 20, "bhk": 2})
if r1.status_code == 200:
    d1 = r1.json()
    bedrooms = [r.get("bedroom") for r in d1.get("results", [])]
    non_2bhk = [b for b in bedrooms if b != 2]
    print(f"\n  bhk=2 filter: returned bedrooms {set(bedrooms)}, non-2BHK count: {len(non_2bhk)}, total={d1.get('total')}")
    if non_2bhk:
        print(f"  FINDING: bhk filter does NOT work! Returned non-2BHK: {non_2bhk}")

# Test sort
r_desc = session.get(f"{BASE_URL}/v1/listings", params={"limit": 10, "sort_by": "price", "order": "desc"})
r_asc = session.get(f"{BASE_URL}/v1/listings", params={"limit": 10, "sort_by": "price", "order": "asc"})
if r_desc.status_code == 200 and r_asc.status_code == 200:
    prices_desc = [r.get("price") for r in r_desc.json().get("results", [])]
    prices_asc = [r.get("price") for r in r_asc.json().get("results", [])]
    desc_sorted = prices_desc == sorted(prices_desc, reverse=True)
    asc_sorted = prices_asc == sorted(prices_asc)
    print(f"\n  sort_by=price desc: {prices_desc[:5]}, is_sorted_desc: {desc_sorted}")
    print(f"  sort_by=price asc: {prices_asc[:5]}, is_sorted_asc: {asc_sorted}")

# Test min/max price filter
r_price = session.get(f"{BASE_URL}/v1/listings", params={"limit": 10, "min_price": 10000000, "max_price": 11000000})
if r_price.status_code == 200:
    d_price = r_price.json()
    prices = [r.get("price") for r in d_price.get("results", [])]
    out_of_range = [p for p in prices if p is not None and (p < 10000000 or p > 11000000)]
    print(f"\n  price filter [10M,11M]: total={d_price.get('total')}, out_of_range={out_of_range}")

# Test locality filter
r_loc = session.get(f"{BASE_URL}/v1/listings", params={"limit": 20, "locality": "baner"})
if r_loc.status_code == 200:
    d_loc = r_loc.json()
    locs = set(r.get("locality") for r in d_loc.get("results", []))
    print(f"\n  locality=baner: returned localities={locs}, total={d_loc.get('total')}")

# Test /v1/listing (singular) vs /v1/listings/{id}
if all_listings:
    lid = all_listings[0]["listing_id"]
    r_singular = session.get(f"{BASE_URL}/v1/listing/{lid}")
    r_plural = session.get(f"{BASE_URL}/v1/listings/{lid}")
    print(f"\n  /v1/listing/{{id}} (singular as documented): {r_singular.status_code}")
    print(f"  /v1/listings/{{id}} (plural): {r_plural.status_code}")
    if r_plural.status_code == 200:
        print(f"  NOTE: Plural path works, singular doesn't (or vice versa)")

# Test /v1/listings/{id}/similar
r_sim = session.get(f"{BASE_URL}/v1/listings/{all_listings[0]['listing_id']}/similar")
print(f"\n  /v1/listings/{{id}}/similar: {r_sim.status_code} - {r_sim.text[:100]}")

# Test favourites (need auth)
r_fav = session.get(f"{BASE_URL}/v1/favourites")
print(f"\n  GET /v1/favourites: {r_fav.status_code} - {r_fav.text[:100]}")

# Test project_id filter on listings
if all_projects:
    pid = all_projects[0]["project_id"]
    r_proj = session.get(f"{BASE_URL}/v1/listings", params={"limit": 5, "project_id": pid})
    print(f"\n  project_id={pid} filter: {r_proj.status_code} - {r_proj.text[:100]}")

# ===== FINAL SUMMARY =====
print("\n" + "=" * 60)
print("FINAL ANSWERS")
print("=" * 60)

# Q6: avg price per sqft for active 2BHK (excl corrupt + fake)
# For now, compute excluding corrupt only (will update after manual fake ID analysis)
exclude_ids = set(q4)  # Add fake IDs once identified
valid_2bhk = [l for l in active_2bhk 
              if l["listing_id"] not in exclude_ids 
              and l.get("price") and l.get("carpet_area") and l["carpet_area"] > 0]
if valid_2bhk:
    ppsqft_vals = [l["price"] / l["carpet_area"] for l in valid_2bhk]
    q6 = round(sum(ppsqft_vals) / len(ppsqft_vals), 2)
else:
    q6 = 0.0
print(f"Q6 avg_price_per_sqft_2bhk (excl corrupt, pre-fake): {q6} (from {len(valid_2bhk)} listings)")

print(f"\nQ1 total_listing_records: {q1}")
print(f"Q2 unique_properties: {q2}")
print(f"Q3 active_listings: {q3}")
print(f"Q4 corrupt_listing_ids: {q4}")
print(f"Q5 total_monthly_rent (Baner): {q5}")
print(f"Q6 avg_price_per_sqft_2bhk: {q6}")
print(f"Q7 costliest_project: {{'project_id': '{q7_id}', 'price_max_inr': {q7_price}}}")
print(f"Q8 listings_last_7_days: {q8}")
print(f"Q9 fake_listing_ids: [NEEDS ANALYSIS - see outliers above]")
print(f"Q10 projects_with_wrong_listing_count: {q10}")

# Save intermediate results
results = {
    "q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5,
    "q6": q6, "q7_id": q7_id, "q7_price": q7_price,
    "q8": q8, "q10": q10,
    "outliers": [(z, lid, pps, med, loc) for z, lid, pps, med, std, loc, price, area in outliers[:30]],
    "wrong_projects": wrong_projects,
    "top_contacts": [(c, ids) for c, ids in top_contacts],
    "corrupt_details": {lid: issues for lid in corrupt_ids for issues in [corrupt_details.get(lid, [])]}
}
with open("analysis_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\nSaved to analysis_results.json")
