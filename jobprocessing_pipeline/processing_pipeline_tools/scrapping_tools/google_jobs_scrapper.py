import os
from dotenv import load_dotenv
from serpapi import GoogleSearch
import re
import json
from datetime import datetime, timedelta

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if not SERPAPI_KEY:
    raise ValueError("SERPAPI_KEY not found in .env file")

JOB_MAX_AGE_DAYS = 7

def is_within_timeframe(job: dict, max_age_days: int = JOB_MAX_AGE_DAYS) -> bool:
    """Check if job was posted within max_age_days using SerpApi structure."""
    
    # Priority 1: detected_extensions (structured data)
    detected = job.get("detected_extensions", {})
    date_str = detected.get("posted_at") or detected.get("posted")
    if date_str:
        date_str_lower = date_str.lower()
        if _is_recent(date_str_lower):
            return True
    
    # Priority 2: extensions list (raw strings like ["1 week ago", "Full time"])
    extensions = job.get("extensions", [])
    for ext in extensions:
        if isinstance(ext, str) and _is_recent(ext.lower()):
            return True
    
    # Priority 3: legacy fields
    for field in ["posted_at", "date_posted"]:
        date_str = job.get(field)
        if date_str and _is_recent(date_str.lower()):
            return True
    
    return True  # Conservative: keep if unclear

def _is_recent(date_str_lower: str) -> bool:
    """Parse relative dates and check against max age."""
    if any(word in date_str_lower for word in ["just posted", "today", "hour", "minute"]):
        return True
    
    match = re.search(r"(\d+)\s*(day|week|month)s?\s*ago", date_str_lower)
    if match:
        num, unit = int(match.group(1)), match.group(2)
        if unit == "month":
            num *= 30
        elif unit == "week":
            num *= 7
        return num <= JOB_MAX_AGE_DAYS
    
    return True

def search_google_jobs_sync(queries: list[dict], max_results_per_query: int = 2):
    all_jobs = []
    seen_ids = set()

    for i, query in enumerate(queries, 1):
        position = query["position"].strip()
        is_remote = query.get("remote", False)
        location_input = query.get("location", "Remote").strip()

        print(f"\nProcessing query {i}/{len(queries)}: '{position}' {'(remote)' if is_remote else ''}")

        # Build query
        base_query = f'"{position}"'
        if is_remote:
            base_query += ' remote'
        else:
            base_query += ' (remote OR onsite)'

        params = {
            "engine": "google_jobs",
            "q": base_query,
            "hl": "en",
            "api_key": SERPAPI_KEY,
            "num": max_results_per_query
        }

        # Location handling
        if location_input.lower() != "remote":
            params["location"] = location_input

        try:
            print(f"  Search params: {params['q']}")
            search = GoogleSearch(params)
            results = search.get_dict()

            if "error" in results:
                print(f"  ❌ SerpApi error: {results['error']}")
                continue

            jobs_raw = results.get("jobs_results", [])
            print(f"  Received {len(jobs_raw)} raw jobs")

            # Process jobs (already dicts from SerpApi)
            recent_jobs = []
            for job in jobs_raw:
                if isinstance(job, dict) and is_within_timeframe(job):
                    recent_jobs.append(job)

            # Deduplicate
            unique_jobs = []
            for job in recent_jobs:
                job_id = job.get('job_id') or f"{job.get('title', '')}_{job.get('company_name', '')}"
                if job_id not in seen_ids:
                    seen_ids.add(job_id)
                    unique_jobs.append(job)

            all_jobs.extend(unique_jobs)
            print(f"  ✓ Added {len(unique_jobs)} recent/unique jobs (total: {len(all_jobs)})")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue

    return all_jobs