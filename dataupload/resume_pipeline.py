from dataupload.resumeUpload import HandleResumeUpload
from dataupload.resumevectorstore import vectorservice
from dataupload.database import DatabaseService
from dataupload.resumeInfoextraction import extract_structured_data


class ResumeProcessingPipeline:
    def __init__(self):
        self.chunker = HandleResumeUpload()
        self.vector_service = vectorservice()
        self.db = DatabaseService()

    def process_resume(self, file_path: str) -> int:

        # 1️⃣ Read full raw text
        raw_text = self.chunker._read_pdf(file_path)

        # 2️⃣ Extract structured info via LLM (returns a Pydantic ResumeData model)
        structured = extract_structured_data(raw_text)

        # 3️⃣ Store structured info in PostgreSQL
        #    Pydantic guarantees these fields exist with safe defaults:
        #    - years_experience → None if missing  → NULL in DB
        #    - achievements     → []   if missing  → no rows inserted
        user_id = self.db.store_user_profile(
            name=structured.name,
            email=structured.email,
            years_experience=structured.years_experience,
            skills=structured.skills,
            achievements=structured.achievements,
        )

        # 4️⃣ Chunk full resume and store in Pinecone
        chunks = self.chunker.process_file(file_path)

        self.vector_service.upload_chunks(
            chunks=chunks,
            namespace=str(user_id),
        )

        return user_id

    def close(self):
        """Clean up database connection."""
        self.db.close()