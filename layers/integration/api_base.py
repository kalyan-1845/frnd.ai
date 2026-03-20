"""
Integration Layer — API Base Classes
=====================================
Abstraction layer for external service integrations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import time
import json
import os

class ProviderType(Enum):
    """External service providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    EDGE_TTS = "edge_tts"
    VOSK = "vosk"
    CUSTOM = "custom"

@dataclass
class APIResponse:
    """Standardized API response."""
    success: bool
    data: Any = None
    error: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseAPIClient(ABC):
    """
    Abstract base class for API clients.
    Provides common functionality and interface contract.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._connected = False
        self._last_call = 0
        self._rate_limit_delay = 0.5  # seconds between calls
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the service."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is available."""
        pass
    
    def _rate_limit(self):
        """Apply rate limiting between calls."""
        elapsed = time.time() - self._last_call
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_call = time.time()
    
    def _load_config(self, key: str, default: Any = None) -> Any:
        """Load configuration value."""
        return self.config.get(key, default)


class CachedAPIClient(BaseAPIClient):
    """
    API client with caching support.
    """
    
    def __init__(self, config: Dict[str, Any] = None, cache_dir: str = "cache"):
        super().__init__(config)
        self.cache_dir = cache_dir
        self._cache_ttl = self._load_config("cache_ttl", 3600)  # 1 hour default
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """Generate cache file path from key."""
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if not expired."""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)
            
            # Check expiration
            if time.time() - cached.get("timestamp", 0) > self._cache_ttl:
                os.remove(cache_path)
                return None
            
            return cached.get("data")
        except Exception:
            return None
    
    def set_cached(self, key: str, data: Any):
        """Cache data with timestamp."""
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    "timestamp": time.time(),
                    "data": data
                }, f)
        except Exception:
            pass
    
    def clear_cache(self, key: str = None):
        """Clear cache."""
        if key:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
        else:
            # Clear all
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".cache"):
                    os.remove(os.path.join(self.cache_dir, filename))


class StreamingAPIClient(BaseAPIClient):
    """
    API client with streaming support.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._stream_callback = None
    
    def set_stream_callback(self, callback):
        """Set callback for streaming responses."""
        self._stream_callback = callback
    
    @abstractmethod
    def stream(self, *args, **kwargs):
        """Send streaming request."""
        pass
