from __future__ import annotations
from typing import List, Optional, Callable
from .base_agent import BaseAgent
from ..gemini_client import Gemini
from ..recent_ops import FileOp


class ActionFilterAgent(BaseAgent):
    """Agent that filters out program-generated actions from user actions"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
    
    def process(self, operations: List[FileOp]) -> List[FileOp]:
        """Process method implementation for BaseAgent"""
        return self.filter_user_actions(operations)
    
    def filter_user_actions(self, operations: List[FileOp]) -> List[FileOp]:
        """Filter out program-generated actions, keeping only user-initiated ones"""
        if not operations:
            return []
        
        # First, apply rule-based filtering
        filtered_ops = self._rule_based_filter(operations)
        
        # Log the rule-based filtering results
        if self._logger:
            context = {
                "input_count": len(operations),
                "rule_filtered_count": len(filtered_ops),
                "filtered_operations": [f"{op.event_type}: {op.src_path}" for op in filtered_ops[:5]]  # First 5 for context
            }
            self._log_interaction("ActionFilterAgent", f"Rule-based filtering: {len(operations)} -> {len(filtered_ops)} operations", f"Filtered out {len(operations) - len(filtered_ops)} program-generated operations", context)
        
        # If we have an LLM, use it for additional filtering
        if self._llm and len(filtered_ops) > 0:
            original_count = len(filtered_ops)
            filtered_ops = self._llm_based_filter(filtered_ops)
            
            # Log the LLM-based filtering results
            if self._logger:
                context = {
                    "rule_filtered_count": original_count,
                    "llm_filtered_count": len(filtered_ops),
                    "final_operations": [f"{op.event_type}: {op.src_path}" for op in filtered_ops[:5]]  # First 5 for context
                }
                self._log_interaction("ActionFilterAgent", f"LLM-based filtering: {original_count} -> {len(filtered_ops)} operations", f"Further filtered out {original_count - len(filtered_ops)} operations using AI analysis", context)
        
        return filtered_ops
    
    def _rule_based_filter(self, operations: List[FileOp]) -> List[FileOp]:
        """Apply rule-based filtering to remove obvious program-generated actions"""
        filtered = []
        
        for op in operations:
            # Skip if it's a system operation
            if op.operation_category == "system":
                continue
            
            # Skip common program-generated file patterns
            if self._is_program_generated(op.src_path):
                continue
            
            # Skip if it's a temporary or cache file
            if self._is_temporary_file(op.src_path):
                continue
            
            # Skip if it's a build artifact
            if self._is_build_artifact(op.src_path):
                continue
            
            # Skip if it's a log file
            if self._is_log_file(op.src_path):
                continue
            
            filtered.append(op)
        
        return filtered
    
    def _is_program_generated(self, path: str) -> bool:
        """Check if a file path indicates program-generated content"""
        path_lower = path.lower()
        
        # Common program-generated patterns
        program_patterns = [
            '__pycache__',
            '.pyc',
            '.pyo',
            '.pack',
            '.idx',
            'node_modules',
            '.git/',
            '.vscode/',
            '.idea/',
            'target/',
            'build/',
            'dist/',
            '.next/',
            '.nuxt/',
            'venv/',
            'env/',
            '.env',
            'package-lock.json',
            'yarn.lock',
            'composer.lock',
            'Pipfile.lock',
            '.DS_Store',
            'Thumbs.db',
            '.tmp',
            '.temp'
        ]
        
        return any(pattern in path_lower for pattern in program_patterns)
    
    def _is_temporary_file(self, path: str) -> bool:
        """Check if a file is temporary"""
        path_lower = path.lower()
        
        temp_patterns = [
            '.tmp',
            '.temp',
            '.cache',
            '.swp',
            '.swo',
            '~',
            '.bak',
            '.backup'
        ]
        
        return any(pattern in path_lower for pattern in temp_patterns)
    
    def _is_build_artifact(self, path: str) -> bool:
        """Check if a file is a build artifact"""
        path_lower = path.lower()
        
        build_patterns = [
            '.o',
            '.obj',
            '.exe',
            '.dll',
            '.so',
            '.dylib',
            '.a',
            '.lib',
            '.jar',
            '.war',
            '.ear',
            '.class',
            '.pyc',
            '.pyo'
        ]
        
        return any(path_lower.endswith(pattern) for pattern in build_patterns)
    
    def _is_log_file(self, path: str) -> bool:
        """Check if a file is a log file"""
        path_lower = path.lower()
        
        log_patterns = [
            '.log',
            '.logs/',
            'log/',
            'logs/',
            'debug.log',
            'error.log',
            'access.log',
            'application.log'
        ]
        
        return any(pattern in path_lower for pattern in log_patterns)
    
    def _llm_based_filter(self, operations: List[FileOp]) -> List[FileOp]:
        """Use LLM to further filter operations that might be program-generated"""
        if len(operations) <= 5:  # Don't use LLM for small sets
            return operations
        
        # Create a prompt for the LLM to analyze the operations
        prompt = self._create_filter_prompt(operations)
        
        try:
            response = self._llm.prompt(prompt)
            self._log_interaction("ActionFilter", prompt, response)
            # Parse the response to determine which operations to keep
            return self._parse_llm_filter_response(operations, response)
        except Exception:
            # If LLM fails, return the original filtered operations
            return operations
    
    def _create_filter_prompt(self, operations: List[FileOp]) -> str:
        """Create a prompt for the LLM to filter operations"""
        lines = [
            "You are an action filter that identifies user-initiated file operations vs program-generated ones.",
            "Analyze the following file operations and determine which ones were likely initiated by a human user.",
            "",
            "Keep operations that:",
            "- Show clear user intent (editing source code, creating documents, organizing files)",
            "- Involve meaningful file types (.py, .js, .html, .css, .md, .txt, .json, etc.)",
            "- Appear to be part of a deliberate workflow",
            "",
            "Remove operations that:",
            "- Are clearly automated or program-generated",
            "- Involve system files, cache, or temporary files",
            "- Show patterns typical of build processes or automated tools",
            "- Are too frequent or systematic to be human-initiated",
            "",
            "Respond with a JSON array of indices (0-based) of operations to KEEP.",
            "For example: [0, 2, 5, 7]",
            "",
            "File operations:",
        ]
        
        for i, op in enumerate(operations):
            lines.append(f"{i}: {op.event_type} | {op.src_path} | {op.dest_path or ''}")
        
        return "\n".join(lines)
    
    def _parse_llm_filter_response(self, operations: List[FileOp], response: str) -> List[FileOp]:
        """Parse LLM response to get filtered operations"""
        try:
            import json
            # Extract JSON array from response
            response = response.strip()
            if response.startswith('[') and response.endswith(']'):
                indices = json.loads(response)
                if isinstance(indices, list):
                    return [operations[i] for i in indices if 0 <= i < len(operations)]
        except Exception:
            pass
        
        # If parsing fails, return original operations
        return operations
