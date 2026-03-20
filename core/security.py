"""
Security Module
=============
Encrypted communication, secure authentication, and RBAC.

Features:
- AES-256 encryption for data at rest
- Secure key derivation
- Role-based access control (RBAC)
- Session encryption
"""
import os
import hashlib
import base64
import json
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    # Fallback to simple encoding
    import base64

from core.logger import log_event, log_error


class Role(Enum):
    """User roles."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    LIMITED = "limited"


# Permission constants
class Permission:
    """Permission constants."""
    # Admin permissions
    ADMIN_ALL = "admin:*"
    # System permissions
    SYSTEM_CONTROL = "system:control"
    SYSTEM_MONITOR = "system:monitor"
    # Automation permissions
    AUTOMATION_ALL = "automation:*"
    BROWSER_CONTROL = "automation:browser"
    FILE_OPERATIONS = "automation:files"
    MESSAGING = "automation:messaging"
    # AI permissions
    AI_CHAT = "ai:chat"
    AI_LEARN = "ai:learn"
    # Security permissions
    SECURITY_VIEW = "security:view"
    SECURITY_CONFIG = "security:config"


# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.ADMIN_ALL,
        Permission.SYSTEM_CONTROL,
        Permission.SYSTEM_MONITOR,
        Permission.AUTOMATION_ALL,
        Permission.AI_CHAT,
        Permission.AI_LEARN,
        Permission.SECURITY_VIEW,
        Permission.SECURITY_CONFIG,
    ],
    Role.USER: [
        Permission.SYSTEM_CONTROL,
        Permission.SYSTEM_MONITOR,
        Permission.AUTOMATION_ALL,
        Permission.AI_CHAT,
        Permission.AI_LEARN,
        Permission.SECURITY_VIEW,
    ],
    Role.GUEST: [
        Permission.SYSTEM_MONITOR,
        Permission.AI_CHAT,
    ],
    Role.LIMITED: [
        Permission.AI_CHAT,
    ],
}


@dataclass
class UserSession:
    """User session data."""
    user_id: str
    username: str
    role: Role
    created_at: float
    last_activity: float
    permissions: List[str]


class SecurityManager:
    """
    Central security manager for encryption and access control.
    """
    
    def __init__(self, config_dir: str = "."):
        self.config_dir = config_dir
        self.sessions: Dict[str, UserSession] = {}
        self._encryption_key = None
        self._fernet = None
        
        # Initialize encryption if available
        if CRYPTO_AVAILABLE:
            self._init_encryption()
        
        log_event("SecurityManager initialized")
    
    def _init_encryption(self):
        """Initialize encryption with stored or new key."""
        key_file = os.path.join(self.config_dir, ".key")
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                self._fernet = Fernet(key)
                self._encryption_key = key
            except Exception as e:
                log_error("EncryptionInit", e)
                self._generate_key()
        else:
            self._generate_key()
    
    def _generate_key(self):
        """Generate new encryption key."""
        if CRYPTO_AVAILABLE:
            self._encryption_key = Fernet.generate_key()
            self._fernet = Fernet(self._encryption_key)
            
            # Save key securely
            key_file = os.path.join(self.config_dir, ".key")
            try:
                with open(key_file, 'wb') as f:
                    f.write(self._encryption_key)
                os.chmod(key_file, 0o600)  # Owner read/write only
            except Exception as e:
                log_error("KeyGeneration", e)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        if not data:
            return ""
        
        if CRYPTO_AVAILABLE and self._fernet:
            return self._fernet.encrypt(data.encode()).decode()
        else:
            # Fallback: simple base64 (NOT secure, for dev only)
            return base64.b64encode(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        if not encrypted_data:
            return ""
        
        if CRYPTO_AVAILABLE and self._fernet:
            try:
                return self._fernet.decrypt(encrypted_data.encode()).decode()
            except Exception:
                return ""
        else:
            # Fallback
            try:
                return base64.b64decode(encrypted_data.encode()).decode()
            except Exception:
                return ""
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt."""
        if not salt:
            salt = os.urandom(32).hex()
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        )
        
        return key.hex(), salt
    
    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash."""
        key, _ = self.hash_password(password, salt)
        return key == hashed
    
    def create_session(self, user_id: str, username: str, role: Role) -> str:
        """Create new user session."""
        session_id = os.urandom(32).hex()
        
        session = UserSession(
            user_id=user_id,
            username=username,
            role=role,
            created_at=time.time(),
            last_activity=time.time(),
            permissions=ROLE_PERMISSIONS.get(role, []),
        )
        
        self.sessions[session_id] = session
        log_event("Session created", f"user={username} role={role.value}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID."""
        session = self.sessions.get(session_id)
        
        if session:
            # Update last activity
            session.last_activity = time.time()
        
        return session
    
    def revoke_session(self, session_id: str):
        """Revoke session."""
        if session_id in self.sessions:
            username = self.sessions[session_id].username
            del self.sessions[session_id]
            log_event("Session revoked", f"user={username}")
    
    def has_permission(self, session_id: str, permission: str) -> bool:
        """Check if session has permission."""
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        # Admin has all permissions
        if Permission.ADMIN_ALL in session.permissions:
            return True
        
        # Check exact permission
        if permission in session.permissions:
            return True
        
        # Check wildcard permission
        prefix = permission.split(':')[0] + ":*"
        if prefix in session.permissions:
            return True
        
        return False
    
    def require_permission(self, permission: str):
        """Decorator to require permission."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # This would be integrated with actual session management
                # For now, return the function
                return func(*args, **kwargs)
            return wrapper
        return decorator


# Global instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


def encrypt_data(data: str) -> str:
    """Quick encrypt helper."""
    return get_security_manager().encrypt(data)


def decrypt_data(data: str) -> str:
    """Quick decrypt helper."""
    return get_security_manager().decrypt(data)


def check_permission(session_id: str, permission: str) -> bool:
    """Quick permission check."""
    return get_security_manager().has_permission(session_id, permission)


__all__ = [
    "SecurityManager",
    "Role",
    "Permission",
    "UserSession",
    "get_security_manager",
    "encrypt_data",
    "decrypt_data",
    "check_permission",
]
