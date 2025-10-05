"""
Long-Term Pattern Detection Agent
Creates hierarchical summaries of user activity:
- Every 1 minute: Summarize actions from the last minute (1-2 sentences)
- Every 10 minutes: Summarize the last 10 minute-summaries (4-5 sentences)
"""

from __future__ import annotations
from typing import List, Optional, Callable, Dict, Any
from .base_agent import BaseAgent
from ..gemini_client import Gemini
from ..action_registry import UserAction
import time


class LongTermPatternAgent(BaseAgent):
    """
    Agent that creates hierarchical summaries of user activity over time
    """
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
        self._enabled = True
    
    def process(self, actions: List[UserAction]) -> Optional[Dict[str, Any]]:
        """Process method implementation for BaseAgent"""
        return self.detect_long_term_pattern(actions)
    
    def detect_long_term_pattern(self, actions: List[UserAction]) -> Optional[Dict[str, Any]]:
        """
        Detect patterns in long-term actions
        """
        if not self._enabled:
            return None
        
        # This is for API status endpoint
        return {
            "status": "active",
            "message": "Long-term pattern detection is active!",
            "features": [
                "1-minute activity summaries",
                "10-minute consolidated summaries",
                "Historical activity tracking"
            ]
        }
    
    def create_minute_summary(self, actions: List[UserAction]) -> Optional[str]:
        """
        Create a 1-2 sentence summary of actions from the last minute
        
        Args:
            actions: List of user actions from the last minute
            
        Returns:
            A 1-2 sentence summary or None if no actions or LLM not configured
        """
        if not self._configured or not actions:
            return None
        
        # Create prompt for minute summary
        prompt = self._create_minute_summary_prompt(actions)
        
        try:
            summary = self._llm.prompt(prompt)
            
            # Log the interaction
            context = {
                "action_count": len(actions),
                "action_types": list(set(a.action_type for a in actions)),
                "summary_type": "1-minute"
            }
            self._log_interaction("LongTermPatternAgent-Minute", prompt, summary, context)
            
            return summary.strip()
        except Exception as e:
            print(f"Error creating minute summary: {e}")
            return None
    
    def create_ten_minute_summary(self, minute_summaries: List[str]) -> Optional[str]:
        """
        Create a 4-5 sentence summary from 10 minute-summaries
        
        Args:
            minute_summaries: List of 1-minute summaries
            
        Returns:
            A 4-5 sentence summary or None if no summaries or LLM not configured
        """
        if not self._configured or not minute_summaries:
            return None
        
        # Create prompt for 10-minute summary
        prompt = self._create_ten_minute_summary_prompt(minute_summaries)
        
        try:
            summary = self._llm.prompt(prompt)
            
            # Log the interaction
            context = {
                "minute_summaries_count": len(minute_summaries),
                "summary_type": "10-minute"
            }
            self._log_interaction("LongTermPatternAgent-TenMinute", prompt, summary, context)
            
            return summary.strip()
        except Exception as e:
            print(f"Error creating 10-minute summary: {e}")
            return None
    
    def _create_minute_summary_prompt(self, actions: List[UserAction]) -> str:
        """Create a prompt for summarizing 1 minute of activity"""
        lines = [
            "You are an activity summarizer. Your job is to create a VERY BRIEF summary of what the user did in the last minute.",
            "",
            "RULES:",
            "- Output ONLY 1-2 sentences, no more",
            "- Be specific: mention file names, application names, or actions taken",
            "- Use past tense (e.g., 'User opened Chrome', 'User edited 3 files')",
            "- Focus on meaningful actions, ignore trivial ones",
            "- If no meaningful actions, say 'User was idle' or 'User was browsing'",
            "",
            "Recent user actions from the last minute:",
            ""
        ]
        
        # Group actions by type for better summarization
        action_groups = {}
        for action in actions:
            action_type = action.action_type
            if action_type not in action_groups:
                action_groups[action_type] = []
            action_groups[action_type].append(action)
        
        # Format actions by group
        for action_type, group_actions in action_groups.items():
            lines.append(f"\n{action_type.upper()} ({len(group_actions)} actions):")
            for action in group_actions[:5]:  # Limit to 5 per group to avoid prompt bloat
                if action_type == "file_operation":
                    lines.append(f"  - {action.details.get('event_type')}: {action.details.get('src_path', 'unknown')}")
                elif action_type == "app_switch":
                    lines.append(f"  - Opened {action.details.get('app_name', 'unknown')}")
                elif action_type == "keyboard_shortcut":
                    lines.append(f"  - Pressed {action.details.get('shortcut', 'unknown')}")
                else:
                    lines.append(f"  - {action.details.get('description', 'unknown action')}")
        
        lines.append("\n\nSummarize in 1-2 sentences:")
        return "\n".join(lines)
    
    def _create_ten_minute_summary_prompt(self, minute_summaries: List[str]) -> str:
        """Create a prompt for summarizing 10 minutes of activity"""
        lines = [
            "You are an activity summarizer. Your job is to create a CONCISE summary of what the user did over the last 10 minutes.",
            "",
            "RULES:",
            "- Output EXACTLY 4-5 sentences, no more",
            "- Identify patterns and workflows (e.g., 'User was working on a Python project')",
            "- Mention the most important activities",
            "- Use past tense",
            "- Group similar activities together",
            "",
            "Here are 10 summaries of 1-minute intervals:",
            ""
        ]
        
        for i, summary in enumerate(minute_summaries, 1):
            lines.append(f"Minute {i}: {summary}")
        
        lines.append("\n\nCreate a 4-5 sentence summary of the entire 10-minute period:")
        return "\n".join(lines)
    
    def enable(self):
        """Enable long-term pattern detection"""
        self._enabled = True
    
    def disable(self):
        """Disable long-term pattern detection"""
        self._enabled = False
    
    def is_available(self) -> bool:
        """Check if long-term pattern detection is available"""
        return self._enabled and self._configured

