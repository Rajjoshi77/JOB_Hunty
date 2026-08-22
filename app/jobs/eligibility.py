import re
from typing import Tuple, List
from app.database.models import User, Job

# Keywords that indicate experienced / senior roles to filter out for freshers
SENIOR_KEYWORDS = [
    "senior", "sr.", "sr ", "lead", "principal", "staff", "architect",
    "manager", "director", "head of", "team lead", "tech lead", "vp", "chief",
    "engineer 2", "engineer 3", "engineer 4", "engineer 5",
    "engineer ii", "engineer iii", "engineer iv",
    "developer 2", "developer 3", "developer 4",
    "developer ii", "developer iii",
    "sde 2", "sde 3", "sde-2", "sde-3", "sde ii", "sde iii",
    "swe 2", "swe 3", "swe ii", "swe iii", "l3", "l4", "l5", "l6"
]

# Keywords that explicitly welcome freshers and beginners
FRESHER_KEYWORDS = [
    "fresher", "freshers", "entry level", "entry-level", "graduate",
    "junior", "jr.", "jr ", "trainee", "associate", "intern", "internship",
    "0-1 year", "0-2 years", "0 - 1 year", "0 - 2 years", "0 to 1 year",
    "0 to 2 years", "no experience required", "early career", "beginner", "sde 1", "sde-1", "sde i"
]

# Keywords that indicate non-technical / unrelated roles to eliminate
NON_TECH_KEYWORDS = [
    "account executive", "sales representative", "business development", "marketing manager",
    "recruiter", "talent acquisition", "hr generalist", "human resources", "accountant",
    "legal counsel", "content writer", "content reviewer", "customer support", "call center",
    "telecaller", "operations associate", "office administrator", "copywriter", "producer",
    "compliance officer", "reporting officer", "treasury finance", "finance analyst", "sales engineer"
]

# Region markers that restrict hiring to outside India (e.g. US-only or Europe-only remote)
NON_INDIA_RESTRICTED_MARKERS = [
    "us - remote", "remote-us", "remote - us", "remote (us", "us only", "usa only",
    "north america", "remote - americas", "americas", "amer", "europe only", "emea only",
    "remote - emea", "remote (emea", "uk only", "bangkok", "singapore", "nyc", "seattle",
    "japan", "tokyo", "germany", "berlin", "munich", "london", "paris", "sydney", "melbourne",
    "toronto", "vancouver", "dublin", "cork", "ireland", "alberta", "ontario", "quebec",
    "canada", "united states", "usa", "uk", "israel", "spain", "france", "brazil", "mexico",
    "poland", "netherlands", "sweden", "australia", "new zealand", "philippines", "apac", "emea", "latam"
]


class EligibilityChecker:
    """Evaluates strict rules and constraints for user-to-job eligibility."""

    @staticmethod
    def extract_years_required(text: str) -> int:
        """Extract minimum years of experience mentioned in job description."""
        patterns = [
            r"(\d+)\+?\s*(?:-\s*\d+)?\s*(?:years?|yrs?)(?:\s+of)?\s+experience",
            r"(?:at least|minimum|min)\s+(\d+)\s*(?:years?|yrs?)",
            r"experience:\s*(\d+)\+?\s*(?:years?|yrs?)",
            r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|with)",
        ]
        text_lower = text.lower()
        years_found = []
        for pat in patterns:
            matches = re.findall(pat, text_lower)
            for m in matches:
                try:
                    years_found.append(int(m))
                except ValueError:
                    continue

        return min(years_found) if years_found else 0

    @classmethod
    def check_eligibility(cls, user: User, job: Job) -> Tuple[bool, List[str], bool]:
        """
        Check if user passes basic eligibility criteria for the given job.
        Returns (is_eligible, violations, is_fresher_friendly).
        """
        violations = []
        title_lower = (job.title or "").lower()
        loc_lower = (job.location or "").lower()
        desc_lower = (job.description or "").lower()
        tags_lower = (job.tags or "").lower()
        exp_lower = (job.experience_level or "").lower()
        full_text = f"{title_lower} {loc_lower} {tags_lower} {desc_lower}"

        # Detect if explicitly fresher-friendly
        is_fresher_friendly = any(fk in full_text for fk in FRESHER_KEYWORDS)

        # 1. Non-Technical / Irrelevant Role Filter
        if any(nt in title_lower for nt in NON_TECH_KEYWORDS):
            violations.append("Non-technical / unrelated role")

        # 2. Location Restriction Filter (Must be India-accessible: Ahmedabad, Gujarat, Metro India, India, or Worldwide Remote)
        india_city_keywords = ["india", "ahmedabad", "gujarat", "gandhinagar", "surat", "vadodara", "rajkot", "bengaluru", "bangalore", "pune", "hyderabad", "delhi", "mumbai", "noida", "gurgaon", "gurugram", "chennai", "kolkata", "kochi"]
        is_explicit_india = any(re.search(rf"\b{re.escape(iw)}\b", loc_lower) for iw in india_city_keywords)
        is_worldwide_remote = any(rw in loc_lower for rw in ["worldwide", "anywhere", "remote - worldwide", "global"])

        if not is_explicit_india and not is_worldwide_remote:
            for nrm in NON_INDIA_RESTRICTED_MARKERS:
                if nrm in loc_lower:
                    violations.append(f"Region restricted outside India ({nrm.upper()})")
                    break

        # 3. Senior / Experienced Filter for Freshers (Experience <= 1 year)
        if user.experience_years <= 1:
            # Check title for senior tags
            is_senior_title = any(
                re.search(rf"\b{re.escape(sk)}\b", title_lower)
                for sk in SENIOR_KEYWORDS
            )
            if is_senior_title:
                violations.append("Senior/Lead role (Filtered out for Fresher)")

            # Check explicit years of experience required
            req_years = cls.extract_years_required(desc_lower)
            if req_years >= 2:
                violations.append(f"Requires {req_years}+ years experience (Filtered out for Fresher)")
            elif exp_lower in ["senior", "lead", "staff", "architect"]:
                violations.append(f"Requires {exp_lower} experience")

        # 4. Work Mode Check
        user_work_mode = getattr(user, "work_mode", "any") or "any"
        if user_work_mode == "remote" and ("on-site only" in full_text or "must be located in office" in full_text):
            violations.append("Position is strictly on-site (User prefers Remote)")

        is_eligible = len(violations) == 0
        return is_eligible, violations, is_fresher_friendly
