import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ACTOR_ID = "misceres~indeed-scraper"

# ── Time frame filter ─────────────────────────────────────────────────────────
JOB_MAX_AGE_DAYS = 7


def is_within_timeframe(job: dict, max_age_days: int = JOB_MAX_AGE_DAYS) -> bool:
    """
    Returns True if the job was posted within the last `max_age_days` days.
    Checks both 'postingDateParsed' and 'scrapedAt' fields as fallback.
    """
    date_str = job.get("postingDateParsed") or job.get("scrapedAt")

    if not date_str:
        # If no date info at all, we can't verify — exclude it to be safe
        return False

    try:
        # Parse ISO 8601 format: e.g. "2026-03-07T05:52:26.412Z"
        posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        return posted_at >= cutoff
    except (ValueError, TypeError):
        return False


async def wait_for_run_completion(run_id: str, client: httpx.AsyncClient):
    """Wait for Apify run to finish and return dataset items"""
    # ✅ Fixed: removed accidental space before ACTOR_ID
    status_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}?token={APIFY_TOKEN}"

    while True:
        status_resp = await client.get(status_url)
        status_data = status_resp.json()
        status = status_data["data"]["status"]

        print(f"  Run {run_id} status: {status}")

        if status == "SUCCEEDED":
            break
        elif status in ["FAILED", "ABORTED", "ERROR"]:
            error_msg = status_data["data"].get("exitReason", "Unknown error")
            raise Exception(f"Run {run_id} failed: {error_msg}")

        await asyncio.sleep(3)

    dataset_id = status_data["data"].get("defaultDatasetId")

    if not dataset_id:
        print("  No dataset ID found in run data")
        return []

    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&format=json"
    resp = await client.get(dataset_url)

    if resp.status_code != 200:
        print(f"  Dataset error: {resp.status_code} - {resp.text}")
        return []

    return resp.json()


async def search_indeed(queries: list[dict], max_results_per_query: int = 2):
    # ✅ Fixed: removed accidental space before ACTOR_ID
    api_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"

    async with httpx.AsyncClient(timeout=180.0) as client:
        all_jobs = []
        seen_ids = set()  # For deduplication across queries

        for i, query in enumerate(queries):
            position = query["position"]
            location = query.get("location", "Remote")

            print(f"\nProcessing query {i+1}/{len(queries)}: '{position}' in {location}")

            # ✅ Fixed: "position" is a singular string, not a "positions" array.
            #    Bake "remote" into the search term since remoteJobs param is not supported.
            search_term = f"{position} remote" if query.get("remote") else position

            payload = {
                "position": search_term,   # ✅ singular string, not an array
                "location": location,
                "country": "US",
                "maxItems": max_results_per_query,
            }

            resp = await client.post(api_url, json=payload)

            if resp.status_code != 201:
                print(f"  ❌ POST Error {resp.status_code}: {resp.text}")
                continue

            run_data = resp.json()
            run_id = run_data["data"]["id"]
            print(f"  Started run {run_id}")

            try:
                jobs = await wait_for_run_completion(run_id, client)
            except Exception as e:
                print(f"  ❌ Run failed: {e}")
                continue

            # ── Step 1: Deduplicate ───────────────────────────────────────────
            unique_jobs = []
            for job in jobs:
                job_id = job.get("id") or job.get("url")
                if job_id and job_id not in seen_ids:
                    seen_ids.add(job_id)
                    unique_jobs.append(job)

            # ── Step 2: Filter by time frame ──────────────────────────────────
            recent_jobs = [j for j in unique_jobs if is_within_timeframe(j)]
            stale_count = len(unique_jobs) - len(recent_jobs)

            if stale_count:
                print(f"  ⏩ Skipped {stale_count} job(s) older than {JOB_MAX_AGE_DAYS} days")

            # ── Step 3: Report if nothing matched ─────────────────────────────
            if not recent_jobs:
                print(f"  ⚠️  No jobs posted in the last {JOB_MAX_AGE_DAYS} days for '{position}' in {location}")
            else:
                print(f"  ✓ {len(recent_jobs)} recent unique job(s) found for '{position}'")
                all_jobs.extend(recent_jobs)

        return all_jobs