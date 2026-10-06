import re
from typing import List

from schema import JobRecord


SYNONYMS = {
    "openai": "openai api",
    "chatgpt": "openai api",
    "gpt": "openai api",
    "chatgpt api": "openai api",

    "claude": "claude api",
    "anthropic": "claude api",

    "js": "javascript",
    "node": "node.js",
    "nodejs": "node.js",

    "postgres": "postgresql",

    "make": "make.com",

    "web scraping": "scraping",
    "scrapers": "scraping",
}


VAGUE_SKILLS = {
    "ai",
    "ai development",
    "ai chatbot",
    "chatbot",
    "automation",
    "development",
    "programming",
    "software development",
    "full-stack",
    "api",
    "api integration",
}


def clean_text(value):

    if value is None:
        return None

    value = str(value)

    value = re.sub(r"\s+", " ", value)

    value = value.strip()

    return value


def clean_skills(skills):

    cleaned = []

    for skill in skills:

        skill = clean_text(skill)

        if not skill:
            continue

        skill = skill.lower()

        skill = SYNONYMS.get(skill, skill)

        if skill in VAGUE_SKILLS:
            continue

        if skill not in cleaned:
            cleaned.append(skill)

    return cleaned


def clean_job(job: JobRecord) -> JobRecord:

    job.title = clean_text(job.title)

    job.client_problem = clean_text(
        job.client_problem
    )

    job.source_snippet = clean_text(
        job.source_snippet
    )

    job.posted_ago = clean_text(
        job.posted_ago
    )

    job.skills = clean_skills(
        job.skills
    )

    return job


def duplicate_key(job: JobRecord):

    title = clean_text(job.title).lower()

    snippet = clean_text(
        job.source_snippet
    ).lower()

    snippet = " ".join(
        re.sub(r"\W+", " ", snippet).split()[:5]
    )

    return title + "|" + snippet


def clean_jobs(
    jobs: List[JobRecord]
) -> List[JobRecord]:

    cleaned_jobs = []

    seen = set()

    for job in jobs:

        job = clean_job(job)

        key = duplicate_key(job)

        if key in seen:
            continue

        seen.add(key)

        cleaned_jobs.append(job)

    return cleaned_jobs