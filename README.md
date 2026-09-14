# Ivy Homes — Software Engineering Internship Assignment (September 2026)

**Candidate:** Harsh Srivastava  
**City:** Pune  
**Assigned Locality:** Baner  
**API Key:** `IVY26-5993D94E34F4`  

---

## 1. How to Run the Application

The frontend is a lightweight, zero-dependency single-page application built with clean, responsive HTML, CSS, and modern JavaScript.

### Option A: Open directly in browser
Simply open `frontend/index.html` in any modern web browser.

### Option B: Local HTTP server
```bash
# Using Python
cd frontend
python -m http.server 3000
# Open http://localhost:3000 in your browser

# Or using npx serve
npx serve frontend
```

### Option C: Production Deployment
The application is deployable directly as static files on Vercel, Netlify, Cloudflare Pages, or GitHub Pages.

### Login Credentials
The application supports all three demo accounts with shared password:
- `demo1@ivy.homes` / `b9895dbe7f`
- `demo2@ivy.homes` / `b9895dbe7f`
- `demo3@ivy.homes` / `b9895dbe7f`

---

## 2. Methodology: Investigating the API & Uncovering Discrepancies

Rather than trusting documentation or single-point responses, we downloaded the entire dataset (3,650 listings, 1,400 rentals, 450 projects) via script and performed systemic statistical and boundary analysis.

### A. Authentication & Session Management
- **The Lie:** The reference states API keys should be sent as query parameters (`?api_key=...`) and login returns `token` valid for 24 hours without refresh.
- **The Truth:** The server responds with `401 Unauthorized` demanding `X-API-Key` in the request header. Login returns `access_token` and `refresh_token` with an expiration of only 900 seconds (15 minutes). Furthermore, an unadvertised `POST /auth/refresh` endpoint exists.
- **Our Fix:** The frontend implements an automated token management service that stores the refresh token, monitors access token lifespan, and automatically refreshes sessions prior to expiration.

### B. Massive Listing Duplication
- **The Lie:** "Every `listing_id` is globally unique, and each listing corresponds to exactly one physical property."
- **The Truth:** The API returns 3,650 records, but there are only 50 unique listing IDs. Every single listing ID is repeated exactly 73 times.
- **Our Fix:** Client-side deduplication indexes listings by `listing_id` and physical property fingerprints (lat/long, floor, BHK, carpet area) to present clean, unique property cards and compute accurate metrics.

### C. Unit Mismatches in Projects
- **The Lie:** All prices across all endpoints are integer Indian Rupees.
- **The Truth:** `/v1/projects` expresses `price_min` and `price_max` in Lakhs INR (e.g. `97.8` represents ₹97.8 Lakhs = ₹9,780,000), while `/v1/listings` expresses prices in raw Rupees. Additionally, 36 out of 50 projects have `price_min` and `price_max` swapped (e.g. `min=80.0, max=3.22`).
- **Our Fix:** Project prices are normalized as `min(price_min, price_max)` and `max(price_min, price_max)` and converted to human-readable Lakhs/Crores display.

### D. Silent Filter Invalidation
- **The Lie:** Query parameters `min_price` and `max_price` filter listings on the server.
- **The Truth:** The parameters are accepted with `200 OK` status but completely ignored by backend query execution.
- **Our Fix:** The frontend performs client-side filtering and multi-attribute sorting over cached records to guarantee that user-selected price boundaries and filters are strictly respected.

### E. Missing / Misnamed Endpoints
- Singular `GET /v1/listing/{id}` returns `404 Not Found`; plural `GET /v1/listings/{id}` is the actual endpoint.
- `GET /v1/listings/{id}/similar` and `GET /v1/analytics/summary` return `404 Not Found`.
- **Our Fix:** The frontend uses the plural route and computes similarity and city-wide insights aggregates directly on the client.

---

## 3. What We Checked That Turned Out to Be Fine (Negative Hypotheses)

In thorough testing, several hypotheses about potential flaws turned out to be completely fine:

1. **Timestamp Consistency:** We suspected timestamps might mix UTC and local IST offsets inconsistently. All `posted_at` values in listings consistently used ISO 8601 UTC format with `Z` suffix.
2. **Locality Filter Accuracy:** We tested whether the `locality` query filter was leaky. Filtering for `baner` or `kharadi` on `/v1/listings` strictly returned listings in those respective localities without bleed from other areas.
3. **BHK Parameter Accuracy:** We tested if `bhk` parameter quietly returned mismatched bedroom counts. The server-side BHK filter worked accurately.
4. **Negative Prices in Raw Listings:** Despite negative numbers appearing in sort tests, all individual listing records had strictly positive price values in valid INR ranges.
5. **Rental Deposit & Maintenance Units:** We checked if rental deposit or maintenance figures were denominated in Lakhs like projects. Both were correctly stored in integer Rupees.
6. **RERA Number Format:** We verified whether RERA registration numbers in project data were syntactically invalid or truncated; all followed standard state format patterns.

---

## 4. Answers to the 10 Questions (Pune Dataset)

| # | Key | Answer | Description |
|---|---|---|---|
| 1 | `total_listing_records` | **3650** | Total retrievable records from `/v1/listings` |
| 2 | `unique_properties` | **50** | Distinct physical properties across all records |
| 3 | `active_listings` | **2920** | Retrievable listing records with `is_live: true` (40 unique × 73) |
| 4 | `corrupt_listing_ids` | `["MAG-3001035", "MAG-3001327", "MAG-3001519", "MAG-3001756", "MAG-3002851", "MAG-3003434"]` | Listings with physically impossible area/BHK/furnishing |
| 5 | `total_monthly_rent` | **3295600** | Sum of monthly rent across all 84 Baner rental records |
| 6 | `avg_price_per_sqft_2bhk` | **10789.96** | Mean price/sqft for active 2BHK listings (excl. corrupt/fake) |
| 7 | `costliest_project` | `{"project_id": "P30015", "price_max_inr": 9780000}` | Century Grand (97.8 Lakhs = ₹97,80,000 INR) |
| 8 | `listings_last_7_days` | **73** | Listing records posted in `[2026-09-03T00:00:00+05:30, 2026-09-10T00:00:00+05:30)` (1 unique ID × 73) |
| 9 | `fake_listing_ids` | `["ZER-3001479"]` | Fraudulent lead-gen bait listing requesting upfront token advance |
| 10 | `projects_with_wrong_listing_count` | **47** | Projects where `total_listings` mismatches actual linked listings |

---

## 5. What We Would Do With Another Two Days

If granted 48 additional hours to develop this project further:
1. **Interactive Geospatial Map View:** Integrate Leaflet / Mapbox with clustering to visualize properties across Pune localities, overlaying price heatmaps.
2. **Automated Data Quality Pipeline:** Implement a client/server data sanitizer with rule-based validators (detecting inverted min/max, suspicious advance token requests, area anomalies).
3. **Offline Sync & Progressive Web App (PWA):** Cache listings in IndexedDB with Service Worker support for offline browsing and instant filtering.
4. **End-to-End Test Suite:** Add automated Playwright / Cypress test suites verifying auth expiry recovery, client-side deduplication, and filter integrity.

---

## 6. AI Usage Disclosure
In accordance with assignment guidelines, an LLM assistant (Google Antigravity / Gemini) was utilized for exploratory script scaffolding, statistical data aggregation, and rapid UI development. All findings and data points were verified and reproduced against the running API.
