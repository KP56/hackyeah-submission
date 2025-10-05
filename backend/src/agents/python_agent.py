from __future__ import annotations
from typing import Optional, List, Dict, Any, Callable
from .base_agent import BaseAgent
from ..gemini_client import Gemini
from ..automation_executor import AutomationExecutor


class PythonAgent(BaseAgent):
    """Agent that executes Python code safely using AutomationExecutor"""
    
    def __init__(self, llm: Optional[Gemini] = None, logger: Optional[Callable[[str, str, str], None]] = None):
        super().__init__(llm, logger)
        self._automation_executor = AutomationExecutor(max_retries=1, verbose=False)
        self._execution_history = []
        self._next_execution_id = 1
    
    def execute_script(self, script: str, script_name: str = "python_agent_script") -> Dict[str, Any]:
        """Execute a Python script safely using AutomationExecutor"""
        if not script.strip():
            return {"status": "error", "message": "Empty script", "output": ""}
        
        # Use AutomationExecutor for script execution
        result = self._automation_executor.execute_automation(
            script=script,
            user_explanation=f"PythonAgent execution: {script_name}"
        )
        
        # Convert AutomationExecutor result format to PythonAgent format
        converted_result = {
            "status": "success" if result["success"] else "error",
            "message": "Script executed successfully" if result["success"] else result.get("final_error", "Execution failed"),
            "output": result.get("final_output", ""),
            "error": result.get("final_error", ""),
            "execution_id": result.get("execution_id", 0)
        }
        
        # Log the execution
        if self._logger:
            self._log_interaction(
                "PythonAgent", 
                f"Executed script: {script_name}", 
                f"Success: {converted_result['status'] == 'success'}, Output: {converted_result['output'][:100]}..."
            )
        
        return converted_result
        
    def process(self, script: str) -> str:
        """Process method implementation for BaseAgent"""
        return self.get_suggestions(script)
    
    def get_suggestions(self, script: str) -> str:
        """Get suggestions for improving a Python script"""
        if not self._configured:
            return "Python agent not configured"
        
        prompt = self._create_suggestion_prompt(script)
        response = self._llm.prompt(prompt)
        self._log_interaction("PythonAgent", prompt, response)
        return response
    
    def _create_suggestion_prompt(self, script: str) -> str:
        """Create a prompt for script improvement suggestions"""
        lines = [
            "You are a Python code reviewer that provides suggestions for improving automation scripts.",
            "Analyze the following Python script and provide constructive feedback.",
            "",
            "Focus on:",
            "- Code quality and readability",
            "- Error handling and robustness",
            "- Performance and efficiency",
            "- Best practices and Python idioms",
            "- Security considerations",
            "- Documentation and comments",
            "",
            "Provide specific, actionable suggestions.",
            "",
            "Python script:",
            "```python",
            script,
            "```",
            "",
            "Suggestions:",
        ]
        
        return "\n".join(lines)
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get the execution history from AutomationExecutor"""
        return self._automation_executor.get_execution_history()
    
    def get_execution_by_id(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific execution record by ID from AutomationExecutor"""
        return self._automation_executor.get_execution_by_id(execution_id)
    
    def clear_execution_history(self) -> None:
        """Clear the execution history in AutomationExecutor"""
        self._automation_executor.clear_history()
    
    def reload_security_config(self) -> None:
        """Reload security configuration in AutomationExecutor"""
        self._automation_executor.reload_security_config()
