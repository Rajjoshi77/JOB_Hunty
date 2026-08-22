import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx

from app.jobs.validator import JobValidator
from app.database.database import get_session
from app.database.models import Job
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 JobHunterBot/1.0"
}

# 100% FREE Direct Company ATS Boards (Zero Fees, Zero Intermediaries, Direct Employer HR Systems)
DIRECT_COMPANY_GREENHOUSE_BOARDS = [
    ("postman", "Postman"),
    ("gitlab", "GitLab"),
    ("hackerrank", "HackerRank"),
    ("inmobi", "InMobi"),
    ("canonical", "Canonical (Ubuntu)"),
    ("razorpaysoftwareprivatelimited", "Razorpay"),
    ("elastic", "Elastic"),
    ("mongodb", "MongoDB"),
    ("cloudflare", "Cloudflare"),
    ("stripe", "Stripe"),
    ("datadog", "Datadog"),
    ("figma", "Figma"),
    ("sentry", "Sentry"),
    ("posthog", "PostHog"),
    ("supabase", "Supabase"),
    ("airmeet", "Airmeet"),
]

# 100% FREE Direct Company Lever ATS Boards (Zero Fees, Direct Employer HR Systems)
DIRECT_COMPANY_LEVER_BOARDS = [
    ("cred", "CRED"),
]


class JobCollector:
    """Collects ONLY 100% FREE, DIRECT COMPANY ATS job vacancies (Greenhouse & Lever) with zero paywalls."""

    @classmethod
    async def fetch_greenhouse_company_jobs(cls, company_slug: str, company_name: str) -> List[Dict[str, Any]]:
        """Fetch active live jobs from official Greenhouse ATS with direct free application forms."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
        jobs = []
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("jobs", [])
                    for item in data:
                        job_title = item.get("title", "")
                        raw_url = item.get("absolute_url", "")
                        location = (item.get("location") or {}).get("name") or "Remote / India"

                        if not raw_url:
                            continue

                        # Ensure direct link lands on the live job application form with no paywall
                        direct_url = raw_url if raw_url.endswith("#app") else f"{raw_url}#app"

                        title_lower = job_title.lower()
                        is_tech = any(kw in title_lower for kw in [
                            "engineer", "developer", "software", "frontend", "backend",
                            "full stack", "fullstack", "react", "python", "ai", "ml",
                            "associate", "junior", "trainee", "fresher", "intern", "web",
                            "data", "qa", "mobile"
                        ])

                        if not is_tech:
                            continue

                        jobs.append({
                            "external_id": f"gh_{company_slug}_{item.get('id')}",
                            "title": job_title,
                            "company": company_name,
                            "description": f"Direct career opening at {company_name} ({location}). 100% Free official application directly on {company_name}'s Greenhouse ATS.",
                            "url": direct_url,
                            "location": location,
                            "salary": "Competitive (Company Standard)",
                            "experience_level": "Fresher / Entry / Mid",
                            "source": f"{company_name} Official ATS (100% Free)",
                            "tags": [company_slug, "greenhouse-ats", "direct-company", "free-apply"],
                            "posted_at": datetime.utcnow(),
                        })
        except Exception as e:
            logger.debug(f"Greenhouse fetch skipped for {company_slug}: {e}")
        return jobs

    @classmethod
    async def fetch_lever_company_jobs(cls, company_slug: str, company_name: str) -> List[Dict[str, Any]]:
        """Fetch active live jobs from official Lever ATS with direct free application forms."""
        url = f"https://api.lever.co/v0/postings/{company_slug}"
        jobs = []
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data:
                        job_title = item.get("text", "")
                        raw_url = item.get("hostedUrl", "") or item.get("applyUrl", "")
                        categories = item.get("categories", {})
                        location = categories.get("location") or "India / Remote"

                        if not raw_url:
                            continue

                        # Direct application form
                        direct_url = raw_url if "/apply" in raw_url else f"{raw_url.rstrip('/')}/apply"

                        title_lower = job_title.lower()
                        is_tech = any(kw in title_lower for kw in [
                            "engineer", "developer", "software", "frontend", "backend",
                            "full stack", "fullstack", "react", "python", "ai", "ml",
                            "associate", "junior", "trainee", "fresher", "intern", "web"
                        ])

                        if not is_tech:
                            continue

                        jobs.append({
                            "external_id": f"lever_{company_slug}_{item.get('id')}",
                            "title": job_title,
                            "company": company_name,
                            "description": f"Direct career opening at {company_name} ({location}). 100% Free official application directly on {company_name}'s Lever ATS.",
                            "url": direct_url,
                            "location": location,
                            "salary": "Competitive",
                            "experience_level": "Fresher / Entry / Mid",
                            "source": f"{company_name} Official ATS (100% Free)",
                            "tags": [company_slug, "lever-ats", "direct-company", "free-apply"],
                            "posted_at": datetime.utcnow(),
                        })
        except Exception as e:
            logger.debug(f"Lever fetch skipped for {company_slug}: {e}")
        return jobs

    @classmethod
    async def collect_and_store_jobs(cls) -> int:
        """Fetch strictly from 100% FREE, DIRECT COMPANY ATS systems (Greenhouse & Lever). No third-party paywalls."""
        logger.info("Starting 100% free direct company ATS aggregation pipeline (Greenhouse & Lever)...")

        # Purge any third-party paywalled job aggregators from database
        async with get_session() as session:
            await session.execute(delete(Job).where(Job.url.like("%jobicy%")))
            await session.execute(delete(Job).where(Job.url.like("%remoteok%")))
            await session.execute(delete(Job).where(Job.url.like("%weworkremotely%")))
            await session.execute(delete(Job).where(Job.url.like("%example.com%")))
            await session.execute(delete(Job).where(Job.url.like("%google.com/search%")))
            await session.commit()

        # Build async tasks for direct company ATS boards only
        tasks = []
        for slug, name in DIRECT_COMPANY_GREENHOUSE_BOARDS:
            tasks.append(cls.fetch_greenhouse_company_jobs(slug, name))
        for slug, name in DIRECT_COMPANY_LEVER_BOARDS:
            tasks.append(cls.fetch_lever_company_jobs(slug, name))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_raw_jobs: List[Dict[str, Any]] = []
        for res in results:
            if isinstance(res, list):
                all_raw_jobs.extend(res)

        new_jobs_count = 0
        async with get_session() as session:
            for raw_job in all_raw_jobs:
                sanitized = JobValidator.validate_and_sanitize(raw_job)
                if not sanitized:
                    continue

                existing = await session.execute(
                    select(Job).where(Job.external_id == sanitized["external_id"])
                )
                if existing.scalar_one_or_none():
                    continue

                job_obj = Job(
                    external_id=sanitized["external_id"],
                    title=sanitized["title"],
                    company=sanitized["company"],
                    description=sanitized["description"],
                    url=sanitized["url"],
                    location=sanitized["location"],
                    salary=sanitized["salary"],
                    experience_level=sanitized["experience_level"],
                    source=sanitized["source"],
                    tags=sanitized["tags"],
                    posted_at=sanitized.get("posted_at") or datetime.utcnow(),
                    is_active=True,
                )
                session.add(job_obj)
                new_jobs_count += 1

        logger.info(f"Direct company ATS collection complete. Stored {new_jobs_count} 100% free direct positions.")
        return new_jobs_count
