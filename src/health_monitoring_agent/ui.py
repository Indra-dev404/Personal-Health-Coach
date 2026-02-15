"""
User Interface for Health Monitoring Agent.

Provides CLI-based interface for data input, viewing recommendations,
and visualizing wellness trends.
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import ValidationError

from .models import VitalSigns, Activity, Symptom, ActivityIntensity, RecommendationPriority
from .wellness_tracker import WellnessTracker
from .recommendation_engine import RecommendationEngine
from .export_manager import ExportManager
from .privacy import PrivacyModule
from .data_store import DataStore


class HealthMonitoringUI:
    """
    Command-line interface for Health Monitoring Agent.
    
    Provides forms for data input, recommendation viewing, and trend visualization.
    """
    
    def __init__(self, user_id: str, user_key: bytes):
        """
        Initialize UI for a specific user.
        
        Args:
            user_id: User identifier
            user_key: User's encryption key
        """
        self.user_id = user_id
        self.user_key = user_key
        
        # Initialize components
        self.privacy_module = PrivacyModule()
        self.data_store = DataStore(privacy_module=self.privacy_module)
        self.wellness_tracker = WellnessTracker(
            data_store=self.data_store,
            privacy_module=self.privacy_module
        )
        self.recommendation_engine = RecommendationEngine(
            wellness_tracker=self.wellness_tracker
        )
        self.export_manager = ExportManager(
            wellness_tracker=self.wellness_tracker,
            recommendation_engine=self.recommendation_engine,
            privacy_module=self.privacy_module
        )
        
        # Cache for pre-population
        self._last_vitals: Optional[VitalSigns] = None
        self._last_activity: Optional[Activity] = None
    
    def input_vital_signs(self) -> bool:
        """
        Display form for vital signs input with validation.
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 6.1, 6.2, 6.3, 6.5
        """
        print("\n=== Record Vital Signs ===")
        
        # Pre-populate with last values if available
        defaults = {}
        if self._last_vitals:
            defaults = {
                'heart_rate': self._last_vitals.heart_rate,
                'systolic_bp': self._last_vitals.systolic_bp,
                'diastolic_bp': self._last_vitals.diastolic_bp,
                'temperature': self._last_vitals.temperature,
                'oxygen_saturation': self._last_vitals.oxygen_saturation,
                'weight': self._last_vitals.weight
            }
            print("(Press Enter to use previous values shown in brackets)")
        
        try:
            # Get input with validation
            heart_rate = self._get_int_input(
                "Heart Rate (30-220 bpm)", 
                defaults.get('heart_rate')
            )
            systolic_bp = self._get_int_input(
                "Systolic Blood Pressure (70-200 mmHg)", 
                defaults.get('systolic_bp')
            )
            diastolic_bp = self._get_int_input(
                "Diastolic Blood Pressure (40-130 mmHg)", 
                defaults.get('diastolic_bp')
            )
            temperature = self._get_float_input(
                "Temperature (35-42°C)", 
                defaults.get('temperature')
            )
            oxygen_saturation = self._get_int_input(
                "Oxygen Saturation (70-100%)", 
                defaults.get('oxygen_saturation')
            )
            weight = self._get_float_input(
                "Weight in kg (optional, press Enter to skip)", 
                defaults.get('weight'),
                optional=True
            )
            
            # Create VitalSigns object (Pydantic validates)
            vitals = VitalSigns(
                heart_rate=heart_rate,
                systolic_bp=systolic_bp,
                diastolic_bp=diastolic_bp,
                temperature=temperature,
                oxygen_saturation=oxygen_saturation,
                weight=weight
            )
            
            # Record vitals
            result = self.wellness_tracker.record_vital_signs(
                self.user_id, vitals, self.user_key
            )
            
            if result.success:
                print(f"\n✓ {result.message}")
                self._last_vitals = vitals
                return True
            else:
                print(f"\n✗ Error: {result.message}")
                return False
                
        except ValidationError as e:
            # Display clear error messages
            print("\n✗ Validation Error:")
            for error in e.errors():
                field = error['loc'][0]
                msg = error['msg']
                print(f"  - {field}: {msg}")
            return False
        except ValueError as e:
            print(f"\n✗ Invalid input: {str(e)}")
            return False
        except Exception as e:
            print(f"\n✗ Unexpected error: {str(e)}")
            return False
    
    def input_activity(self) -> bool:
        """
        Display form for activity input with validation.
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 6.1, 6.2, 6.3, 6.5
        """
        print("\n=== Record Activity ===")
        
        # Pre-populate with last values if available
        defaults = {}
        if self._last_activity:
            defaults = {
                'type': self._last_activity.type,
                'duration': self._last_activity.duration,
                'intensity': self._last_activity.intensity.value
            }
            print("(Press Enter to use previous values shown in brackets)")
        
        try:
            activity_type = self._get_string_input(
                "Activity Type (e.g., walking, running, cycling)", 
                defaults.get('type')
            )
            duration = self._get_int_input(
                "Duration (1-1440 minutes)", 
                defaults.get('duration')
            )
            intensity_str = self._get_choice_input(
                "Intensity",
                ['low', 'moderate', 'high'],
                defaults.get('intensity')
            )
            intensity = ActivityIntensity(intensity_str)
            
            calories = self._get_int_input(
                "Calories burned (optional, press Enter to skip)",
                optional=True
            )
            distance = self._get_float_input(
                "Distance in km (optional, press Enter to skip)",
                optional=True
            )
            
            # Create Activity object
            activity = Activity(
                type=activity_type,
                duration=duration,
                intensity=intensity,
                calories=calories,
                distance=distance
            )
            
            # Record activity
            result = self.wellness_tracker.record_activity(
                self.user_id, activity, self.user_key
            )
            
            if result.success:
                print(f"\n✓ {result.message}")
                self._last_activity = activity
                return True
            else:
                print(f"\n✗ Error: {result.message}")
                return False
                
        except ValidationError as e:
            print("\n✗ Validation Error:")
            for error in e.errors():
                field = error['loc'][0]
                msg = error['msg']
                print(f"  - {field}: {msg}")
            return False
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            return False
    
    def input_symptom(self) -> bool:
        """
        Display form for symptom input with validation.
        
        Returns:
            True if successful, False otherwise
            
        Requirements: 6.1, 6.2, 6.3
        """
        print("\n=== Record Symptom ===")
        
        try:
            description = self._get_string_input("Symptom Description")
            severity = self._get_int_input("Severity (1-10 scale)")
            duration = self._get_int_input("Duration in hours")
            body_part = self._get_string_input(
                "Body Part (optional, press Enter to skip)",
                optional=True
            )
            
            # Create Symptom object
            symptom = Symptom(
                description=description,
                severity=severity,
                duration=duration,
                body_part=body_part
            )
            
            # Record symptom
            result = self.wellness_tracker.record_symptom(
                self.user_id, symptom, self.user_key
            )
            
            if result.success:
                print(f"\n✓ {result.message}")
                return True
            else:
                print(f"\n✗ Error: {result.message}")
                return False
                
        except ValidationError as e:
            print("\n✗ Validation Error:")
            for error in e.errors():
                field = error['loc'][0]
                msg = error['msg']
                print(f"  - {field}: {msg}")
            return False
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            return False
    
    def view_recommendations(self) -> None:
        """
        Display recommendations organized by priority.
        
        Requirements: 7.1, 7.4
        """
        print("\n=== Health Recommendations ===")
        
        try:
            recommendations = self.recommendation_engine.generate_recommendations(
                self.user_id, self.user_key
            )
            
            if not recommendations:
                print("No recommendations at this time. Keep tracking your wellness data!")
                return
            
            # Group by priority
            by_priority = {
                RecommendationPriority.CRITICAL: [],
                RecommendationPriority.IMPORTANT: [],
                RecommendationPriority.INFORMATIONAL: []
            }
            
            for rec in recommendations:
                by_priority[rec.priority].append(rec)
            
            # Display by priority
            for priority in [RecommendationPriority.CRITICAL, 
                           RecommendationPriority.IMPORTANT, 
                           RecommendationPriority.INFORMATIONAL]:
                recs = by_priority[priority]
                if recs:
                    print(f"\n{'='*60}")
                    print(f"{priority.value} PRIORITY ({len(recs)} recommendation{'s' if len(recs) > 1 else ''})")
                    print('='*60)
                    
                    for rec in recs:
                        print(f"\n📋 {rec.title}")
                        print(f"   {rec.description}")
                        print(f"\n   Rationale: {rec.rationale}")
                        print(f"   Evidence: {rec.evidence_source}")
                        
                        if rec.action_items:
                            print("\n   Action Items:")
                            for item in rec.action_items:
                                print(f"   • {item}")
                        
                        print(f"\n   Status: {rec.status.value}")
                        print()
                        
        except Exception as e:
            print(f"\n✗ Error generating recommendations: {str(e)}")
    
    def view_wellness_trends(self, days: int = 7) -> None:
        """
        Display wellness trends over specified time period.
        
        Args:
            days: Number of days to display (7, 30, or 90)
            
        Requirements: 7.2, 7.3
        """
        print(f"\n=== Wellness Trends (Last {days} Days) ===")
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            wellness_data = self.wellness_tracker.get_wellness_data(
                self.user_id, self.user_key, start_date, end_date
            )
            
            if not wellness_data:
                print(f"No wellness data found for the last {days} days.")
                return
            
            # Separate by type
            vitals = [e for e in wellness_data if e.entry_type == "vital"]
            activities = [e for e in wellness_data if e.entry_type == "activity"]
            symptoms = [e for e in wellness_data if e.entry_type == "symptom"]
            
            # Display vital signs with highlighting
            if vitals:
                print(f"\n📊 Vital Signs ({len(vitals)} readings)")
                print("-" * 60)
                for entry in vitals[:5]:  # Show last 5
                    v = entry.data
                    date_str = v.timestamp.strftime("%Y-%m-%d %H:%M")
                    
                    # Highlight abnormal values
                    hr_flag = "⚠️" if v.heart_rate < 60 or v.heart_rate > 100 else "✓"
                    bp_flag = "⚠️" if v.systolic_bp < 90 or v.systolic_bp > 140 or v.diastolic_bp < 60 or v.diastolic_bp > 90 else "✓"
                    temp_flag = "⚠️" if v.temperature < 36.1 or v.temperature > 37.2 else "✓"
                    o2_flag = "⚠️" if v.oxygen_saturation < 95 else "✓"
                    
                    print(f"{date_str}")
                    print(f"  {hr_flag} Heart Rate: {v.heart_rate} bpm")
                    print(f"  {bp_flag} Blood Pressure: {v.systolic_bp}/{v.diastolic_bp} mmHg")
                    print(f"  {temp_flag} Temperature: {v.temperature}°C")
                    print(f"  {o2_flag} Oxygen Saturation: {v.oxygen_saturation}%")
                    print()
            
            # Display activities
            if activities:
                print(f"\n🏃 Activities ({len(activities)} logged)")
                print("-" * 60)
                total_minutes = sum(a.data.duration for a in activities)
                print(f"Total Activity Time: {total_minutes} minutes")
                for entry in activities[:5]:  # Show last 5
                    a = entry.data
                    date_str = a.timestamp.strftime("%Y-%m-%d %H:%M")
                    print(f"{date_str}: {a.type} - {a.duration} min ({a.intensity.value})")
            
            # Display symptoms
            if symptoms:
                print(f"\n🩺 Symptoms ({len(symptoms)} reported)")
                print("-" * 60)
                for entry in symptoms[:5]:  # Show last 5
                    s = entry.data
                    date_str = s.timestamp.strftime("%Y-%m-%d %H:%M")
                    severity_bar = "█" * s.severity + "░" * (10 - s.severity)
                    print(f"{date_str}: {s.description}")
                    print(f"  Severity: {severity_bar} ({s.severity}/10)")
                    print(f"  Duration: {s.duration} hours")
                    print()
                    
        except Exception as e:
            print(f"\n✗ Error retrieving wellness trends: {str(e)}")
    
    def _get_int_input(self, prompt: str, default: Optional[int] = None, optional: bool = False) -> Optional[int]:
        """Get integer input with optional default."""
        if default is not None:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
        
        while True:
            value = input(prompt).strip()
            if not value and default is not None:
                return default
            if not value and optional:
                return None
            try:
                return int(value)
            except ValueError:
                print("  ✗ Please enter a valid integer")
    
    def _get_float_input(self, prompt: str, default: Optional[float] = None, optional: bool = False) -> Optional[float]:
        """Get float input with optional default."""
        if default is not None:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
        
        while True:
            value = input(prompt).strip()
            if not value and default is not None:
                return default
            if not value and optional:
                return None
            try:
                return float(value)
            except ValueError:
                print("  ✗ Please enter a valid number")
    
    def _get_string_input(self, prompt: str, default: Optional[str] = None, optional: bool = False) -> Optional[str]:
        """Get string input with optional default."""
        if default is not None:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
        
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if not value and optional:
            return None
        return value
    
    def _get_choice_input(self, prompt: str, choices: list[str], default: Optional[str] = None) -> str:
        """Get choice input from list of options."""
        choices_str = "/".join(choices)
        if default is not None:
            prompt = f"{prompt} ({choices_str}) [{default}]: "
        else:
            prompt = f"{prompt} ({choices_str}): "
        
        while True:
            value = input(prompt).strip().lower()
            if not value and default is not None:
                return default
            if value in choices:
                return value
            print(f"  ✗ Please choose from: {choices_str}")
