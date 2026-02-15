"""
Wellness Tracker module for Health Monitoring Agent.

Records and manages wellness data including vital signs, activities, and symptoms.
"""

import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from .models import VitalSigns, Activity, Symptom, WellnessEntry
from .data_store import DataStore, StorageResult
from .privacy import PrivacyModule


@dataclass
class TrackingResult:
    """Result of wellness tracking operation."""
    success: bool
    message: str = ""
    entry_id: Optional[str] = None


class WellnessTracker:
    """
    Records and retrieves wellness data with validation and encryption.
    
    Integrates with DataStore for encrypted persistence and validation
    through Pydantic models.
    """
    
    def __init__(self, data_store: DataStore = None, privacy_module: PrivacyModule = None):
        """
        Initialize wellness tracker.
        
        Args:
            data_store: DataStore instance (created if not provided)
            privacy_module: PrivacyModule instance (created if not provided)
        """
        self.privacy_module = privacy_module or PrivacyModule()
        self.data_store = data_store or DataStore(privacy_module=self.privacy_module)
    
    def record_vital_signs(
        self, 
        user_id: str, 
        vitals: VitalSigns, 
        user_key: bytes,
        timestamp: datetime = None
    ) -> TrackingResult:
        """
        Record vital signs with validation.
        
        Args:
            user_id: User identifier
            vitals: VitalSigns data (validated by Pydantic)
            user_key: User's encryption key
            timestamp: Optional timestamp (uses vitals.timestamp if not provided)
            
        Returns:
            TrackingResult indicating success/failure
            
        Requirements: 2.1, 2.4
        """
        try:
            # Use provided timestamp or vitals timestamp
            if timestamp:
                vitals.timestamp = timestamp
            
            # Create wellness entry
            entry = WellnessEntry(
                user_id=user_id,
                entry_type="vital",
                data=vitals,
                timestamp=vitals.timestamp
            )
            
            # Generate storage key (use safe filename format)
            timestamp_str = vitals.timestamp.strftime("%Y%m%d_%H%M%S")
            entry_id = f"{timestamp_str}_{id(vitals)}"
            key = f"{user_id}/wellness/vitals/{entry_id}"
            
            # Serialize entry
            entry_bytes = entry.model_dump_json().encode('utf-8')
            
            # Store with metadata
            metadata = {
                'timestamp': vitals.timestamp.isoformat(),
                'data_type': 'vital_signs',
                'entry_type': 'vital'
            }
            
            result = self.data_store.store(key, entry_bytes, metadata, user_key)
            
            if result.success:
                return TrackingResult(
                    success=True,
                    message="Vital signs recorded successfully",
                    entry_id=entry_id
                )
            else:
                return TrackingResult(success=False, message=result.message)
                
        except Exception as e:
            return TrackingResult(success=False, message=f"Failed to record vital signs: {str(e)}")
    
    def record_activity(
        self, 
        user_id: str, 
        activity: Activity, 
        user_key: bytes,
        timestamp: datetime = None
    ) -> TrackingResult:
        """
        Record activity with validation.
        
        Args:
            user_id: User identifier
            activity: Activity data (validated by Pydantic)
            user_key: User's encryption key
            timestamp: Optional timestamp (uses activity.timestamp if not provided)
            
        Returns:
            TrackingResult indicating success/failure
            
        Requirements: 2.2, 2.4
        """
        try:
            # Use provided timestamp or activity timestamp
            if timestamp:
                activity.timestamp = timestamp
            
            # Create wellness entry
            entry = WellnessEntry(
                user_id=user_id,
                entry_type="activity",
                data=activity,
                timestamp=activity.timestamp
            )
            
            # Generate storage key (use safe filename format)
            timestamp_str = activity.timestamp.strftime("%Y%m%d_%H%M%S")
            entry_id = f"{timestamp_str}_{id(activity)}"
            key = f"{user_id}/wellness/activities/{entry_id}"
            
            # Serialize entry
            entry_bytes = entry.model_dump_json().encode('utf-8')
            
            # Store with metadata
            metadata = {
                'timestamp': activity.timestamp.isoformat(),
                'data_type': 'activity',
                'entry_type': 'activity'
            }
            
            result = self.data_store.store(key, entry_bytes, metadata, user_key)
            
            if result.success:
                return TrackingResult(
                    success=True,
                    message="Activity recorded successfully",
                    entry_id=entry_id
                )
            else:
                return TrackingResult(success=False, message=result.message)
                
        except Exception as e:
            return TrackingResult(success=False, message=f"Failed to record activity: {str(e)}")
    
    def record_symptom(
        self, 
        user_id: str, 
        symptom: Symptom, 
        user_key: bytes,
        timestamp: datetime = None
    ) -> TrackingResult:
        """
        Record symptom with validation.
        
        Args:
            user_id: User identifier
            symptom: Symptom data (validated by Pydantic)
            user_key: User's encryption key
            timestamp: Optional timestamp (uses symptom.timestamp if not provided)
            
        Returns:
            TrackingResult indicating success/failure
            
        Requirements: 2.3, 2.4
        """
        try:
            # Use provided timestamp or symptom timestamp
            if timestamp:
                symptom.timestamp = timestamp
            
            # Create wellness entry
            entry = WellnessEntry(
                user_id=user_id,
                entry_type="symptom",
                data=symptom,
                timestamp=symptom.timestamp
            )
            
            # Generate storage key (use safe filename format)
            timestamp_str = symptom.timestamp.strftime("%Y%m%d_%H%M%S")
            entry_id = f"{timestamp_str}_{id(symptom)}"
            key = f"{user_id}/wellness/symptoms/{entry_id}"
            
            # Serialize entry
            entry_bytes = entry.model_dump_json().encode('utf-8')
            
            # Store with metadata
            metadata = {
                'timestamp': symptom.timestamp.isoformat(),
                'data_type': 'symptom',
                'entry_type': 'symptom'
            }
            
            result = self.data_store.store(key, entry_bytes, metadata, user_key)
            
            if result.success:
                return TrackingResult(
                    success=True,
                    message="Symptom recorded successfully",
                    entry_id=entry_id
                )
            else:
                return TrackingResult(success=False, message=result.message)
                
        except Exception as e:
            return TrackingResult(success=False, message=f"Failed to record symptom: {str(e)}")
    
    def get_wellness_data(
        self, 
        user_id: str, 
        user_key: bytes,
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> list[WellnessEntry]:
        """
        Retrieve wellness data sorted by timestamp (descending).
        
        Args:
            user_id: User identifier
            user_key: User's encryption key
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of WellnessEntry sorted by timestamp (most recent first)
            
        Requirements: 2.5
        """
        entries = []
        
        try:
            # Query all wellness data types
            for data_type in ['vitals', 'activities', 'symptoms']:
                filters = {}
                if start_date:
                    filters['start_date'] = start_date
                if end_date:
                    filters['end_date'] = end_date
                
                # Query data store
                results = self.data_store.query(user_id, f"wellness/{data_type}", filters, user_key)
                
                # Deserialize entries
                for result_bytes in results:
                    try:
                        entry_dict = json.loads(result_bytes.decode('utf-8'))
                        entry = WellnessEntry(**entry_dict)
                        
                        # Apply date filters
                        if start_date and entry.timestamp < start_date:
                            continue
                        if end_date and entry.timestamp > end_date:
                            continue
                        
                        entries.append(entry)
                    except Exception as e:
                        # Skip invalid entries
                        continue
            
            # Sort by timestamp descending (most recent first)
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            
            return entries
            
        except Exception as e:
            # Return empty list on error
            return []
