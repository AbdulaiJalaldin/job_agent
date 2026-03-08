import json
from dataupload.resume_pipeline import ResumeProcessingPipeline
from dataupload.moreinfo import MoreInfo
from dataupload.database import DatabaseService
from jobprocessing_pipeline.processing_pipeline_tools.query_generator import fetch_user_profile, generate_search_queries
from jobprocessing_pipeline.processing_pipeline_tools.scrapping_tools.indeed_job_Scraper import search_indeed
import asyncio

async def main():
    pipeline = ResumeProcessingPipeline()

    try:
        # ── Step 1: Ensure user profile exists ────────────────────────────
        existing = pipeline.db.get_existing_user()

        if existing is None:
            print("No existing user found. Processing resume...")
            user_id = pipeline.process_resume("resume.pdf")
            print(f"Resume processed. User ID: {user_id}")
        else:
            user_id = existing["user_id"]
            print(f"Existing user found (ID: {user_id}). Skipping resume processing.")

        # ── Step 2: Ensure additional info exists ─────────────────────────
        if existing and not existing["has_additional_info"]:
            more_info = MoreInfo(user_id)
            extra = more_info.get_more_info()
            pipeline.db.update_user_additional_info(
                user_id=user_id,
                additional_info=extra["info"],
                goals=extra["goals"],
            )
            print("Additional info and goals saved.")

        # ── Step 3: Fetch full profile ────────────────────────────────────
        profile = fetch_user_profile(user_id)
        print("\n" + "=" * 60)
        print("USER PROFILE")
        print("=" * 60)
        for key, value in profile.items():
            print(f"  {key}: {value}")

        # ── Step 4: Generate search queries ───────────────────────────────
        print("\n" + "=" * 60)
        print("GENERATING SEARCH QUERIES...")
        print("=" * 60)
        queries = generate_search_queries(profile)

        print("\nGenerated Queries:")
        for i, q in enumerate(queries, 1):
            print(f"  {i}. Position: {q['position']}")
            print(f"     Location: {q['location']}")
            print(f"     Remote:   {q['remote']}")
            print()

        # ── Step 5: Search Indeed ─────────────────────────────────────────
        print("=" * 60)
        print("SEARCHING INDEED...")
        print("=" * 60)
        jobs = await search_indeed(queries)

        
        print("\n" + "=" * 60)
        print(f"RESULTS: {len(jobs)} jobs found")
        print("=" * 60)

        # DEBUG: Check what the first item looks like
        if jobs:
            print(f"First job type: {type(jobs[0])}")
            print(f"First job content: {jobs[0][:200] if isinstance(jobs[0], str) else jobs[0]}")

        for i, job in enumerate(jobs, 1):
            # Handle if job is a string (JSON string)
            if isinstance(job, str):
                try:
                    job = json.loads(job)
                except json.JSONDecodeError:
                    print(f"\n  [{i}] {job}")  # Just print the string
                    continue
            
            # Now safe to use .get()
            print(f"\n  [{i}] {job.get('positionName', 'N/A')}")
            print(f"      Company:  {job.get('company', 'N/A')}")
            print(f"      Location: {job.get('location', 'N/A')}")
            print(f"      Salary:   {job.get('salary', 'Not listed')}")
            print(f"      Posted:   {job.get('postingDateParsed', 'N/A')}")
            print(f"      URL:      {job.get('url', 'N/A')}")
    finally:
        pipeline.close()


if __name__ == "__main__":
     asyncio.run(main())