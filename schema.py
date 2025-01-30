from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Table, Enum, DateTime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum

Base = declarative_base()

# ---- Enums for Standardization ----
class LocationType(PyEnum):
    REMOTE = "Remote"
    HYBRID = "Hybrid"
    ON_SITE = "On-site"

class SkillLevel(PyEnum):
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4

class CareerPreference(PyEnum):
    UPWARD_MOBILITY = "Upward Mobility"
    LATERAL_MOVE = "Lateral Move"
    CAREER_CHANGE = "Career Change"

class Availability(PyEnum):
    IMMEDIATE = "Immediate"
    WITHIN_1_MONTH = "Within 1 Month"
    WITHIN_3_MONTHS = "Within 3 Months"

# ---- Core Tables ----
class Skill(Base):
    __tablename__ = 'skills'
    id = Column(Integer, primary_key=True)
    skill_type = Column(String(50))  # e.g., "Programming"
    skill_group = Column(String(50))  # e.g., "Python"
    skill_level = Column(Enum(SkillLevel))  # e.g., SkillLevel.ADVANCED

class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    required_experience = Column(Integer)  # Years
    location_type = Column(Enum(LocationType))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    availability = Column(Enum(Availability))
    career_preference = Column(Enum(CareerPreference))
    skills = relationship('Skill', secondary='job_skills')
    created_at = Column(DateTime, server_default=func.now())

class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)  # Anonymized identifier
    total_experience = Column(Integer)  # Added field
    preferred_location = Column(Enum(LocationType))
    expected_salary_min = Column(Integer)
    expected_salary_max = Column(Integer)
    career_preference = Column(Enum(CareerPreference))
    skills = relationship('Skill', secondary='candidate_skills')
    created_at = Column(DateTime, server_default=func.now())

# ---- Junction Tables ----
job_skills = Table(
    'job_skills', Base.metadata,
    Column('job_id', ForeignKey('jobs.id'), primary_key=True),
    Column('skill_id', ForeignKey('skills.id'), primary_key=True)
)

candidate_skills = Table(
    'candidate_skills', Base.metadata,
    Column('candidate_id', ForeignKey('candidates.id'), primary_key=True),
    Column('skill_id', ForeignKey('skills.id'), primary_key=True)
)

# ---- Database Connection ----
DATABASE_URL = "postgresql://postgres:anasdb25@localhost:5432/talentloft"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)