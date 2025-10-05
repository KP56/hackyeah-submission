from __future__ import annotations
from typing import List, Optional, Callable
from .base_agent import BaseAgent
from ..gemini_client import Gemini
from ..recent_ops import FileOp


class PatternSpotterAgent(BaseAgent):
    """Agent that makes the final decision about whether to spot a pattern"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
    
    def process(self, analysis: str, operations: List[FileOp]) -> str:
        """Process method implementation for BaseAgent"""
        return self.spot_pattern(analysis, operations)
    
    def spot_pattern(self, analysis: str, operations: List[FileOp]) -> str:
        """Make final decision about whether to spot a pattern based on analysis"""
        if not self._configured:
            return "Agent not configured."
        
        prompt = self._create_spotting_prompt(analysis, operations)
        response = self._llm.prompt(prompt)
        
        # Enhanced logging with context
        context = {
            "analysis_length": len(analysis),
            "operation_count": len(operations),
            "pattern_spotted": self.has_spotted_pattern(response),
            "analysis_summary": analysis[:200] + "..." if len(analysis) > 200 else analysis
        }
        self._log_interaction("PatternSpotterAgent", prompt, response, context)
        return response
    
    def _create_spotting_prompt(self, analysis: str, operations: List[FileOp]) -> str:
        """Create a prompt for final pattern spotting decision"""
        lines = [
            "You are a pattern spotting agent that makes the final decision about whether to spot an automation pattern.",
            "You have received an analysis of file operations and must decide if there's a clear, automatable pattern.",
            "",
            "CRITICAL REQUIREMENTS:",
            "- Only spot patterns that are VERY SPECIFIC and ALGORITHM-LIKE",
            "- Patterns must be easily convertible to short Python scripts",
            "- Patterns must show clear, repetitive user intent",
            "- Patterns must involve meaningful file operations",
            "",
            "If you find a clear, automatable pattern:",
            "1. Describe the specific algorithmic steps",
            "2. Explain why it's automatable",
            "3. End your response with: 'I have spotted the pattern'",
            "",
            "If no clear pattern exists:",
            "1. Explain why the operations don't form a clear pattern",
            "2. Do NOT end with 'I have spotted the pattern'",
            "",
            "Pattern Analysis:",
            analysis,
            "",
            "File Operations:",
        ]
        
        for op in operations:
            lines.append(f"- {op.event_type} | {op.src_path} | {op.dest_path or ''}")
        
        return "\n".join(lines)
    
    def has_spotted_pattern(self, response: str) -> bool:
        """Check if the response contains the pattern spotting phrase"""
        return "I have spotted the pattern" in response
