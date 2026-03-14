import json
from dataupload.resume_pipeline import ResumeProcessingPipeline
from dataupload.moreinfo import MoreInfo
from dataupload.database import DatabaseService
from jobprocessing_pipeline.processing_pipeline_tools.query_generator import fetch_user_profile, generate_search_queries
from jobprocessing_pipeline.processing_pipeline_tools.scrapping_tools.google_jobs_scrapper import search_google_jobs_sync
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

            # ── Step 5: Search Google Jobs ────────────────────────────────────
    
        print("=" * 60)
        print("SEARCHING GOOGLE JOBS...")
        print("=" * 60)
        jobs = search_google_jobs_sync(queries, max_results_per_query=2)
        
        print("\n" + "=" * 60)
        print(f"RESULTS: {len(jobs)} jobs found")
        print("=" * 60)

        for i, job in enumerate(jobs, 1):
            print(f"  [{i}] {job.get('title', 'N/A')}")
            print(f"      Company:    {job.get('company_name', 'N/A')}")
            print(f"      Location:   {job.get('location', 'N/A')}")
            print(f"      Via:        {job.get('via', 'N/A')}")
            
            # Salary from detected_extensions
            salary = job.get('detected_extensions', {}).get('salary', 'Not listed')
            print(f"      Salary:     {salary}")
            
            # Posted date (prioritize detected, fallback to extensions)
            posted = (
                job.get('detected_extensions', {}).get('posted_at') or
                job.get('detected_extensions', {}).get('posted') or
                job.get('extensions', [{}])[0] if job.get('extensions') else 'N/A'
            )
            print(f"      Posted:     {posted}")
            print(f"      URL:        {job.get('link', job.get('job_apply_link', 'N/A'))}")
            
            desc = job.get('description', 'No description available')
            desc_preview = desc[:400] + '...' if len(desc) > 400 else desc
            print(f"      Description:\n{desc_preview}\n")
            print("-" * 80)
    finally:
        pipeline.close()


if __name__ == "__main__":
     asyncio.run(main())