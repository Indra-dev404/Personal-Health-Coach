"""
Medical History Compressor module.

Provides lossless compression and decompression of medical records using gzip
with SHA-256 checksum verification for data integrity.
"""

import gzip
import hashlib
import json
from typing import Union

from .models import MedicalRecord, CompressedData


class CompressionError(Exception):
    """Raised when compression operations fail."""
    pass


class MedicalHistoryCompressor:
    """
    Compresses and decompresses medical history data.
    
    Uses gzip compression with SHA-256 checksums for integrity verification.
    Supports FHIR JSON and HL7 v2 message formats.
    """
    
    def compress(self, medical_data: MedicalRecord) -> CompressedData:
        """
        Compress medical record data.
        
        Args:
            medical_data: MedicalRecord to compress
            
        Returns:
            CompressedData with checksum and metadata
            
        Raises:
            CompressionError: If compression fails
            
        Requirements: 1.1, 1.2, 1.4, 1.5
        """
        try:
            # Serialize medical record to JSON
            json_str = medical_data.model_dump_json()
            original_bytes = json_str.encode('utf-8')
            original_size = len(original_bytes)
            
            # Calculate checksum before compression
            checksum = hashlib.sha256(original_bytes).hexdigest()
            
            # Compress using gzip
            compressed_bytes = gzip.compress(original_bytes, compresslevel=9)
            compressed_size = len(compressed_bytes)
            
            # Calculate compression ratio
            compression_ratio = compressed_size / original_size
            
            return CompressedData(
                compressed_bytes=compressed_bytes,
                checksum=checksum,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                algorithm="gzip"
            )
            
        except Exception as e:
            raise CompressionError(f"Compression failed: {str(e)}") from e
    
    def decompress(self, compressed_data: CompressedData) -> MedicalRecord:
        """
        Decompress medical record data with checksum verification.
        
        Args:
            compressed_data: CompressedData to decompress
            
        Returns:
            Original MedicalRecord
            
        Raises:
            CompressionError: If decompression or checksum verification fails
            
        Requirements: 1.2, 1.4
        """
        try:
            # Decompress data
            decompressed_bytes = gzip.decompress(compressed_data.compressed_bytes)
            
            # Verify checksum
            if not self.validate_checksum(compressed_data, decompressed_bytes):
                raise CompressionError("Checksum mismatch - data may be corrupted")
            
            # Deserialize JSON to MedicalRecord
            json_str = decompressed_bytes.decode('utf-8')
            data_dict = json.loads(json_str)
            
            return MedicalRecord(**data_dict)
            
        except gzip.BadGzipFile as e:
            raise CompressionError(f"Invalid gzip data: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise CompressionError(f"Invalid JSON data: {str(e)}") from e
        except Exception as e:
            raise CompressionError(f"Decompression failed: {str(e)}") from e
    
    def validate_checksum(
        self, 
        compressed_data: CompressedData, 
        decompressed_bytes: bytes = None
    ) -> bool:
        """
        Validate checksum of compressed data.
        
        Args:
            compressed_data: CompressedData with stored checksum
            decompressed_bytes: Optional pre-decompressed bytes for validation
            
        Returns:
            True if checksum is valid, False otherwise
            
        Requirements: 1.4
        """
        try:
            # Decompress if not provided
            if decompressed_bytes is None:
                decompressed_bytes = gzip.decompress(compressed_data.compressed_bytes)
            
            # Calculate checksum of decompressed data
            calculated_checksum = hashlib.sha256(decompressed_bytes).hexdigest()
            
            # Compare with stored checksum
            return calculated_checksum == compressed_data.checksum
            
        except Exception:
            return False
