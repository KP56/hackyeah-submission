from __future__ import annotations
from typing import List, Optional, Callable
from .base_agent import BaseAgent
from ..gemini_client import Gemini
from ..recent_ops import FileOp


class PatternDetectorAgent(BaseAgent):
    """Agent that reasons about whether there are patterns in file operations"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
    
    def process(self, operations: List[FileOp]) -> str:
        """Process method implementation for BaseAgent"""
        return self.analyze_patterns(operations)
    
    def analyze_patterns(self, operations: List[FileOp]) -> str:
        """Analyze file operations and reason about potential patterns"""
        if not self._configured or not operations:
            return "No operations to analyze or agent not configured."
        
        prompt = self._create_analysis_prompt(operations)
        response = self._llm.prompt(prompt)
        
        # Enhanced logging with context
        context = {
            "operation_count": len(operations),
            "operation_types": list(set(op.event_type for op in operations)),
            "file_extensions": list(set(op.file_extension for op in operations if op.file_extension)),
            "directories": list(set(op.src_path.split('/')[-2] if '/' in op.src_path else 'root' for op in operations)),
            "time_range": f"{min(op.timestamp for op in operations)} to {max(op.timestamp for op in operations)}" if operations else "N/A"
        }
        self._log_interaction("PatternDetectorAgent", prompt, response, context)
        return response
    
    def _create_analysis_prompt(self, operations: List[FileOp]) -> str:
        """Create a prompt for pattern analysis"""
        lines = [
            "You are a pattern analysis agent that examines file operations to identify potential automation opportunities.",
            "Your job is to REASON about whether there are meaningful patterns that could be automated.",
            "",
            "Analyze the following file operations and provide your reasoning about:",
            "1. Whether there are repetitive patterns",
            "2. If the patterns show clear user intent",
            "3. Whether the patterns could be converted into useful automation",
            "4. The complexity and feasibility of automation",
            "",
            "Focus on patterns that:",
            "- Show clear, repetitive user actions",
            "- Involve meaningful file operations (not system/cache files)",
            "- Represent workflows the user would want to automate",
            "- Can be converted into simple algorithms",
            "",
            "Ignore patterns that are:",
            "- Random or one-off operations",
            "- System-generated (cache, temp, build files)",
            "- Too complex or vague to automate",
            "- Not representative of user intent",
            "",
            "Provide your analysis in a clear, structured way.",
            "Be specific about what patterns you observe and why they might be automatable.",
            "",
            "File operations:",
        ]
        
        for op in operations:
            lines.append(f"- {op.event_type} | {op.src_path} | {op.dest_path or ''}")
        
        return "\n".join(lines)
