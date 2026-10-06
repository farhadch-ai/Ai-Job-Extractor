import os
import json
import time

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from schema import JobRecord


# --------------------------------------------------
# 1. OpenAI setup
# --------------------------------------------------

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MODEL = "gpt-4o-mini"

MAX_TRIES = 3

CHUNK_SIZE = 14000
OVERLAP = 6000


# --------------------------------------------------
# 2. Give the AI our Pydantic schema
# --------------------------------------------------

ITEM_SCHEMA = json.dumps(
    JobRecord.model_json_schema(),
    indent=2
)


# --------------------------------------------------
# 3. Instructions for the AI
# --------------------------------------------------

SYSTEM = f"""
You will receive a slice of a text file containing
one or more freelance job posts.

Extract EVERY complete job post in the text.

Return ONLY a JSON object in this format:

{{
    "jobs": [
        ...
    ]
}}

Each job must match this JSON schema:

{ITEM_SCHEMA}

Rules:

- Extract every complete job post.
- Do not merge two different job posts.
- Do not skip complete job posts.
- The text may be a slice of a larger file.
- If a job begins before the current slice and its beginning
  is cut off, skip that job.
- Use null for anything not stated.
- Never guess.
- title must be copied exactly as written.
- source_snippet must be the first 8 to 10 words of the
  job title or description, copied exactly.
- Never use a line about pay, hourly rate, experience level,
  or estimated time as the source_snippet.
- budget_min and budget_max must contain numbers only.
- For "$10-25/hr", use budget_min=10 and budget_max=25.
- For "$500", use budget_min=500 and budget_max=500.
- For "up to $500", use budget_min=null and budget_max=500.
- If pay is negotiable, open, flexible, or to be discussed
  with no number, set budget_negotiable=true.
- Copy posted_ago exactly as written.
- Use the allowed values for project_type, budget_type,
  and experience_level exactly.
- If there are no complete jobs, return:
  {{"jobs": []}}
- Output JSON only.
"""


# --------------------------------------------------
# 4. Split large text into overlapping chunks
# --------------------------------------------------

def chunk_text(text):
    chunks = []

    step = CHUNK_SIZE - OVERLAP

    start = 0

    while start < len(text):

        chunk = text[start:start + CHUNK_SIZE]

        chunks.append(chunk)

        if start + CHUNK_SIZE >= len(text):
            break

        start += step

    return chunks


# --------------------------------------------------
# 5. Call OpenAI
# --------------------------------------------------

def call_model(messages):

    for attempt in range(MAX_TRIES):

        try:

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0,
                response_format={
                    "type": "json_object"
                }
            )

            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = input_tokens + output_tokens

            raw = response.choices[0].message.content

            return raw, input_tokens, output_tokens, total_tokens

        except Exception as e:

            if attempt == MAX_TRIES - 1:
                raise RuntimeError(
                    "The AI service could not process the request."
                ) from e

            time.sleep(2 ** attempt)


# --------------------------------------------------
# 6. Extract jobs from ONE chunk
# --------------------------------------------------

def extract_chunk(chunk):

    messages = [
        {
            "role": "system",
            "content": SYSTEM
        },
        {
            "role": "user",
            "content": chunk
        }
    ]

    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    for attempt in range(MAX_TRIES):

        try:

            raw, input_tokens, output_tokens, tokens = (
                call_model(messages)
            )

            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_tokens += tokens

            data = json.loads(raw)

            items = data.get("jobs", [])

            validated_jobs = []

            errors = []

            for index, item in enumerate(items):

                try:

                    job = JobRecord.model_validate(item)

                    validated_jobs.append(job)

                except ValidationError as e:

                    errors.append(
                        f"Job {index}: {e}"
                    )

            # If validation failed, ask AI to correct everything
            if errors:

                messages.extend(
                    [
                        {
                            "role": "assistant",
                            "content": raw
                        },
                        {
                            "role": "user",
                            "content":
                                'Some jobs failed validation. '
                                'Return the complete corrected '
                                '{"jobs": [...]} list, including '
                                'the valid jobs.\n\n'
                                + "\n".join(errors)
                        }
                    ]
                )

                continue

            return {
                "jobs": validated_jobs,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
            }

        except json.JSONDecodeError:

            if attempt == MAX_TRIES - 1:

                raise RuntimeError(
                    "The AI returned invalid JSON."
                )

        except Exception:

            if attempt == MAX_TRIES - 1:

                raise RuntimeError(
                    "The job extraction failed."
                )


    raise RuntimeError(
        "The job extraction failed after several attempts."
    )


# --------------------------------------------------
# 7. Extract ALL jobs from the input text
# --------------------------------------------------

def extract_jobs(text):

    chunks = chunk_text(text)

    all_jobs = []

    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    for number, chunk in enumerate(
        chunks,
        start=1
    ):

        result = extract_chunk(chunk)

        jobs = result["jobs"]

        # ------------------------------------------
        # Verify source snippets
        # ------------------------------------------

        chunk_normalized = " ".join(
            chunk.lower().split()
        )

        verified_jobs = []

        for job in jobs:

            snippet = " ".join(
                job.source_snippet.lower().split()
            )

            if snippet in chunk_normalized:

                verified_jobs.append(job)

        # ------------------------------------------
        # Add jobs
        # ------------------------------------------

        all_jobs.extend(verified_jobs)

        # ------------------------------------------
        # Add token usage
        # ------------------------------------------

        total_input_tokens += result["input_tokens"]
        total_output_tokens += result["output_tokens"]
        total_tokens += result["total_tokens"]

    return {
        "jobs": all_jobs,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
    }