"""
Comprehensive error handling wrapper for agent operations.
Prevents agent errors from crashing the FastAPI server.
"""

import traceback
import time
import logging
from typing import Any, Callable, Optional, Dict
from functools import wraps
from datetime import datetime


class AgentErrorHandler:
    """Handles errors from agent operations without crashing the server."""
    
    def __init__(self, error_logger=None):
        self.error_logger = error_logger
        self.error_count = 0
        self.last_error_time = None
        self.error_threshold = 10  # Max errors per minute
        self.error_window = 60  # seconds
        
    def handle_agent_error(self, agent_name: str, operation: str, error: Exception, context: Optional[Dict] = None):
        """Handle an error from an agent operation."""
        self.error_count += 1
        self.last_error_time = time.time()
        
        error_msg = f"[{agent_name}] Error in {operation}: {str(error)}"
        print(error_msg)
        
        # Log to error logger if available
        if self.error_logger:
            try:
                self.error_logger.log_error(
                    agent_name=agent_name,
                    operation=operation,
                    error=str(error),
                    traceback=traceback.format_exc(),
                    context=context or {}
                )
            except Exception as log_error:
                print(f"Failed to log error: {log_error}")
        
        # Check if we're hitting error threshold
        if self._is_error_threshold_exceeded():
            print(f"WARNING: Error threshold exceeded for {agent_name}. Consider investigating.")
    
    def _is_error_threshold_exceeded(self) -> bool:
        """Check if error threshold is exceeded."""
        if not self.last_error_time:
            return False
        
        # Reset counter if outside error window
        if time.time() - self.last_error_time > self.error_window:
            self.error_count = 0
            return False
        
        return self.error_count >= self.error_threshold
    
    def safe_execute(self, agent_name: str, operation: str, func: Callable, *args, **kwargs) -> Any:
        """Safely execute an agent function with error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_agent_error(agent_name, operation, e, {
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            })
            return None
    
    def safe_execute_with_fallback(self, agent_name: str, operation: str, func: Callable, fallback_value: Any, *args, **kwargs) -> Any:
        """Safely execute with a fallback value on error."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_agent_error(agent_name, operation, e, {
                'function': func.__name__,
                'fallback_used': True
            })
            return fallback_value


def safe_agent_operation(agent_name: str, operation: str, error_handler: AgentErrorHandler):
    """Decorator for safe agent operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_agent_error(agent_name, operation, e, {
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                })
                return None
        return wrapper
    return decorator


def safe_worker_operation(worker_name: str, error_handler: AgentErrorHandler):
    """Decorator for safe background worker operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            while True:  # Workers run in loops
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_handler.handle_agent_error(worker_name, func.__name__, e, {
                        'worker': True,
                        'args_count': len(args),
                        'kwargs_count': len(kwargs)
                    })
                    # Wait a bit before retrying to prevent rapid error loops
                    time.sleep(5)
        return wrapper
    return decorator


def safe_agent_method_call(agent, method_name: str, error_handler: AgentErrorHandler, *args, **kwargs):
    """Safely call an agent method with error handling."""
    if not agent:
        print(f"Agent is None, cannot call {method_name}")
        return None
    
    try:
        method = getattr(agent, method_name)
        return method(*args, **kwargs)
    except Exception as e:
        agent_name = getattr(agent, 'agent_name', agent.__class__.__name__)
        error_handler.handle_agent_error(agent_name, method_name, e, {
            'method': method_name,
            'args_count': len(args),
            'kwargs_count': len(kwargs)
        })
        return None


def safe_agent_method_call_with_fallback(agent, method_name: str, error_handler: AgentErrorHandler, fallback_value, *args, **kwargs):
    """Safely call an agent method with fallback value on error."""
    if not agent:
        print(f"Agent is None, cannot call {method_name}, using fallback")
        return fallback_value
    
    try:
        method = getattr(agent, method_name)
        return method(*args, **kwargs)
    except Exception as e:
        agent_name = getattr(agent, 'agent_name', agent.__class__.__name__)
        error_handler.handle_agent_error(agent_name, method_name, e, {
            'method': method_name,
            'fallback_used': True,
            'args_count': len(args),
            'kwargs_count': len(kwargs)
        })
        return fallback_value


# Global error handler instance
global_error_handler = AgentErrorHandler()
