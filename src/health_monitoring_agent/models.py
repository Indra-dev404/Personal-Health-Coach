"""
Data models for Health Monitoring Agent.

Defines Pydantic models for medical records, vital signs, activities, and symptoms
with validation rules according to requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator


class ActivityIntensity(str, Enum):
    """Activity intensity levels."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class RecommendationPriority(str, Enum):
    """Recommendation priority levels."""
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    INFORMATIONAL = "INFORMATIONAL"


class RecommendationStatus(str, Enum):
    """Recommendation status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class VitalSigns(BaseModel):
    """
    Vital signs data model with validation.
    
    Validates:
    - Heart rate: 30-220 bpm
    - Blood pressure: Systolic 70-200, Diastolic 40-130 mmHg
    - Temperature: 35-42°C
    - Oxygen saturation: 70-100%
    """
    heart_rate: int = Field(..., ge=30, le=220, description="Heart rate in bpm")
    systolic_bp: int = Field(..., ge=70, le=200, description="Systolic blood pressure in mmHg")
    diastolic_bp: int = Field(..., ge=40, le=130, description="Diastolic blood pressure in mmHg")
    temperature: float = Field(..., ge=35.0, le=42.0, description="Body temperature in Celsius")
    oxygen_saturation: int = Field(..., ge=70, le=100, description="Oxygen saturation percentage")
    weight: Optional[float] = Field(None, gt=0, description="Weight in kg")
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('diastolic_bp')
    @classmethod
    def validate_blood_pressure(cls, v: int, info) -> int:
        """Ensure diastolic BP is less than systolic BP."""
        if 'systolic_bp' in info.data and v >= info.data['systolic_bp']:
            raise ValueError("Diastolic blood pressure must be less than systolic blood pressure")
        return v


class Activity(BaseModel):
    """
    Activity data model with validation.
    
    Validates:
    - Duration: 1-1440 minutes (max 24 hours)
    - Intensity: low, moderate, high
    """
    type: str = Field(..., min_length=1, description="Activity type (e.g., walking, running)")
    duration: int = Field(..., ge=1, le=1440, description="Duration in minutes")
    intensity: ActivityIntensity = Field(..., description="Activity intensity level")
    calories: Optional[int] = Field(None, gt=0, description="Calories burned")
    distance: Optional[float] = Field(None, gt=0, description="Distance in km")
    timestamp: datetime = Field(default_factory=datetime.now)


class Symptom(BaseModel):
    """
    Symptom data model with validation.
    
    Validates:
    - Severity: 1-10 scale
    - Duration: positive hours
    """
    description: str = Field(..., min_length=1, description="Symptom description")
    severity: int = Field(..., ge=1, le=10, description="Severity on 1-10 scale")
    duration: int = Field(..., gt=0, description="Duration in hours")
    body_part: Optional[str] = Field(None, description="Affected body part")
    timestamp: datetime = Field(default_factory=datetime.now)


class MedicalRecord(BaseModel):
    """
    Medical record data model.
    
    Supports FHIR JSON and HL7 v2 formats.
    """
    user_id: str = Field(..., min_length=1)
    format: Literal["FHIR", "HL7v2"] = Field(..., description="Medical data format")
    content: dict[str, Any] = Field(..., description="Medical record content")
    last_updated: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0")


class CompressedData(BaseModel):
    """
    Compressed data with integrity verification.
    """
    compressed_bytes: bytes = Field(..., description="Compressed data")
    checksum: str = Field(..., description="SHA-256 checksum")
    original_size: int = Field(..., gt=0)
    compressed_size: int = Field(..., gt=0)
    compression_ratio: float = Field(..., gt=0, le=1)
    algorithm: Literal["deflate", "gzip"] = Field(default="gzip")


class WellnessEntry(BaseModel):
    """
    Unified wellness entry containing vitals, activities, or symptoms.
    """
    user_id: str = Field(..., min_length=1)
    entry_type: Literal["vital", "activity", "symptom"]
    data: VitalSigns | Activity | Symptom
    timestamp: datetime = Field(default_factory=datetime.now)


class Recommendation(BaseModel):
    """
    Health recommendation with evidence and priority.
    """
    id: str = Field(..., min_length=1)
    priority: RecommendationPriority
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1, description="Why this recommendation applies")
    supporting_data: dict[str, Any] = Field(default_factory=dict)
    evidence_source: str = Field(..., min_length=1, description="Citation for evidence")
    action_items: list[str] = Field(default_factory=list)
    status: RecommendationStatus = Field(default=RecommendationStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.now)


class EncryptedData(BaseModel):
    """
    Encrypted data with AES-256-GCM.
    """
    ciphertext: bytes = Field(..., description="Encrypted data")
    iv: bytes = Field(..., description="Initialization vector")
    auth_tag: bytes = Field(..., description="GCM authentication tag")
    algorithm: Literal["AES-256-GCM"] = Field(default="AES-256-GCM")
