from __future__ import annotations
from typing import List, Optional, Callable
from .base_agent import BaseAgent
from ..gemini_client import Gemini
from ..recent_ops import FileOp


class AutomationAgent(BaseAgent):
    """Agent that creates automation scripts from spotted patterns"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
    
    def process(self, pattern_description: str, operations: List[FileOp]) -> str:
        """Process method implementation for BaseAgent"""
        return self.create_automation_script(pattern_description, operations)
    
    def create_automation_script(self, pattern_description: str, operations: List[FileOp]) -> str:
        """Create a Python automation script based on the spotted pattern"""
        if not self._configured:
            return "# Automation agent not configured"
        
        prompt = self._create_script_prompt(pattern_description, operations)
        response = self._llm.prompt(prompt)
        
        # Strip markdown code blocks if present
        response = self._clean_script(response)
        
        # Enhanced logging with context
        context = {
            "pattern_description_length": len(pattern_description),
            "operation_count": len(operations),
            "script_length": len(response),
            "pattern_summary": pattern_description[:100] + "..." if len(pattern_description) > 100 else pattern_description,
            "operations_summary": [f"{op.event_type}: {op.src_path}" for op in operations[:3]]  # First 3 operations
        }
        self._log_interaction("AutomationAgent", prompt, response, context)
        return response
    
    def _clean_script(self, script: str) -> str:
        """Remove markdown code blocks and clean the script"""
        script = script.strip()
        
        # Remove ```python or ``` at start
        if script.startswith('```python'):
            script = script[9:].strip()
        elif script.startswith('```'):
            script = script[3:].strip()
        
        # Remove ``` at end
        if script.endswith('```'):
            script = script[:-3].strip()
        
        return script
    
    def _create_script_prompt(self, pattern_description: str, operations: List[FileOp]) -> str:
        """Create a prompt for generating automation scripts"""
        lines = [
            "You are a Python automation script generator. Create SIMPLE, SAFE Python scripts from user patterns.",
            "",
            "🚨 CRITICAL SAFETY RULES:",
            "1. ALWAYS use FULL ABSOLUTE PATHS - NO relative paths, NO path manipulation",
            "2. Use SIMPLE Python code - avoid complex logic that could fail",
            "3. MINIMIZE risk of errors that could damage user's PC",
            "4. If you see file paths in the pattern, use EXACTLY those paths",
            "",
            "CRITICAL: Output ONLY the raw Python code. DO NOT use markdown code blocks like ```python.",
            "Start directly with the import statements or code.",
            "",
            "CODE REQUIREMENTS:",
            "- Create a complete, runnable Python script that executes AUTOMATICALLY",
            "- DO NOT ask for user confirmation or input (no input(), no prompts)",
            "- DO NOT print warnings or ask 'are you sure?' - just execute",
            "- The script should run silently and complete the task automatically",
            "- PREFER standard library modules (os, shutil, pathlib, glob, re, etc.) to avoid dependencies",
            "- Use FULL PATHS everywhere (e.g., 'C:\\Users\\user\\Documents\\file.txt')",
            "- NO relative paths like './file.txt' or '../folder/'",
            "- If you need external packages, use CORRECT pip package names:",
            "  * For images: use 'Pillow' (NOT 'PIL')",
            "  * For Excel: use 'openpyxl' (NOT 'excel')",
            "  * For PDFs: use 'PyPDF2' or 'pypdf' (NOT 'pdf')",
            "  * For CSV: use standard 'csv' module (NO package needed)",
            "  * For JSON: use standard 'json' module (NO package needed)",
            "- Include proper error handling with try/except blocks",
            "- Add brief comments explaining key steps",
            "- Include a main() function and if __name__ == '__main__' guard",
            "",
            "Pattern Description:",
            pattern_description,
            "",
            "File Operations:",
        ]
        
        for op in operations:
            lines.append(f"- {op.event_type} | {op.src_path} | {op.dest_path or ''}")
        
        lines.extend([
            "",
            "Generate a Python script that automates this pattern:",
        ])
        
        return "\n".join(lines)
