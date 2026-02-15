"""
Privacy Module for Health Monitoring Agent.

Provides encryption, authentication, access control, and audit logging
for HIPAA compliance.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from .models import EncryptedData


class PrivacyError(Exception):
    """Raised when privacy operations fail."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


@dataclass
class AuthResult:
    """Authentication result with session token."""
    success: bool
    user_id: Optional[str] = None
    session_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    message: str = ""


class PrivacyModule:
    """
    Handles encryption, authentication, and access control.
    
    Implements AES-256-GCM encryption, bcrypt password hashing,
    and HIPAA-compliant audit logging.
    """
    
    def __init__(self, audit_log_path: str = "data/audit.log"):
        """
        Initialize privacy module.
        
        Args:
            audit_log_path: Path to audit log file
        """
        self.audit_log_path = audit_log_path
        self._sessions: dict[str, tuple[str, datetime]] = {}  # token -> (user_id, expires_at)
        self._failed_attempts: dict[str, list[datetime]] = {}  # username -> [attempt_times]
        
        # Ensure audit log directory exists
        os.makedirs(os.path.dirname(audit_log_path) if os.path.dirname(audit_log_path) else ".", exist_ok=True)
    
    def encrypt_data(self, plaintext: bytes, user_key: bytes) -> EncryptedData:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            user_key: 32-byte encryption key
            
        Returns:
            EncryptedData with ciphertext, IV, and auth tag
            
        Raises:
            PrivacyError: If encryption fails
            
        Requirements: 5.1, 5.6
        """
        try:
            if len(user_key) != 32:
                raise PrivacyError("User key must be 32 bytes for AES-256")
            
            # Generate random IV (12 bytes for GCM)
            iv = os.urandom(12)
            
            # Create AESGCM cipher
            aesgcm = AESGCM(user_key)
            
            # Encrypt and get ciphertext with auth tag
            ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
            
            # Split ciphertext and auth tag (last 16 bytes)
            ciphertext = ciphertext_with_tag[:-16]
            auth_tag = ciphertext_with_tag[-16:]
            
            return EncryptedData(
                ciphertext=ciphertext,
                iv=iv,
                auth_tag=auth_tag,
                algorithm="AES-256-GCM"
            )
            
        except Exception as e:
            raise PrivacyError(f"Encryption failed: {str(e)}") from e
    
    def decrypt_data(self, encrypted_data: EncryptedData, user_key: bytes) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            encrypted_data: EncryptedData to decrypt
            user_key: 32-byte encryption key
            
        Returns:
            Decrypted plaintext
            
        Raises:
            PrivacyError: If decryption or authentication fails
            
        Requirements: 5.1, 5.6
        """
        try:
            if len(user_key) != 32:
                raise PrivacyError("User key must be 32 bytes for AES-256")
            
            # Create AESGCM cipher
            aesgcm = AESGCM(user_key)
            
            # Combine ciphertext and auth tag
            ciphertext_with_tag = encrypted_data.ciphertext + encrypted_data.auth_tag
            
            # Decrypt and verify auth tag
            plaintext = aesgcm.decrypt(encrypted_data.iv, ciphertext_with_tag, None)
            
            return plaintext
            
        except Exception as e:
            raise PrivacyError(f"Decryption failed: {str(e)}") from e
    
    def derive_key_from_password(self, password: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: User password
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (derived_key, salt)
            
        Requirements: 5.1
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def authenticate_user(
        self, 
        username: str, 
        password: str, 
        stored_hash: bytes
    ) -> AuthResult:
        """
        Authenticate user with bcrypt password verification.
        
        Args:
            username: Username
            password: Password to verify
            stored_hash: Stored bcrypt password hash
            
        Returns:
            AuthResult with session token if successful
            
        Requirements: 5.2
        """
        # Check rate limiting (max 5 failed attempts)
        if self._is_rate_limited(username):
            self.log_access(username, "authentication", datetime.now(), False)
            return AuthResult(
                success=False,
                message="Too many failed attempts. Please try again later."
            )
        
        try:
            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # Generate session token
                session_token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(minutes=30)
                
                # Store session
                self._sessions[session_token] = (username, expires_at)
                
                # Clear failed attempts
                self._failed_attempts.pop(username, None)
                
                # Log successful authentication
                self.log_access(username, "authentication", datetime.now(), True)
                
                return AuthResult(
                    success=True,
                    user_id=username,
                    session_token=session_token,
                    expires_at=expires_at,
                    message="Authentication successful"
                )
            else:
                # Record failed attempt
                self._record_failed_attempt(username)
                self.log_access(username, "authentication", datetime.now(), False)
                
                return AuthResult(
                    success=False,
                    message="Invalid credentials"
                )
                
        except Exception as e:
            self.log_access(username, "authentication", datetime.now(), False)
            return AuthResult(
                success=False,
                message=f"Authentication error: {str(e)}"
            )
    
    def hash_password(self, password: str) -> bytes:
        """
        Hash password using bcrypt.
        
        Args:
            password: Password to hash
            
        Returns:
            Bcrypt password hash
            
        Requirements: 5.2
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    def verify_session(self, session_token: str) -> Optional[str]:
        """
        Verify session token and return user_id if valid.
        
        Args:
            session_token: Session token to verify
            
        Returns:
            user_id if session is valid, None otherwise
        """
        if session_token not in self._sessions:
            return None
        
        user_id, expires_at = self._sessions[session_token]
        
        # Check if session expired
        if datetime.now() > expires_at:
            del self._sessions[session_token]
            return None
        
        return user_id
    
    def log_access(
        self, 
        user_id: str, 
        operation: str, 
        timestamp: datetime, 
        success: bool
    ) -> None:
        """
        Log data access for HIPAA compliance audit trail.
        
        Args:
            user_id: User identifier
            operation: Operation type
            timestamp: Operation timestamp
            success: Whether operation succeeded
            
        Requirements: 5.3, 5.4
        """
        log_entry = (
            f"{timestamp.isoformat()} | "
            f"USER: {user_id} | "
            f"OPERATION: {operation} | "
            f"SUCCESS: {success}\n"
        )
        
        try:
            with open(self.audit_log_path, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            # Log to stderr if file write fails
            print(f"Failed to write audit log: {e}", file=__import__('sys').stderr)
    
    def verify_authorization(
        self, 
        user_id: str, 
        resource: str, 
        operation: str
    ) -> bool:
        """
        Verify user authorization for resource access.
        
        Args:
            user_id: User identifier
            resource: Resource being accessed
            operation: Operation type (read, write, delete)
            
        Returns:
            True if authorized, False otherwise
            
        Requirements: 5.4
        """
        # Basic authorization: users can only access their own resources
        # Resource format: "user_id/data_type/..."
        if resource.startswith(f"{user_id}/"):
            return True
        
        # Log unauthorized attempt
        self.log_access(user_id, f"unauthorized_{operation}_{resource}", datetime.now(), False)
        return False
    
    def _is_rate_limited(self, username: str) -> bool:
        """Check if user is rate limited due to failed attempts."""
        if username not in self._failed_attempts:
            return False
        
        # Remove attempts older than 15 minutes
        cutoff = datetime.now() - timedelta(minutes=15)
        self._failed_attempts[username] = [
            t for t in self._failed_attempts[username] if t > cutoff
        ]
        
        # Check if 5 or more failed attempts in last 15 minutes
        return len(self._failed_attempts[username]) >= 5
    
    def _record_failed_attempt(self, username: str) -> None:
        """Record a failed authentication attempt."""
        if username not in self._failed_attempts:
            self._failed_attempts[username] = []
        self._failed_attempts[username].append(datetime.now())
