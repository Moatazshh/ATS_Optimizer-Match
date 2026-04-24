from pydantic import BaseModel, Field
from typing import List, Optional

# ---- JD Extraction Models ----

class JDKeywords(BaseModel):
    job_title: str = "Unknown Role"
    hard_skills: List[str]
    soft_skills: List[str]
    action_verbs: List[str]
    certifications: List[str]

# ---- Resume Data Models ----

class ContactInfo(BaseModel):
    name: str = Field(description="Full name")
    email: str = Field(description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City, State or Country")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    website: Optional[str] = Field(None, description="Personal website or GitHub")

class ExperienceEntry(BaseModel):
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    start_date: str = Field(description="Start date (e.g., MM/YYYY)")
    end_date: str = Field(description="End date (e.g., MM/YYYY or Present)")
    location: Optional[str] = Field(None, description="Location of the job")
    bullet_points: List[str] = Field(description="List of achievements and responsibilities")

class EducationEntry(BaseModel):
    degree: str = Field(description="Degree obtained")
    institution: str = Field(description="Name of the institution")
    graduation_date: str = Field(description="Graduation date (e.g., MM/YYYY)")
    location: Optional[str] = Field(None, description="Location of the institution")

class StructuredResume(BaseModel):
    contact_info: ContactInfo
    summary: str = Field(description="Professional summary")
    experience: List[ExperienceEntry]
    education: List[EducationEntry]
    skills: List[str] = Field(description="List of skills")
    certifications: Optional[List[str]] = Field(None, description="List of certifications")

class CoverLetter(BaseModel):
    date: str
    recipient_name: str = "Hiring Manager"
    company_name: str
    content: str
    salutation: str = "Dear"
    closing: str = "Sincerely"

# ---- API Response Models ----

class OptimizationResponse(BaseModel):
    ats_score: float
    iterations: int
    template_used: str
    feedback: List[str] = Field(description="Feedback on what was changed or improved")
    # Note: We will likely return the actual docx file as a FileResponse,
    # but we can also return JSON if needed.
