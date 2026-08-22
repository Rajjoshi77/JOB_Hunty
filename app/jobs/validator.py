import re
import hashlib
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup


class JobValidator:
    """Validates, cleans, and sanitizes raw job listings."""

    @staticmethod
    def clean_html(text: str) -> str:
        """Strip HTML tags and excessive whitespace from text."""
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        clean_text = soup.get_text(separator=" ")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        return clean_text

    @staticmethod
    def generate_fingerprint(title: str, company: str, url: str) -> str:
        """Generate a deterministic hash for deduplicating job listings."""
        raw_key = f"{title.lower().strip()}_{company.lower().strip()}_{url.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Verify basic URL validity and ensure it is a direct job application link, not a search query."""
        if not url or not isinstance(url, str):
            return False
        url_clean = url.strip().lower()
        if "google.com/search" in url_clean or "example.com" in url_clean or "bing.com" in url_clean or "yahoo.com" in url_clean:
            return False
        pattern = re.compile(
            r"^(https?:\/\/)"  # http:// or https://
            r"(([a-zA-Z0-9_-]+\.)+[a-zA-Z]{2,})"  # domain
            r"(:\d+)?"  # optional port
            r"(\/.*)?$"  # path
        )
        return bool(pattern.match(url.strip()))

    @classmethod
    def validate_and_sanitize(cls, raw_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate required fields and return sanitized job data dictionary."""
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "").strip()
        url = raw_job.get("url", "").strip()
        description = raw_job.get("description", "")

        # Mandatory checks
        if not title or len(title) < 2:
            return None
        if not company:
            company = "Confidential / Unknown"
        if not cls.is_valid_url(url):
            return None

        clean_description = cls.clean_html(description)
        if len(clean_description) < 20:
            clean_description = f"{title} position at {company}. Apply directly at link."

        # Unique external id
        external_id = raw_job.get("external_id") or cls.generate_fingerprint(title, company, url)

        tags = raw_job.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join([str(t).strip().lower() for t in tags if t])

        return {
            "external_id": str(external_id),
            "title": title[:500],
            "company": company[:255],
            "description": clean_description,
            "url": url[:1000],
            "location": str(raw_job.get("location", "Remote"))[:255],
            "salary": str(raw_job.get("salary", "Not specified"))[:255] if raw_job.get("salary") else "Not specified",
            "experience_level": str(raw_job.get("experience_level", "Mid"))[:100],
            "source": str(raw_job.get("source", "aggregator"))[:100],
            "tags": str(tags),
            "posted_at": raw_job.get("posted_at"),
        }
