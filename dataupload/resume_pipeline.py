from resumeUpload import HandleResumeUpload
from vectorservice import vectorservice
from database_service import DatabaseService
from resume_extractor import extract_structured_data
from your_state_file import UserIdentityState


class ResumeProcessingPipeline:
    def __init__(self):
        self.chunker = HandleResumeUpload()
        self.vector_service = vectorservice()
        self.db = DatabaseService()

    def process_resume(self, file_path: str) -> int:

        # 1️⃣ Read full raw text
        raw_text = self.chunker._read_pdf(file_path)

        # 2️⃣ Extract structured info via LLM
        structured = extract_structured_data(raw_text)

        # 3️⃣ Store structured info in PostgreSQL
        user_id = self.db.store_user_profile(
            name=structured["name"],
            email=structured["email"],
            years_experience=structured["years_experience"],
            skills=structured["skills"],
            achievements=structured["achievements"],
        )

        # 4️⃣ Chunk full resume and store in Pinecone
        chunks = self.chunker.process_file(file_path)

        self.vector_service.upload_chunks(
            chunks=chunks,
            namespace=str(user_id),
        )

        return user_id