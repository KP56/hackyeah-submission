"""
Error Logger Module
Handles logging and retrieval of application errors with timestamps.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime
import threading


@dataclass
class ErrorEntry:
    timestamp: str
    level: str  # ERROR, WARNING, INFO
    message: str
    source: str  # file_watcher, oauth, config, etc.
    details: str = ""


class ErrorLogger:
    """Thread-safe error logger for the application."""
    
    def __init__(self, max_errors: int = 100):
        self._max_errors = max_errors
        self._errors: List[ErrorEntry] = []
        self._lock = threading.Lock()
    
    def log_error(self, message: str, source: str = "general", details: str = "", level: str = "ERROR"):
        """Log an error with timestamp and source information."""
        with self._lock:
            error = ErrorEntry(
                timestamp=datetime.now().isoformat(),
                level=level,
                message=message,
                source=source,
                details=details
            )
            self._errors.append(error)
            
            # Keep only the most recent errors
            if len(self._errors) > self._max_errors:
                self._errors = self._errors[-self._max_errors:]
    
    def log_warning(self, message: str, source: str = "general", details: str = ""):
        """Log a warning message."""
        self.log_error(message, source, details, "WARNING")
    
    def log_info(self, message: str, source: str = "general", details: str = ""):
        """Log an info message."""
        self.log_error(message, source, details, "INFO")
    
    def get_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors as dictionaries."""
        with self._lock:
            recent_errors = self._errors[-limit:] if limit else self._errors
            return [
                {
                    "timestamp": error.timestamp,
                    "level": error.level,
                    "message": error.message,
                    "source": error.source,
                    "details": error.details
                }
                for error in reversed(recent_errors)  # Most recent first
            ]
    
    def clear_errors(self):
        """Clear all logged errors."""
        with self._lock:
            self._errors.clear()
    
    def get_error_count(self) -> int:
        """Get total number of logged errors."""
        with self._lock:
            return len(self._errors)
    
    def get_errors_by_source(self, source: str) -> List[Dict[str, Any]]:
        """Get errors filtered by source."""
        with self._lock:
            filtered_errors = [error for error in self._errors if error.source == source]
            return [
                {
                    "timestamp": error.timestamp,
                    "level": error.level,
                    "message": error.message,
                    "source": error.source,
                    "details": error.details
                }
                for error in reversed(filtered_errors)
            ]
