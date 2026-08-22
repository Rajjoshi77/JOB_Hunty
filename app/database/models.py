import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Default Tech Stack Profile
DEFAULT_SKILLS = (
    "JavaScript, TypeScript, Python, Java, React.js, React 19, Next.js, HTML5, CSS3, Tailwind CSS, "
    "React Hooks, Node.js, Express.js, REST APIs, Django, Flask, MongoDB, PostgreSQL, SQL, "
    "Machine Learning, Predictive Analytics, Pandas, NumPy, Scikit-learn, Generative AI, LLMs, "
    "RAG, Git, GitHub, Docker, Postman, Vercel, WebRTC, Prisma, Three.js, React Three Fiber, GSAP, Framer Motion"
)

# Default Prioritized Roles & Fresher/Junior Variants
DEFAULT_ROLES = (
    "Software Developer, Software Engineer, Full Stack Developer, MERN Stack Developer, "
    "Frontend Developer, React.js Developer, Node.js Developer, Web Developer, Full Stack Engineer, "
    "AI Engineer, AI/ML Engineer, Machine Learning Engineer, Junior ML Engineer, AI Developer, "
    "Generative AI Engineer, Junior Data Scientist, Software Engineer - Fresher, "
    "Graduate Software Engineer, Junior Software Engineer, Associate Software Engineer, "
    "Trainee Software Engineer, Software Developer - Fresher, Full Stack Developer - Fresher, "
    "React Developer - Fresher, MERN Developer - Fresher, Junior AI Engineer"
)

# Tiered Locations & Priorities
DEFAULT_LOCATION_TIERS = json.dumps({
    "100": ["ahmedabad"],
    "95": ["gujarat", "gandhinagar", "surat", "vadodara", "rajkot"],
    "90": ["remote india", "remote - india", "india (remote)", "remote", "anywhere"],
    "85": ["bengaluru", "bangalore", "hyderabad", "pune"],
    "70": ["mumbai", "delhi", "noida", "gurugram", "gurgaon", "chennai", "kolkata", "kochi", "india"],
    "50": ["other india", "indore", "jaipur", "chandigarh"]
})


class User(Base):
    """Telegram User profile and dynamic search preferences."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)

    # Dynamic preferences & Tech Stack
    skills = Column(Text, default=DEFAULT_SKILLS, nullable=False)
    preferred_roles = Column(Text, default=DEFAULT_ROLES, nullable=False)
    location_tiers = Column(Text, default=DEFAULT_LOCATION_TIERS, nullable=False)
    location_preference = Column(String(255), default="Ahmedabad / Gujarat / Remote India", nullable=False)
    work_mode = Column(String(100), default="Any (Remote, Hybrid, On-site)", nullable=False)
    experience_years = Column(Integer, default=0, nullable=False)  # 0 for Fresher / Junior
    min_salary = Column(Integer, default=0, nullable=False)

    # Subscription settings
    is_subscribed = Column(Boolean, default=True, nullable=False)
    last_digest_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    matches = relationship("JobMatch", back_populates="user", cascade="all, delete-orphan")

    def get_skills_list(self) -> List[str]:
        if not self.skills:
            return []
        return [s.strip().lower() for s in self.skills.split(",") if s.strip()]

    def get_roles_list(self) -> List[str]:
        if not self.preferred_roles:
            return []
        return [r.strip().lower() for r in self.preferred_roles.split(",") if r.strip()]

    def get_location_tiers_dict(self) -> Dict[str, List[str]]:
        try:
            return json.loads(self.location_tiers)
        except Exception:
            return json.loads(DEFAULT_LOCATION_TIERS)



class Job(Base):
    """Scraped and validated job listing."""

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    url = Column(String(1000), nullable=False)
    location = Column(String(255), default="Remote", nullable=False)
    salary = Column(String(255), nullable=True)
    experience_level = Column(String(100), default="Any", nullable=False)
    source = Column(String(100), default="aggregator", nullable=False)
    tags = Column(Text, default="", nullable=False)  # Comma-separated tags
    is_active = Column(Boolean, default=True, nullable=False)
    posted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_title_company", "title", "company"),
    )


class JobMatch(Base):
    """Relationship between a User and a Job listing with compatibility scoring."""

    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    match_score = Column(Float, default=0.0, nullable=False)  # Percentage score (0 - 100)
    match_reasons = Column(Text, default="", nullable=False)  # Summary of why matched

    is_notified = Column(Boolean, default=False, nullable=False)
    is_saved = Column(Boolean, default=False, nullable=False)
    is_applied = Column(Boolean, default=False, nullable=False)
    is_dismissed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="matches")
    job = relationship("Job", back_populates="matches")

    __table_args__ = (
        Index("ix_user_job_unique", "user_id", "job_id", unique=True),
    )
