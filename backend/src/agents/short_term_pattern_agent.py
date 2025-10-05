"""
Short-Term Pattern Detection Agent
Detects patterns in user actions from the last 30 seconds
Focuses on REAL automation opportunities, not spam actions
"""

from __future__ import annotations
from typing import List, Optional, Callable, Dict, Any
from .base_agent import BaseAgent
from ..gemini_client import Gemini
from ..action_registry import UserAction


class ShortTermPatternAgent(BaseAgent):
    """Agent that detects patterns in short-term user actions (checks every 5s, looks at last 30s)"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
        self._last_detection_time = 0
        self._detection_cooldown = 5  # Check every 5 seconds
    
    def process(self, actions: List[UserAction]) -> Optional[Dict[str, Any]]:
        """Process method implementation for BaseAgent"""
        return self.detect_pattern(actions)
    
    def detect_pattern(self, actions: List[UserAction]) -> Optional[Dict[str, Any]]:
        """
        Detect patterns in short-term actions (30 seconds window)
        Returns a pattern detection result or None if no pattern detected
        
        Focus: Real automation opportunities (file operations, app switching with work, copy-paste workflows)
        Reject: Spam actions (repeated alt+tab, repeated ctrl+c without purpose)
        """
        if not self._configured or not actions:
            return None
        
        # Don't detect too frequently
        import time
        current_time = time.time()
        if current_time - self._last_detection_time < self._detection_cooldown:
            return None
        
        # Need at least 3 actions to form a pattern
        if len(actions) < 3:
            return None
        
        # Create prompt for pattern detection
        prompt = self._create_detection_prompt(actions)
        response = self._llm.prompt(prompt)
        
        # Check if a pattern was detected
        pattern_detected = self._parse_detection_response(response)
        
        if pattern_detected:
            self._last_detection_time = current_time
            
            # Enhanced logging with context
            context = {
                "action_count": len(actions),
                "action_types": list(set(a.action_type for a in actions)),
                "time_span": max(a.timestamp for a in actions) - min(a.timestamp for a in actions) if len(actions) > 1 else 0,
                "pattern_detected": True,
                "pattern_description": pattern_detected.get("description", "")
            }
            self._log_interaction("ShortTermPatternAgent", prompt, response, context)
            
            return pattern_detected
        
        return None
    
    
    def _create_detection_prompt(self, actions: List[UserAction]) -> str:
        """Create a prompt for short-term pattern detection (Gemini 2.5 Flash)"""
        lines = [
            "You are an intelligent automation pattern detector using Gemini 2.5 Flash. Your job is to identify REAL automation opportunities.",
            "",
            "🎯 WHAT IS A REAL PATTERN (DETECT THESE):",
            "",
            "✅ FILE OPERATIONS IN SAME/NEARBY DIRECTORY:",
            "   • User working with 2-3 files in the same directory or similar paths",
            "   • Renaming, moving, copying files following a pattern",
            "   • Creating folders and organizing files",
            "   Example: Renaming IMG_001.jpg → vacation_001.jpg, IMG_002.jpg → vacation_002.jpg",
            "",
            "✅ APP SWITCHING WITH MEANINGFUL WORK:",
            "   • User switches between 2 apps AND does copy-paste (Ctrl+C, Ctrl+V) between them",
            "   • Example: Excel → Ctrl+C → Word → Ctrl+V → Excel → Ctrl+C → Word → Ctrl+V (2+ cycles)",
            "   • Must have BOTH app switching AND copy-paste actions",
            "",
            "✅ REPETITIVE WORKFLOW:",
            "   • User does the same sequence of file operations multiple times",
            "   • User performs same keyboard shortcuts in pattern with actual work",
            "",
            "🚫 WHAT IS NOT A PATTERN (REJECT THESE):",
            "",
            "❌ SPAM ACTIONS:",
            "   • User repeatedly pressing Alt+Tab (just switching windows)",
            "   • User repeatedly pressing Ctrl+C without context",
            "   • Single app switches with no work",
            "   • Random navigation or browsing",
            "",
            "❌ ISOLATED ACTIONS:",
            "   • Single file operation with no repetition",
            "   • One copy-paste action",
            "   • Just opening apps without doing work",
            "",
            "IMPORTANT RULES:",
            "1. Only suggest patterns with a REAL chance to optimize/automate",
            "2. Pattern must involve at least 3 meaningful actions",
            "3. For app switching: Must have copy-paste actions too (2+ cycles)",
            "4. For file operations: Must involve 2-3+ files in same/nearby directory",
            "5. REJECT spam/repetitive single actions (alt+tab spam, ctrl+c spam)",
            "",
            "IF YOU DETECT A REAL AUTOMATABLE PATTERN:",
            "- Describe what you saw the user doing (be specific about files/apps)",
            "- Explain why this could be automated",
            "- Keep it conversational and helpful",
            "- End with: PATTERN_DETECTED",
            "",
            "IF NO REAL PATTERN EXISTS:",
            "- Say 'No automatable pattern detected'",
            "- Do NOT end with PATTERN_DETECTED",
            "",
            "Recent user actions (last 30 seconds):",
        ]
        
        for i, action in enumerate(actions, 1):
            lines.append(f"\n{i}. Type: {action.action_type}")
            lines.append(f"   Time: {self._format_timestamp(action.timestamp)}")
            lines.append(f"   Details: {self._format_details(action.details)}")
            if action.metadata:
                lines.append(f"   Metadata: {action.metadata}")
        
        return "\n".join(lines)
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp for display"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
    
    def _format_details(self, details: Dict[str, Any]) -> str:
        """Format action details for display"""
        # Truncate long values
        formatted = {}
        for key, value in details.items():
            if isinstance(value, str) and len(value) > 100:
                formatted[key] = value[:100] + "..."
            else:
                formatted[key] = value
        return str(formatted)
    
    def _parse_detection_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse the detection response to check if pattern was detected"""
        if "PATTERN_DETECTED" not in response:
            return None
        
        # Extract the description (everything before "PATTERN_DETECTED")
        description = response.split("PATTERN_DETECTED")[0].strip()
        
        return {
            "detected": True,
            "description": description,
            "confidence": "high" if len(description) > 50 else "medium",
            "timestamp": None  # Will be set by caller
        }
    
    def set_detection_cooldown(self, seconds: int):
        """Set the cooldown period between detections"""
        self._detection_cooldown = seconds

