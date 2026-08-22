import re
import logging
from typing import Dict, Any, List, Tuple
from app.database.models import User, Job
from app.jobs.eligibility import EligibilityChecker

logger = logging.getLogger(__name__)


class JobMatcher:
    """Calculates compatibility score and generates match insights between User and Job."""

    @staticmethod
    def calculate_skill_overlap(user_skills: List[str], text: str) -> List[str]:
        """Find matching skills in the target text using word boundaries and aliases."""
        matched = set()
        text_lower = text.lower()

        # Skill aliases / normalizations
        skill_aliases = {
            "react.js": ["react", "react.js", "reactjs", "react 19"],
            "react 19": ["react", "react 19", "react.js"],
            "next.js": ["next.js", "nextjs", "next"],
            "node.js": ["node", "node.js", "nodejs"],
            "express.js": ["express", "express.js", "expressjs"],
            "tailwind css": ["tailwind", "tailwindcss"],
            "rest apis": ["rest", "rest api", "restful", "rest apis"],
            "postgresql": ["postgres", "postgresql"],
            "mongodb": ["mongo", "mongodb"],
            "machine learning": ["machine learning", "ml"],
            "generative ai": ["generative ai", "genai", "gen ai"],
            "llms": ["llm", "llms", "large language model"],
            "three.js": ["three.js", "threejs", "three"],
            "react three fiber": ["react three fiber", "r3f"],
        }

        for skill in user_skills:
            if not skill:
                continue
            skill_clean = skill.strip().lower()

            # Check direct name or aliases
            aliases = skill_aliases.get(skill_clean, [skill_clean])
            for alias in aliases:
                escaped = re.escape(alias)
                pattern = rf"(?:\b|_){escaped}(?:\b|_)"
                if re.search(pattern, text_lower):
                    matched.add(skill_clean)
                    break

        return sorted(list(matched))

    @staticmethod
    def evaluate_location_priority(user: User, job: Job) -> Tuple[float, str, str]:
        """
        Evaluate tiered location priority based on user's location tiers.
        Returns (location_score_0_to_100, tier_label, badge).
        """
        job_loc_lower = (job.location or "").lower()
        title_lower = (job.title or "").lower()
        desc_lower = (job.description or "").lower()

        # 1. Highest Priority: Ahmedabad (Priority 100)
        if "ahmedabad" in job_loc_lower or "ahmedabad" in title_lower:
            return 100.0, "Ahmedabad", "🔥 Priority 100"

        # 2. Gujarat Hubs: Gandhinagar, Surat, Vadodara, Rajkot (Priority 95)
        for gj in ["gandhinagar", "surat", "vadodara", "baroda", "rajkot", "gujarat"]:
            if gj in job_loc_lower or gj in title_lower:
                return 95.0, f"Gujarat ({gj.title()})", "🔥 Priority 95"

        # 3. Remote India (Priority 90)
        if ("remote" in job_loc_lower or "anywhere" in job_loc_lower or "worldwide" in job_loc_lower) and "india" in job_loc_lower:
            return 90.0, "Remote India", "🟢 Priority 90"

        # 4. Major Tech Hubs: Bengaluru, Pune, Hyderabad (Priority 85)
        for hub in ["bengaluru", "bangalore", "hyderabad", "pune"]:
            if hub in job_loc_lower:
                return 85.0, f"Major Hub ({hub.title()})", "🟢 Priority 85"

        # 5. Remote Worldwide / Flexible Remote (Priority 80)
        if "remote" in job_loc_lower or "anywhere" in job_loc_lower or "worldwide" in job_loc_lower or "home based" in job_loc_lower or "wfh" in job_loc_lower:
            return 80.0, "Remote Worldwide", "🟢 Remote 80"

        # 6. Metro India: Delhi NCR, Mumbai, Noida, Gurgaon, Chennai, Kolkata (Priority 70)
        for metro in ["mumbai", "delhi", "noida", "gurgaon", "gurugram", "chennai", "kolkata", "kochi"]:
            if metro in job_loc_lower:
                return 70.0, f"Metro India ({metro.title()})", "🟡 Priority 70"

        # 7. Other India (Priority 50)
        if "india" in job_loc_lower:
            return 50.0, "India", "🟡 Priority 50"

        return 30.0, job.location or "Global", "📍 Other"

    @classmethod
    def match(cls, user: User, job: Job) -> Dict[str, Any]:
        """
        Evaluate compatibility between candidate and job listing.
        Returns dictionary with match_score (0-100), reasons, and location badge.
        """
        # 1. Strict Eligibility & Fresher Check
        is_eligible, violations, is_fresher_friendly = EligibilityChecker.check_eligibility(user, job)

        # If user is fresher / entry-level and job strictly requires senior/experienced profile, eliminate it
        if user.experience_years <= 1 and not is_eligible:
            return {
                "score": 0.0,
                "reasons": f"🚫 Disqualified: {'; '.join(violations)}",
                "matched_skills": [],
                "location_label": job.location,
                "location_badge": "❌ Experienced Role",
                "is_eligible": False,
            }

        user_skills = user.get_skills_list()
        user_roles = user.get_roles_list()
        searchable_text = f"{job.title} {job.tags} {job.description}"

        # 2. Skill Scoring (Weight: 40%)
        matched_skills = cls.calculate_skill_overlap(user_skills, searchable_text)
        if user_skills:
            overlap_ratio = min(1.0, len(matched_skills) / max(3, len(user_skills) * 0.15))
            skill_score = overlap_ratio * 40.0
        else:
            skill_score = 25.0

        # 3. Role Title Alignment (Weight: 30%)
        role_score = 0.0
        matched_roles = []
        job_title_lower = job.title.lower()

        for role in user_roles:
            if role in job_title_lower or role in job.tags.lower():
                matched_roles.append(role)

        if matched_roles:
            role_score = 30.0
        else:
            title_words = set(job_title_lower.split())
            for role in user_roles:
                role_words = set(role.split())
                if role_words.intersection(title_words):
                    role_score = 20.0
                    matched_roles.append(role)
                    break

        # Fresher boost
        if is_fresher_friendly and user.experience_years <= 1:
            role_score = min(30.0, role_score + 8.0)

        # 4. Tiered Location Scoring (Weight: 30%)
        loc_raw_score, loc_label, loc_badge = cls.evaluate_location_priority(user, job)
        loc_score = (loc_raw_score / 100.0) * 30.0

        total_score = min(100.0, round(skill_score + role_score + loc_score, 1))

        # Construct clear breakdown
        reasons = []
        if is_fresher_friendly:
            reasons.append("🌱 Fresher / Beginner Friendly")
        if matched_roles:
            reasons.append(f"🎯 Role: {matched_roles[0].title()}")
        if matched_skills:
            top_skills = matched_skills[:5]
            reasons.append(f"💻 Stack: {', '.join(top_skills)}")
        reasons.append(f"📍 {loc_badge} ({loc_label})")

        match_explanation = " | ".join(reasons) if reasons else "Beginner Level Match"

        return {
            "score": total_score,
            "reasons": match_explanation,
            "matched_skills": matched_skills,
            "location_label": loc_label,
            "location_badge": loc_badge,
            "is_eligible": True,
        }
