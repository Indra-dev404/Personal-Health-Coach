"""
Unit tests for Recommendation Engine.

Tests core functionality of recommendation generation, vital analysis,
activity analysis, and chronic condition handling.
"""

import pytest
from datetime import datetime, timedelta
from src.health_monitoring_agent.models import (
    VitalSigns, Activity, Symptom, ActivityIntensity,
    RecommendationPriority, MedicalRecord
)
from src.health_monitoring_agent.recommendation_engine import RecommendationEngine


class TestRecommendationEngine:
    """Test suite for RecommendationEngine."""
    
    def test_analyze_vital_trends_normal(self):
        """Test vital trends analysis with normal values."""
        engine = RecommendationEngine()
        
        vitals = [
            VitalSigns(
                heart_rate=75,
                systolic_bp=120,
                diastolic_bp=80,
                temperature=36.8,
                oxygen_saturation=98
            )
        ]
        
        analysis = engine.analyze_vital_trends(vitals)
        
        assert len(analysis.abnormal_readings) == 0
        assert "0 readings with abnormal values" in analysis.summary
    
    def test_analyze_vital_trends_abnormal(self):
        """Test vital trends analysis with abnormal values."""
        engine = RecommendationEngine()
        
        vitals = [
            VitalSigns(
                heart_rate=120,  # High
                systolic_bp=150,  # High
                diastolic_bp=95,  # High
                temperature=38.0,  # High
                oxygen_saturation=92  # Low
            )
        ]
        
        analysis = engine.analyze_vital_trends(vitals)
        
        assert len(analysis.abnormal_readings) == 1
        assert len(analysis.abnormal_readings[0]['abnormalities']) == 5
    
    def test_analyze_activity_levels_meets_guidelines(self):
        """Test activity analysis when meeting WHO guidelines."""
        engine = RecommendationEngine()
        
        # 150 minutes of moderate activity
        activities = [
            Activity(
                type="walking",
                duration=30,
                intensity=ActivityIntensity.MODERATE,
                timestamp=datetime.now() - timedelta(days=i)
            )
            for i in range(5)  # 5 days * 30 min = 150 min
        ]
        
        analysis = engine.analyze_activity_levels(activities)
        
        assert analysis.total_minutes == 150
        assert analysis.meets_who_guidelines == True
        assert len(analysis.recommendations) == 0
    
    def test_analyze_activity_levels_below_guidelines(self):
        """Test activity analysis when below WHO guidelines."""
        engine = RecommendationEngine()
        
        # Only 60 minutes of moderate activity
        activities = [
            Activity(
                type="walking",
                duration=30,
                intensity=ActivityIntensity.MODERATE,
                timestamp=datetime.now() - timedelta(days=i)
            )
            for i in range(2)  # 2 days * 30 min = 60 min
        ]
        
        analysis = engine.analyze_activity_levels(activities)
        
        assert analysis.total_minutes == 60
        assert analysis.meets_who_guidelines == False
        assert len(analysis.recommendations) > 0
        assert "90 minutes" in analysis.recommendations[0]  # 150 - 60 = 90
    
    def test_check_chronic_conditions(self):
        """Test chronic condition extraction from medical history."""
        engine = RecommendationEngine()
        
        medical_record = MedicalRecord(
            user_id="test_user",
            format="FHIR",
            content={"conditions": ["diabetes", "hypertension"]},
            version="1.0"
        )
        
        conditions = engine.check_chronic_conditions(medical_record)
        
        assert len(conditions) == 2
        assert "diabetes" in conditions
        assert "hypertension" in conditions
    
    def test_critical_alert_for_abnormal_vitals(self):
        """Test that CRITICAL alerts are generated for abnormal vitals."""
        engine = RecommendationEngine()
        
        # Create abnormal vital signs
        vitals = [
            VitalSigns(
                heart_rate=120,  # High
                systolic_bp=150,  # High
                diastolic_bp=95,  # High
                temperature=38.0,  # High
                oxygen_saturation=92  # Low
            )
        ]
        
        recommendations = engine._analyze_vitals_for_alerts(vitals)
        
        assert len(recommendations) == 1
        assert recommendations[0].priority == RecommendationPriority.CRITICAL
        assert "Abnormal Vital Signs" in recommendations[0].title
    
    def test_no_alert_for_normal_vitals(self):
        """Test that no alerts are generated for normal vitals."""
        engine = RecommendationEngine()
        
        vitals = [
            VitalSigns(
                heart_rate=75,
                systolic_bp=120,
                diastolic_bp=80,
                temperature=36.8,
                oxygen_saturation=98
            )
        ]
        
        recommendations = engine._analyze_vitals_for_alerts(vitals)
        
        assert len(recommendations) == 0
    
    def test_activity_recommendation_for_low_activity(self):
        """Test that recommendations are generated for low activity."""
        engine = RecommendationEngine()
        
        # Only 30 minutes of activity
        activities = [
            Activity(
                type="walking",
                duration=30,
                intensity=ActivityIntensity.MODERATE
            )
        ]
        
        recommendations = engine._analyze_activity_levels(activities)
        
        assert len(recommendations) == 1
        assert recommendations[0].priority == RecommendationPriority.IMPORTANT
        assert "Increase Physical Activity" in recommendations[0].title


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
