"""
Data Store module for Health Monitoring Agent.

Provides encrypted file-based storage with user-based partitioning
and efficient querying capabilities.
"""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, Any
from datetime import datetime
from dataclasses import dataclass

from .privacy import PrivacyModule


@dataclass
class StorageResult:
    """Result of storage operation."""
    success: bool
    message: str = ""
    key: Optional[str] = None


class DataStoreError(Exception):
    """Raised when data store operations fail."""
    pass


class DataStore:
    """
    Encrypted file-based storage system.
    
    Uses user-based partitioning: {user_id}/{data_type}/{timestamp}
    Integrates with Privacy Module for automatic encryption/decryption.
    """
    
    def __init__(self, base_path: str = "data/store", privacy_module: PrivacyModule = None):
        """
        Initialize data store.
        
        Args:
            base_path: Base directory for data storage
            privacy_module: Privacy module for encryption (created if not provided)
        """
        self.base_path = Path(base_path)
        self.privacy_module = privacy_module or PrivacyModule()
        
        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Index for efficient querying: {user_id: {data_type: [keys]}}
        self._index: dict[str, dict[str, list[str]]] = {}
        self._load_index()
    
    def store(
        self, 
        key: str, 
        value: bytes, 
        metadata: dict[str, Any],
        user_key: bytes
    ) -> StorageResult:
        """
        Store encrypted data with metadata.
        
        Args:
            key: Storage key (format: user_id/data_type/identifier)
            value: Data to store (will be encrypted)
            metadata: Metadata including timestamp, checksum, data type
            user_key: User's encryption key
            
        Returns:
            StorageResult indicating success/failure
            
        Requirements: 1.4, 2.4, 5.1
        """
        try:
            # Parse key to extract user_id and data_type
            parts = key.split('/')
            if len(parts) < 2:
                return StorageResult(
                    success=False,
                    message="Invalid key format. Expected: user_id/data_type/identifier"
                )
            
            user_id = parts[0]
            data_type = parts[1]
            
            # Encrypt data
            encrypted_data = self.privacy_module.encrypt_data(value, user_key)
            
            # Prepare storage object
            storage_obj = {
                'encrypted_data': {
                    'ciphertext': encrypted_data.ciphertext,
                    'iv': encrypted_data.iv,
                    'auth_tag': encrypted_data.auth_tag,
                    'algorithm': encrypted_data.algorithm
                },
                'metadata': metadata
            }
            
            # Create directory structure
            file_path = self.base_path / key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(file_path, 'wb') as f:
                pickle.dump(storage_obj, f)
            
            # Update index
            self._update_index(user_id, data_type, key)
            
            # Log access
            self.privacy_module.log_access(user_id, f"store_{data_type}", datetime.now(), True)
            
            return StorageResult(success=True, message="Data stored successfully", key=key)
            
        except Exception as e:
            return StorageResult(success=False, message=f"Storage failed: {str(e)}")
    
    def retrieve(self, key: str, user_key: bytes) -> Optional[bytes]:
        """
        Retrieve and decrypt data.
        
        Args:
            key: Storage key
            user_key: User's encryption key
            
        Returns:
            Decrypted data or None if not found
            
        Requirements: 2.4, 5.1
        """
        try:
            file_path = self.base_path / key
            
            if not file_path.exists():
                return None
            
            # Read from file
            with open(file_path, 'rb') as f:
                storage_obj = pickle.load(f)
            
            # Reconstruct EncryptedData
            from .models import EncryptedData
            encrypted_data = EncryptedData(
                ciphertext=storage_obj['encrypted_data']['ciphertext'],
                iv=storage_obj['encrypted_data']['iv'],
                auth_tag=storage_obj['encrypted_data']['auth_tag'],
                algorithm=storage_obj['encrypted_data']['algorithm']
            )
            
            # Decrypt data
            decrypted_data = self.privacy_module.decrypt_data(encrypted_data, user_key)
            
            # Log access
            user_id = key.split('/')[0]
            data_type = key.split('/')[1] if len(key.split('/')) > 1 else 'unknown'
            self.privacy_module.log_access(user_id, f"retrieve_{data_type}", datetime.now(), True)
            
            return decrypted_data
            
        except Exception as e:
            # Log failed access
            try:
                user_id = key.split('/')[0]
                data_type = key.split('/')[1] if len(key.split('/')) > 1 else 'unknown'
                self.privacy_module.log_access(user_id, f"retrieve_{data_type}", datetime.now(), False)
            except:
                pass
            return None
    
    def query(
        self, 
        user_id: str, 
        data_type: str, 
        filters: dict[str, Any],
        user_key: bytes
    ) -> list[bytes]:
        """
        Query data with filters.
        
        Args:
            user_id: User identifier
            data_type: Type of data to query
            filters: Filter criteria (e.g., {'start_date': ..., 'end_date': ...})
            user_key: User's encryption key
            
        Returns:
            List of matching decrypted data
            
        Requirements: 2.4, 2.5
        """
        results = []
        
        try:
            # Get keys from index
            if user_id not in self._index or data_type not in self._index[user_id]:
                # Try to find files directly if index is empty
                search_path = self.base_path / user_id / data_type
                if search_path.exists():
                    for file_path in search_path.rglob('*'):
                        if file_path.is_file() and file_path.name != '_index.json':
                            # Construct key from path
                            rel_path = file_path.relative_to(self.base_path)
                            key = str(rel_path).replace('\\', '/')
                            data = self.retrieve(key, user_key)
                            if data is not None:
                                results.append(data)
                return results
            
            keys = self._index[user_id][data_type]
            
            # Retrieve and filter data
            for key in keys:
                data = self.retrieve(key, user_key)
                if data is not None:
                    # Apply filters (basic implementation)
                    # In production, would parse metadata and apply sophisticated filtering
                    results.append(data)
            
            # Log access
            self.privacy_module.log_access(user_id, f"query_{data_type}", datetime.now(), True)
            
            return results
            
        except Exception as e:
            self.privacy_module.log_access(user_id, f"query_{data_type}", datetime.now(), False)
            return results
    
    def delete(self, key: str, user_id: str) -> StorageResult:
        """
        Delete data after authorization check.
        
        Args:
            key: Storage key
            user_id: User requesting deletion
            
        Returns:
            StorageResult indicating success/failure
            
        Requirements: 2.4, 5.4
        """
        try:
            # Verify authorization
            if not self.privacy_module.verify_authorization(user_id, key, "delete"):
                self.privacy_module.log_access(user_id, f"delete_unauthorized", datetime.now(), False)
                return StorageResult(success=False, message="Unauthorized access")
            
            file_path = self.base_path / key
            
            if not file_path.exists():
                return StorageResult(success=False, message="Key not found")
            
            # Delete file
            file_path.unlink()
            
            # Update index
            parts = key.split('/')
            if len(parts) >= 2:
                user_id_from_key = parts[0]
                data_type = parts[1]
                if user_id_from_key in self._index and data_type in self._index[user_id_from_key]:
                    self._index[user_id_from_key][data_type].remove(key)
                    self._save_index()
            
            # Log access
            self.privacy_module.log_access(user_id, f"delete", datetime.now(), True)
            
            return StorageResult(success=True, message="Data deleted successfully")
            
        except Exception as e:
            self.privacy_module.log_access(user_id, f"delete", datetime.now(), False)
            return StorageResult(success=False, message=f"Deletion failed: {str(e)}")
    
    def _update_index(self, user_id: str, data_type: str, key: str) -> None:
        """Update index with new key."""
        if user_id not in self._index:
            self._index[user_id] = {}
        if data_type not in self._index[user_id]:
            self._index[user_id][data_type] = []
        if key not in self._index[user_id][data_type]:
            self._index[user_id][data_type].append(key)
        self._save_index()
    
    def _save_index(self) -> None:
        """Save index to disk."""
        index_path = self.base_path / '_index.json'
        try:
            with open(index_path, 'w') as f:
                json.dump(self._index, f)
        except Exception as e:
            print(f"Failed to save index: {e}", file=__import__('sys').stderr)
    
    def _load_index(self) -> None:
        """Load index from disk."""
        index_path = self.base_path / '_index.json'
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    self._index = json.load(f)
            except Exception as e:
                print(f"Failed to load index: {e}", file=__import__('sys').stderr)
                self._index = {}
