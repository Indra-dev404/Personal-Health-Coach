"""
Export Manager for Health Monitoring Agent.

Provides data export functionality in FHIR and PDF formats with
re-authentication requirements for sensitive data.
"""

import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from .models import MedicalRecord, WellnessEntry, Recommendation
from .wellness_tracker import WellnessTracker
from .recommendation_engine import RecommendationEngine
from .privacy import PrivacyModule
from .compression import MedicalHistoryCompressor


@dataclass
class ExportResult:
    """Result of export operation."""
    success: bool
    message: str = ""
    file_path: Optional[str] = None
    data: Optional[dict] = None


class ExportManager:
    """
    Manages data export in standard formats.
    
    Supports FHIR R4 JSON and PDF exports with re-authentication
    requirements for sensitive data.
    """
    
    def __init__(
        self,
        wellness_tracker: WellnessTracker = None,
        recommendation_engine: RecommendationEngine = None,
        privacy_module: PrivacyModule = None,
        compressor: MedicalHistoryCompressor = None
    ):
        """
        Initialize export manager.
        
        Args:
            wellness_tracker: WellnessTracker instance
            recommendation_engine: RecommendationEngine instance
            privacy_module: PrivacyModule instance
            compressor: MedicalHistoryCompressor instance
        """
        self.wellness_tracker = wellness_tracker or WellnessTracker()
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.privacy_module = privacy_module or PrivacyModule()
        self.compressor = compressor or MedicalHistoryCompressor()
    
    def export_fhir(
        self,
        user_id: str,
        user_key: bytes,
        medical_history: Optional[MedicalRecord] = None,
        session_token: Optional[str] = None
    ) -> ExportResult:
        """
        Export user data as FHIR R4 JSON Bundle.
        
        Args:
            user_id: User identifier
            user_key: User's encryption key
            medical_history: Optional medical history
            session_token: Session token for re-authentication check
            
        Returns:
            ExportResult with FHIR Bundle
            
        Requirements: 8.1, 8.2, 8.3, 8.5
        """
        try:
            # Require re-authentication
            if not self.require_reauth(user_id, session_token):
                return ExportResult(
                    success=False,
                    message="Re-authentication required for sensitive data export"
                )
            
            # Get all wellness data
            wellness_data = self.wellness_tracker.get_wellness_data(user_id, user_key)
            
            # Get recommendations
            recommendations = self.recommendation_engine.generate_recommendations(
                user_id, user_key, medical_history
            )
            
            # Build FHIR Bundle
            fhir_bundle = self._build_fhir_bundle(
                user_id, wellness_data, recommendations, medical_history
            )
            
            # Log export
            self.privacy_module.log_access(user_id, "export_fhir", datetime.now(), True)
            
            return ExportResult(
                success=True,
                message="FHIR export completed successfully",
                data=fhir_bundle
            )
            
        except Exception as e:
            self.privacy_module.log_access(user_id, "export_fhir", datetime.now(), False)
            return ExportResult(
                success=False,
                message=f"FHIR export failed: {str(e)}"
            )
    
    def export_pdf(
        self,
        user_id: str,
        user_key: bytes,
        medical_history: Optional[MedicalRecord] = None,
        session_token: Optional[str] = None
    ) -> ExportResult:
        """
        Export user data as human-readable PDF report.
        
        Args:
            user_id: User identifier
            user_key: User's encryption key
            medical_history: Optional medical history
            session_token: Session token for re-authentication check
            
        Returns:
            ExportResult with PDF report data
            
        Requirements: 8.4, 8.5
        """
        try:
            # Require re-authentication
            if not self.require_reauth(user_id, session_token):
                return ExportResult(
                    success=False,
                    message="Re-authentication required for sensitive data export"
                )
            
            # Get all wellness data
            wellness_data = self.wellness_tracker.get_wellness_data(user_id, user_key)
            
            # Get recommendations
            recommendations = self.recommendation_engine.generate_recommendations(
                user_id, user_key, medical_history
            )
            
            # Build PDF report (simplified - would use reportlab or similar in production)
            pdf_content = self._build_pdf_report(
                user_id, wellness_data, recommendations, medical_history
            )
            
            # Log export
            self.privacy_module.log_access(user_id, "export_pdf", datetime.now(), True)
            
            return ExportResult(
                success=True,
                message="PDF export completed successfully",
                data=pdf_content
            )
            
        except Exception as e:
            self.privacy_module.log_access(user_id, "export_pdf", datetime.now(), False)
            return ExportResult(
                success=False,
                message=f"PDF export failed: {str(e)}"
            )
    
    def require_reauth(self, user_id: str, session_token: Optional[str]) -> bool:
        """
        Check if re-authentication is required for export.
        
        Args:
            user_id: User identifier
            session_token: Session token to verify
            
        Returns:
            True if authenticated, False otherwise
            
        Requirements: 8.5
        """
        if not session_token:
            return False
        
        # Verify session token
        verified_user = self.privacy_module.verify_session(session_token)
        
        return verified_user == user_id
    
    def _build_fhir_bundle(
        self,
        user_id: str,
        wellness_data: list[WellnessEntry],
        recommendations: list[Recommendation],
        medical_history: Optional[MedicalRecord]
    ) -> dict:
        """
        Build FHIR R4 Bundle with all user data.
        
        Requirements: 8.1, 8.2
        """
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": datetime.now().isoformat(),
            "entry": []
        }
        
        # Add patient resource
        bundle["entry"].append({
            "resource": {
                "resourceType": "Patient",
                "id": user_id,
                "identifier": [{"value": user_id}]
            }
        })
        
        # Add medical history if available
        if medical_history:
            bundle["entry"].append({
                "resource": {
                    "resourceType": "Condition",
                    "subject": {"reference": f"Patient/{user_id}"},
                    "code": {"text": "Medical History"},
                    "note": [{"text": json.dumps(medical_history.content)}]
                }
            })
        
        # Add vital signs observations
        for entry in wellness_data:
            if entry.entry_type == "vital":
                vital = entry.data
                bundle["entry"].append({
                    "resource": {
                        "resourceType": "Observation",
                        "status": "final",
                        "category": [{"coding": [{"code": "vital-signs"}]}],
                        "subject": {"reference": f"Patient/{user_id}"},
                        "effectiveDateTime": vital.timestamp.isoformat(),
                        "component": [
                            {
                                "code": {"text": "Heart Rate"},
                                "valueQuantity": {"value": vital.heart_rate, "unit": "bpm"}
                            },
                            {
                                "code": {"text": "Blood Pressure"},
                                "valueQuantity": {
                                    "value": f"{vital.systolic_bp}/{vital.diastolic_bp}",
                                    "unit": "mmHg"
                                }
                            },
                            {
                                "code": {"text": "Temperature"},
                                "valueQuantity": {"value": vital.temperature, "unit": "Celsius"}
                            },
                            {
                                "code": {"text": "Oxygen Saturation"},
                                "valueQuantity": {"value": vital.oxygen_saturation, "unit": "%"}
                            }
                        ]
                    }
                })
            
            elif entry.entry_type == "activity":
                activity = entry.data
                bundle["entry"].append({
                    "resource": {
                        "resourceType": "Observation",
                        "status": "final",
                        "category": [{"coding": [{"code": "activity"}]}],
                        "subject": {"reference": f"Patient/{user_id}"},
                        "effectiveDateTime": activity.timestamp.isoformat(),
                        "code": {"text": activity.type},
                        "valueQuantity": {"value": activity.duration, "unit": "minutes"},
                        "note": [{"text": f"Intensity: {activity.intensity}"}]
                    }
                })
            
            elif entry.entry_type == "symptom":
                symptom = entry.data
                bundle["entry"].append({
                    "resource": {
                        "resourceType": "Observation",
                        "status": "final",
                        "category": [{"coding": [{"code": "symptom"}]}],
                        "subject": {"reference": f"Patient/{user_id}"},
                        "effectiveDateTime": symptom.timestamp.isoformat(),
                        "code": {"text": symptom.description},
                        "valueInteger": symptom.severity,
                        "note": [{"text": f"Duration: {symptom.duration} hours"}]
                    }
                })
        
        # Add recommendations as care plans
        for rec in recommendations:
            bundle["entry"].append({
                "resource": {
                    "resourceType": "CarePlan",
                    "status": "active",
                    "intent": "proposal",
                    "subject": {"reference": f"Patient/{user_id}"},
                    "title": rec.title,
                    "description": rec.description,
                    "note": [
                        {"text": f"Rationale: {rec.rationale}"},
                        {"text": f"Evidence: {rec.evidence_source}"},
                        {"text": f"Priority: {rec.priority.value}"}
                    ],
                    "activity": [
                        {"detail": {"description": item}} for item in rec.action_items
                    ]
                }
            })
        
        return bundle
    
    def _build_pdf_report(
        self,
        user_id: str,
        wellness_data: list[WellnessEntry],
        recommendations: list[Recommendation],
        medical_history: Optional[MedicalRecord]
    ) -> dict:
        """
        Build human-readable PDF report content.
        
        Requirements: 8.4
        """
        # Simplified PDF content as structured data
        # In production, would use reportlab or similar to generate actual PDF
        
        report = {
            "title": "Health Monitoring Report",
            "generated_at": datetime.now().isoformat(),
            "patient_id": user_id,
            "sections": []
        }
        
        # Medical history summary
        if medical_history:
            report["sections"].append({
                "title": "Medical History",
                "content": f"Format: {medical_history.format}, Last Updated: {medical_history.last_updated}"
            })
        
        # Wellness data summary
        vitals_count = sum(1 for e in wellness_data if e.entry_type == "vital")
        activities_count = sum(1 for e in wellness_data if e.entry_type == "activity")
        symptoms_count = sum(1 for e in wellness_data if e.entry_type == "symptom")
        
        report["sections"].append({
            "title": "Wellness Data Summary",
            "content": f"Vital Signs: {vitals_count}, Activities: {activities_count}, Symptoms: {symptoms_count}"
        })
        
        # Recommendations
        report["sections"].append({
            "title": "Health Recommendations",
            "recommendations": [
                {
                    "priority": rec.priority.value,
                    "title": rec.title,
                    "description": rec.description,
                    "rationale": rec.rationale,
                    "actions": rec.action_items
                }
                for rec in recommendations
            ]
        })
        
        return report
