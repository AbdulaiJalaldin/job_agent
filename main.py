from dataupload.resume_pipeline import ResumeProcessingPipeline
from dataupload.moreinfo import MoreInfo
from dataupload.database import DatabaseService


def main():
    pipeline = ResumeProcessingPipeline()

    try:
        # Check if user data already exists
        existing = pipeline.db.get_existing_user()

        if existing is None:
            # No user data at all → run full pipeline
            print("No existing user found. Processing resume...")
            user_id = pipeline.process_resume("resume.pdf")
            print(f"Resume processed. User ID: {user_id}")
        else:
            user_id = existing["user_id"]
            print(f"Existing user found (ID: {user_id}). Skipping resume processing.")

            if existing["has_additional_info"]:
                # User already has everything filled in
                print("Additional info already saved. Nothing to do.")
                profile = pipeline.db.get_user_profile(user_id)
                print(f"User profile: {profile}")
                return

        # Ask for additional info (runs for both new and existing users without additional info)
        more_info = MoreInfo(user_id)
        extra = more_info.get_more_info()

        pipeline.db.update_user_additional_info(
            user_id=user_id,
            additional_info=extra["info"],
            goals=extra["goals"],
        )
        print("Additional info and goals saved to database.")

    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
