"""
Recommendation Engine for Health Monitoring Agent.

Analyzes wellness data and medical history to generate personalized
health recommendations with evidence-based guidance.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from .models import (
    Recommendation, RecommendationPriority, VitalSigns, 
    Activity, Symptom, WellnessEntry, MedicalRecord
)
from .wellness_tracker import WellnessTracker
from .compression import MedicalHistoryCompressor


@dataclass
class TrendAnalysis:
    """Analysis of vital signs trends."""
    abnormal_readings: list[dict]
    trends: dict[str, str]  # metric -> "increasing", "decreasing", "stable"
    summary: str


@dataclass
class ActivityAnalysis:
    """Analysis of activity levels."""
    total_minutes: int
    weekly_average: float
    meets_who_guidelines: bool
    recommendations: list[str]


class RecommendationEngine:
    """
    Generates personalized health recommendations.
    
    Analyzes wellness data, medical history, and generates evidence-based
    recommendations with priority levels.
    """
    
    # Normal ranges for vital signs
    NORMAL_RANGES = {
        'heart_rate': (60, 100),
        'systolic_bp': (90, 140),
        'diastolic_bp': (60, 90),
        'temperature': (36.1, 37.2),
        'oxygen_saturation': (95, 100)
    }
    
    # WHO recommended activity: 150 minutes/week moderate intensity
    WHO_ACTIVITY_THRESHOLD = 150
    
    def __init__(
        self, 
        wellness_tracker: WellnessTracker = None,
        compressor: MedicalHistoryCompressor = None
    ):
        """
        Initialize recommendation engine.
        
        Args:
            wellness_tracker: WellnessTracker instance
            compressor: MedicalHistoryCompressor instance
        """
        self.wellness_tracker = wellness_tracker or WellnessTracker()
        self.compressor = compressor or MedicalHistoryCompressor()
    
    def generate_recommendations(
        self, 
        user_id: str,
        user_key: bytes,
        medical_history: Optional[MedicalRecord] = None
    ) -> list[Recommendation]:
        """
        Generate personalized recommendations.
        
        Args:
            user_id: User identifier
            user_key: User's encryption key
            medical_history: Optional medical history for chronic condition analysis
            
        Returns:
            List of recommendations sorted by priority
            
        Requirements: 3.1, 3.3
        """
        recommendations = []
        
        # Get wellness data from last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        wellness_data = self.wellness_tracker.get_wellness_data(
            user_id, user_key, start_date, end_date
        )
        
        # Separate data by type
        vitals = [e.data for e in wellness_data if e.entry_type == "vital"]
        activities = [e.data for e in wellness_data if e.entry_type == "activity"]
        symptoms = [e.data for e in wellness_data if e.entry_type == "symptom"]
        
        # Analyze vital signs for critical alerts
        if vitals:
            vital_recommendations = self._analyze_vitals_for_alerts(vitals)
            recommendations.extend(vital_recommendations)
        
        # Analyze activity levels
        if activities:
            activity_recommendations = self._analyze_activity_levels(activities)
            recommendations.extend(activity_recommendations)
        
        # Analyze chronic conditions if medical history provided
        if medical_history:
            chronic_recommendations = self._analyze_chronic_conditions(
                medical_history, vitals, activities, symptoms
            )
            recommendations.extend(chronic_recommendations)
        
        # Analyze symptoms for patterns
        if symptoms:
            symptom_recommendations = self._analyze_symptoms(symptoms)
            recommendations.extend(symptom_recommendations)
        
        # Sort by priority: CRITICAL -> IMPORTANT -> INFORMATIONAL
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.IMPORTANT: 1,
            RecommendationPriority.INFORMATIONAL: 2
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])
        
        return recommendations
    
    def analyze_vital_trends(self, vitals: list[VitalSigns]) -> TrendAnalysis:
        """
        Analyze vital signs trends and detect anomalies.
        
        Args:
            vitals: List of vital signs over time
            
        Returns:
            TrendAnalysis with abnormal readings and trends
            
        Requirements: 3.3
        """
        abnormal_readings = []
        
        for vital in vitals:
            abnormalities = []
            
            # Check heart rate
            if vital.heart_rate < self.NORMAL_RANGES['heart_rate'][0]:
                abnormalities.append(f"Low heart rate: {vital.heart_rate} bpm")
            elif vital.heart_rate > self.NORMAL_RANGES['heart_rate'][1]:
                abnormalities.append(f"High heart rate: {vital.heart_rate} bpm")
            
            # Check blood pressure
            if vital.systolic_bp < self.NORMAL_RANGES['systolic_bp'][0]:
                abnormalities.append(f"Low systolic BP: {vital.systolic_bp} mmHg")
            elif vital.systolic_bp > self.NORMAL_RANGES['systolic_bp'][1]:
                abnormalities.append(f"High systolic BP: {vital.systolic_bp} mmHg")
            
            if vital.diastolic_bp < self.NORMAL_RANGES['diastolic_bp'][0]:
                abnormalities.append(f"Low diastolic BP: {vital.diastolic_bp} mmHg")
            elif vital.diastolic_bp > self.NORMAL_RANGES['diastolic_bp'][1]:
                abnormalities.append(f"High diastolic BP: {vital.diastolic_bp} mmHg")
            
            # Check temperature
            if vital.temperature < self.NORMAL_RANGES['temperature'][0]:
                abnormalities.append(f"Low temperature: {vital.temperature}°C")
            elif vital.temperature > self.NORMAL_RANGES['temperature'][1]:
                abnormalities.append(f"High temperature: {vital.temperature}°C")
            
            # Check oxygen saturation
            if vital.oxygen_saturation < self.NORMAL_RANGES['oxygen_saturation'][0]:
                abnormalities.append(f"Low oxygen saturation: {vital.oxygen_saturation}%")
            
            if abnormalities:
                abnormal_readings.append({
                    'timestamp': vital.timestamp,
                    'abnormalities': abnormalities
                })
        
        summary = f"Found {len(abnormal_readings)} readings with abnormal values out of {len(vitals)} total readings"
        
        return TrendAnalysis(
            abnormal_readings=abnormal_readings,
            trends={},  # Simplified - would calculate trends in production
            summary=summary
        )
    
    def analyze_activity_levels(self, activities: list[Activity]) -> ActivityAnalysis:
        """
        Analyze activity levels against WHO guidelines.
        
        Args:
            activities: List of activities
            
        Returns:
            ActivityAnalysis with recommendations
            
        Requirements: 3.4
        """
        # Calculate total moderate/high intensity activity minutes
        total_minutes = sum(
            a.duration for a in activities 
            if a.intensity in ['moderate', 'high']
        )
        
        # Calculate weekly average (assuming data spans multiple weeks)
        weeks = max(1, len(set(a.timestamp.isocalendar()[1] for a in activities)))
        weekly_average = total_minutes / weeks
        
        meets_guidelines = weekly_average >= self.WHO_ACTIVITY_THRESHOLD
        
        recommendations = []
        if not meets_guidelines:
            deficit = self.WHO_ACTIVITY_THRESHOLD - weekly_average
            recommendations.append(
                f"Increase moderate activity by {int(deficit)} minutes per week to meet WHO guidelines"
            )
            recommendations.append("Consider activities like brisk walking, cycling, or swimming")
        
        return ActivityAnalysis(
            total_minutes=total_minutes,
            weekly_average=weekly_average,
            meets_who_guidelines=meets_guidelines,
            recommendations=recommendations
        )
    
    def check_chronic_conditions(self, medical_history: MedicalRecord) -> list[str]:
        """
        Extract chronic conditions from medical history.
        
        Args:
            medical_history: Medical record
            
        Returns:
            List of chronic condition names
            
        Requirements: 3.2
        """
        conditions = []
        
        # Parse FHIR or HL7 format for conditions
        if medical_history.format == "FHIR":
            # Simplified FHIR parsing
            if 'conditions' in medical_history.content:
                conditions = medical_history.content['conditions']
        
        return conditions
    
    def _analyze_vitals_for_alerts(self, vitals: list[VitalSigns]) -> list[Recommendation]:
        """Generate CRITICAL alerts for abnormal vitals."""
        recommendations = []
        
        # Check most recent vital signs
        if vitals:
            latest_vital = vitals[0]
            abnormalities = []
            
            if (latest_vital.heart_rate < 60 or latest_vital.heart_rate > 100):
                abnormalities.append(f"heart rate {latest_vital.heart_rate} bpm")
            
            if (latest_vital.systolic_bp < 90 or latest_vital.systolic_bp > 140):
                abnormalities.append(f"systolic BP {latest_vital.systolic_bp} mmHg")
            
            if (latest_vital.diastolic_bp < 60 or latest_vital.diastolic_bp > 90):
                abnormalities.append(f"diastolic BP {latest_vital.diastolic_bp} mmHg")
            
            if (latest_vital.temperature < 36.1 or latest_vital.temperature > 37.2):
                abnormalities.append(f"temperature {latest_vital.temperature}°C")
            
            if latest_vital.oxygen_saturation < 95:
                abnormalities.append(f"oxygen saturation {latest_vital.oxygen_saturation}%")
            
            if abnormalities:
                rec = Recommendation(
                    id=str(uuid.uuid4()),
                    priority=RecommendationPriority.CRITICAL,
                    title="Abnormal Vital Signs Detected",
                    description=f"Your recent vital signs show abnormal values: {', '.join(abnormalities)}",
                    rationale="These values fall outside normal ranges and may require medical attention",
                    supporting_data={'vitals': latest_vital.model_dump(), 'abnormalities': abnormalities},
                    evidence_source="CDC Vital Signs Reference Ranges",
                    action_items=[
                        "Consult with a healthcare provider",
                        "Monitor these values closely",
                        "Avoid strenuous activity until consulted"
                    ]
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _analyze_activity_levels(self, activities: list[Activity]) -> list[Recommendation]:
        """Generate recommendations based on activity analysis."""
        recommendations = []
        
        analysis = self.analyze_activity_levels(activities)
        
        if not analysis.meets_who_guidelines:
            rec = Recommendation(
                id=str(uuid.uuid4()),
                priority=RecommendationPriority.IMPORTANT,
                title="Increase Physical Activity",
                description=f"Your weekly activity average is {int(analysis.weekly_average)} minutes, below the WHO recommended 150 minutes",
                rationale="Regular physical activity reduces risk of chronic diseases and improves overall health",
                supporting_data={'analysis': analysis.__dict__},
                evidence_source="WHO Physical Activity Guidelines",
                action_items=analysis.recommendations
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _analyze_chronic_conditions(
        self, 
        medical_history: MedicalRecord,
        vitals: list,
        activities: list,
        symptoms: list
    ) -> list[Recommendation]:
        """Generate recommendations for chronic conditions."""
        recommendations = []
        
        conditions = self.check_chronic_conditions(medical_history)
        
        for condition in conditions:
            rec = Recommendation(
                id=str(uuid.uuid4()),
                priority=RecommendationPriority.IMPORTANT,
                title=f"Managing {condition}",
                description=f"Continue monitoring and managing your {condition}",
                rationale=f"Chronic condition management requires ongoing attention",
                supporting_data={'condition': condition},
                evidence_source="Medical Literature on Chronic Disease Management",
                action_items=[
                    "Follow prescribed treatment plan",
                    "Regular check-ups with healthcare provider",
                    "Monitor relevant vital signs"
                ]
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _analyze_symptoms(self, symptoms: list[Symptom]) -> list[Recommendation]:
        """Generate recommendations based on symptom patterns."""
        recommendations = []
        
        # Check for high severity symptoms
        severe_symptoms = [s for s in symptoms if s.severity >= 7]
        
        if severe_symptoms:
            rec = Recommendation(
                id=str(uuid.uuid4()),
                priority=RecommendationPriority.IMPORTANT,
                title="Severe Symptoms Reported",
                description=f"You've reported {len(severe_symptoms)} severe symptoms (severity 7+)",
                rationale="High severity symptoms may require medical evaluation",
                supporting_data={'symptom_count': len(severe_symptoms)},
                evidence_source="Clinical Symptom Assessment Guidelines",
                action_items=[
                    "Consult with a healthcare provider",
                    "Document symptom progression",
                    "Seek immediate care if symptoms worsen"
                ]
            )
            recommendations.append(rec)
        
        return recommendations
