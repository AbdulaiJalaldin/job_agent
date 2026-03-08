import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── 1. Fetch profile from your existing postgres DB ──────────────────────────
def fetch_user_profile(user_id: int) -> dict:
    """
    Fetch a user profile from the existing 'users', 'skills', and 'achievements' tables.
    Uses psycopg2 (same as the rest of your codebase) — no asyncpg needed.
    """
    import psycopg2

    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name, email, years_experience, additional_info, goals FROM users WHERE id = %s;",
            (user_id,),
        )
        user = cursor.fetchone()

        if not user:
            raise ValueError(f"No profile found for user_id={user_id}")

        cursor.execute("SELECT skill FROM skills WHERE user_id = %s;", (user_id,))
        skills = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT description FROM achievements WHERE user_id = %s;", (user_id,)
        )
        achievements = [row[0] for row in cursor.fetchall()]

        cursor.close()

    finally:
        conn.close()

    return {
        "name": user[0],
        "email": user[1],
        "years_experience": user[2],
        "additional_info": user[3],
        "goals": user[4],
        "skills": skills,
        "achievements": achievements,
    }


# ── 2. LLM → search queries ─────────────────────────────────────────────────
def generate_search_queries(profile: dict) -> list[dict]:
    prompt = f"""
You are a job-search strategist helping a candidate find relevant REMOTE roles on jobs platforms.

Here is their profile:
{json.dumps(profile, indent=2)}

CRITICAL REQUIREMENTS:
1. Generate only 4 distinct job search queries for REMOTE-ONLY positions
2. ALL queries MUST have "location": "Remote" and "remote": true
3. Vary the job titles creatively — use synonyms, adjacent roles, and skill-based titles
4. Focus on companies that are fully remote or explicitly allow remote work
5. Return ONLY a JSON array, no prose, no markdown fences

Each element must have:
   - "position": the search keyword / job title string
   - "location": MUST be "Remote"
   - "remote": MUST be true

Example output:
[
  {{"position": "AI Engineer", "location": "Remote", "remote": true}},
  {{"position": "LLM Developer", "location": "Remote", "remote": true}},
  {{"position": "Machine Learning Engineer", "location": "Remote", "remote": true}},
  {{"position": "AI Research Scientist", "location": "Remote", "remote": true}}
]
"""
    response = groq_client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    queries = json.loads(raw)
    
    # Additional safety check: force all queries to be remote
    for q in queries:
        q["location"] = "Remote"
        q["remote"] = True
    
    print(f"[QueryGenerator] Generated {len(queries)} REMOTE queries:")
    for q in queries:
        print(f"  → {q['position']} | {q['location']} | remote={q['remote']}")
    return queries