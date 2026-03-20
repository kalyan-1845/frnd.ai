"""
Security Layer — Authentication Module
Provides user verification and session management.
"""

import hashlib
import hmac
import time
import os
import json
from typing import Optional, Dict, Any
from functools import wraps

# Path for storing user credentials
CREDENTIALS_FILE = "user_credentials.json"
SESSION_TIMEOUT = 3600  # 1 hour

class SecurityAuth:
    """
    Handles user authentication and session management.
    """
    
    def __init__(self, data_dir: str = "."):
        self.credentials_path = os.path.join(data_dir, CREDENTIALS_FILE)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._credentials: Dict[str, Dict[str, Any]] = {}
        self._master_hash: Optional[str] = None
        self._master_salt: Optional[str] = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load stored credentials from disk."""
        if os.path.exists(self.credentials_path):
            try:
                with open(self.credentials_path, 'r') as f:
                    data = json.load(f)
                    self._credentials = data.get("users", {})
                    self._master_hash = data.get("master_hash")
            except Exception:
                self._credentials = {}
                self._master_hash = None
        else:
            self._credentials = {}
            self._master_hash = None
    
    def _save_credentials(self):
        """Persist credentials to disk."""
        data = {
            "users": self._credentials,
            "master_hash": self._master_hash
        }
        with open(self.credentials_path, 'w') as f:
            json.dump(data, f)
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """Create secure hash of password with salt."""
        if salt is None:
            salt = os.urandom(32).hex()
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return key.hex(), salt
    
    def set_master_password(self, password: str) -> bool:
        """Set the master password for the assistant."""
        self._master_hash, salt = self._hash_password(password)
        self._master_salt = salt
        self._save_credentials()
        return True
    
    def verify_master_password(self, password: str) -> bool:
        """Verify the master password."""
        if not self._master_hash or not hasattr(self, '_master_salt'):
            return False
        
        key, _ = self._hash_password(password, self._master_salt)
        return hmac.compare_digest(key, self._master_hash)
    
    def add_user(self, username: str, password: str, role: str = "user") -> bool:
        """Add a new user."""
        password_hash, salt = self._hash_password(password)
        self._credentials[username] = {
            "hash": password_hash,
            "salt": salt,
            "role": role,
            "created_at": time.time()
        }
        self._save_credentials()
        return True
    
    def verify_user(self, username: str, password: str) -> bool:
        """Verify user credentials."""
        if username not in self._credentials:
            return False
        
        user = self._credentials[username]
        password_hash, _ = self._hash_password(password, user["salt"])
        return hmac.compare_digest(password_hash, user["hash"])
    
    def create_session(self, username: str) -> str:
        """Create a new session for authenticated user."""
        session_id = os.urandom(32).hex()
        self._sessions[session_id] = {
            "username": username,
            "created_at": time.time(),
            "last_activity": time.time()
        }
        return session_id
    
    def verify_session(self, session_id: str) -> Optional[str]:
        """Verify session and return username if valid."""
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        elapsed = time.time() - session["last_activity"]
        
        if elapsed > SESSION_TIMEOUT:
            del self._sessions[session_id]
            return None
        
        session["last_activity"] = time.time()
        return session["username"]
    
    def revoke_session(self, session_id: str):
        """Revoke a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def get_user_role(self, username: str) -> Optional[str]:
        """Get user role."""
        user = self._credentials.get(username)
        return user.get("role") if user else None


def require_auth(func):
    """Decorator to require authentication for a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Session check - can be extended with actual session management
        return func(*args, **kwargs)
    return wrapper


# Global instance
_auth = None

def get_auth() -> SecurityAuth:
    """Get global auth instance."""
    global _auth
    if _auth is None:
        _auth = SecurityAuth()
    return _auth
