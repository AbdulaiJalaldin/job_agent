import instructor
from groq import Groq
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

# Patch the Groq client with instructor for structured output
client = instructor.from_groq(
    Groq(api_key=os.getenv("GROQ_API_KEY")),
    mode=instructor.Mode.JSON,
)


class ResumeData(BaseModel):
    """Structured resume data extracted by the LLM."""
    name: str
    email: str
    years_experience: Optional[int] = None
    skills: List[str] = []
    achievements: List[str] = []


def extract_structured_data(full_text: str) -> ResumeData:
    """
    Extract structured resume info using instructor + Pydantic.
    Missing fields like achievements or years_experience will
    default to None / empty list — never a KeyError.
    """
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        response_model=ResumeData,
        messages=[
            {
                "role": "user",
                "content": f"""
                    Extract the following from this resume:
                    - name (string)
                    - email (string)
                    - years_experience (integer or null if not mentioned)
                    - skills (list of strings)
                    - achievements (list of measurable accomplishments, or empty list if none)

                    Resume:
                    {full_text}
                """,
            }
        ],
    )

    return response