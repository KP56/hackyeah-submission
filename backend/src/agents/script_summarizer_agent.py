"""
Script Summarizer Agent
Creates user-friendly summaries of Python scripts
"""

from __future__ import annotations
from typing import Optional, Callable
from .base_agent import BaseAgent
from ..gemini_client import Gemini


class ScriptSummarizerAgent(BaseAgent):
    """Agent that creates human-readable summaries of Python scripts"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
    
    def process(self, script: str) -> str:
        """Process method implementation for BaseAgent"""
        return self.summarize_script(script)
    
    def summarize_script(self, script: str) -> str:
        """Create a user-friendly summary of what the script will do"""
        if not self._configured:
            return "Script summarizer not configured"
        
        prompt = self._create_summary_prompt(script)
        response = self._llm.prompt(prompt)
        
        # Log the interaction
        context = {
            "script_length": len(script),
            "summary_length": len(response)
        }
        self._log_interaction("ScriptSummarizerAgent", prompt, response, context)
        
        return response
    
    def _create_summary_prompt(self, script: str) -> str:
        """Create a prompt for script summarization with detailed explanation"""
        lines = [
            "You are a helpful AI assistant explaining a Python automation script in SIMPLE, NON-TECHNICAL language.",
            "Write a SHORT summary (4-6 sentences) that a normal person can understand.",
            "",
            "REQUIREMENTS:",
            "1. Write EXACTLY 4-6 sentences (not more, not less)",
            "2. Use SIMPLE everyday language - no technical terms",
            "3. Explain WHAT the script will do (not HOW it works)",
            "4. Mention specific files, folders, or paths if they're in the code",
            "5. Make it clear so the user knows if it does what they want",
            "6. Don't use bullet points - write in paragraph form",
            "",
            "GOOD EXAMPLE (4-6 sentences):",
            "This script will look through your Downloads folder and find all image files that start with 'IMG_'. It will rename them to start with 'vacation_' instead, keeping the numbers the same. For example, IMG_001.jpg becomes vacation_001.jpg. The script will process all matching files in that folder. All your images will stay in the same place, just with new names. Files that don't start with 'IMG_' won't be touched.",
            "",
            "BAD EXAMPLE (too technical or too long):",
            "This script uses the os module to iterate through the directory structure. It will employ a for loop to process each file. The pathlib library handles path operations. It implements error handling with try-except blocks. The script utilizes string manipulation methods...",
            "",
            "Python script to summarize:",
            "```python",
            script,
            "```",
            "",
            "Write your SHORT 4-6 sentence summary (use simple language, no technical terms):",
        ]
        
        return "\n".join(lines)

