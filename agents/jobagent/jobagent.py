"""
Job Agent — an AI agent that finds the best jobs for a user.

Uses Groq's tool-calling to orchestrate tools in parallel.
Currently has:
  - generate_queries: generates search queries from user profile
  - search_indeed: scrapes Indeed for matching jobs

More tools can be added to TOOL_REGISTRY — the agent will discover
and call them automatically (including in parallel).
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

from jobprocessing_pipeline.processing_pipeline_tools.query_generator import fetch_user_profile, generate_search_queries
from agents.jobagent.jobagent_tools.indeed_adapter_tool import search_indeed

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


# ── Tool Definitions (for Groq's tool-calling API) ───────────────────────────
# Each tool has a schema that tells the LLM what it does and what args it expects.
# To add a new tool: add its schema here + its function in TOOL_FUNCTIONS below.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_queries",
            "description": (
                "Generate job search queries based on the user's profile. "
                "Analyzes skills, experience, goals, and preferences to create "
                "diverse search queries for job platforms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's database ID to fetch their profile.",
                    }
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_indeed",
            "description": (
                "Search Indeed for job listings matching the given queries. "
                "Each query should have a position, location, and remote flag. "
                "Returns a list of job postings with titles, companies, descriptions, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "position": {"type": "string", "description": "Job title or search keyword"},
                                "location": {"type": "string", "description": "City, region, or 'Remote'"},
                                "remote":   {"type": "boolean", "description": "Whether to filter for remote jobs"},
                            },
                            "required": ["position", "location", "remote"],
                        },
                        "description": "List of search queries to run on Indeed.",
                    }
                },
                "required": ["queries"],
            },
        },
    },
    # ── Add more tools here as you build them ──
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "search_linkedin",
    #         "description": "Search LinkedIn for job listings...",
    #         "parameters": { ... },
    #     },
    # },
]

# Maps tool names → actual Python functions
TOOL_FUNCTIONS = {
    "generate_queries": lambda user_id: generate_search_queries(
        fetch_user_profile(user_id)
    ),
    "search_indeed": lambda queries: search_indeed(queries),
    # ── Add more tool functions here ──
    # "search_linkedin": lambda queries: search_linkedin(queries),
}


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are JobAgent, an intelligent job-hunting assistant.

Your mission: Find the best job opportunities for the user by using the tools available to you.

## How you work:
1. FIRST, call `generate_queries` with the user's ID to create tailored search queries based on their profile (skills, experience, goals).
2. THEN, call `search_indeed` with those queries to find matching jobs. When more job platform tools become available, call ALL platform tools IN PARALLEL to maximize coverage.
3. FINALLY, analyze the results and present a curated summary of the best opportunities, explaining WHY each job is a good fit for this specific user.

## Rules:
- Always start by generating queries — never guess what to search for.
- When multiple search tools are available, call them ALL at the same time (parallel tool calls) for speed.
- Rank results by relevance to the user's profile, skills, and goals.
- Highlight key details: company, title, location, salary (if available), and why it's a match.
- If no good results are found, suggest adjustments to the search strategy.
- Be concise but informative. The user wants actionable results, not fluff.
"""


# ── Agent Loop ────────────────────────────────────────────────────────────────
def _execute_tool_calls(tool_calls: list) -> list[dict]:
    """
    Execute all tool calls (potentially in parallel if the LLM requested multiple).
    Returns the results formatted for the next LLM message.
    """
    results = []

    for tool_call in tool_calls:
        fn_name = tool_call.function.name
        fn_args = json.loads(tool_call.function.arguments)

        print(f"\n[JobAgent] Calling tool: {fn_name}({fn_args})")

        if fn_name not in TOOL_FUNCTIONS:
            result = {"error": f"Unknown tool: {fn_name}"}
        else:
            try:
                result = TOOL_FUNCTIONS[fn_name](**fn_args)
            except Exception as e:
                result = {"error": str(e)}

        results.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, default=str),
        })

    return results


def run_job_agent(user_id: int) -> str:
    """
    Run the job agent for a given user.

    The agent will:
    1. Generate search queries from the user's profile
    2. Search Indeed (and future platforms) in parallel
    3. Return a curated analysis of the best jobs

    Args:
        user_id: The user's database ID

    Returns:
        The agent's final response with job recommendations
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Find the best jobs for user ID {user_id}. Start by generating search queries from their profile, then search all available job platforms.",
        },
    ]

    print("=" * 60)
    print(f"[JobAgent] Starting job search for user {user_id}")
    print("=" * 60)

    # Agent loop — keeps going until the LLM gives a final text response
    while True:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",  # Let the model decide when/which tools to call
        )

        message = response.choices[0].message

        # If the model wants to call tools → execute them and loop back
        if message.tool_calls:
            # Append the assistant message with tool calls
            messages.append(message)

            print(f"\n[JobAgent] LLM requested {len(message.tool_calls)} tool call(s)")

            # Execute all requested tools (parallel calls from LLM are handled here)
            tool_results = _execute_tool_calls(message.tool_calls)

            # Add all tool results to the conversation
            messages.extend(tool_results)

            # Continue the loop — the LLM will see the results and decide next step
            continue

        # No tool calls → the model is done, return its final answer
        final_response = message.content
        print(f"\n{'=' * 60}")
        print("[JobAgent] Complete!")
        print(f"{'=' * 60}")
        return final_response