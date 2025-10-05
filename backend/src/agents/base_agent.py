from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any
from ..gemini_client import Gemini


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        self._llm = llm
        self._logger = logger
        self._configured = llm is not None
    
    @property
    def is_configured(self) -> bool:
        """Check if the agent is properly configured"""
        return self._configured
    
    def _log_interaction(self, agent_name: str, prompt: str, response: str, context: Optional[dict] = None):
        """Log an AI interaction if logger is available"""
        if self._logger:
            self._logger(agent_name, prompt, response, context)
    
    @abstractmethod
    def process(self, *args, **kwargs):
        """Process method to be implemented by subclasses"""
        pass
