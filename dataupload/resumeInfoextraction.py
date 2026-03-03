import json
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
)

def extract_structured_data(full_text: str) -> dict:
    prompt = f"""
    Extract the following from this resume:
    - name
    - email
    - years_experience (integer)
    - skills (list)
    - achievements (list of measurable accomplishments)

    Return strictly valid JSON.

    Resume:
    {full_text}
    """

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content
    return json.loads(content)