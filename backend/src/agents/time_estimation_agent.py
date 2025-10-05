"""
Time Estimation Agent
Analyzes executed automation scripts and estimates realistic time savings for non-technical users.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import re
import time
from datetime import datetime

from .base_agent import BaseAgent


class TimeEstimationAgent(BaseAgent):
    """
    Agent that estimates how much time a non-technical user would have spent
    performing the tasks that were automated by a script.
    """
    
    def __init__(self, llm, logger=None):
        super().__init__(llm, logger)
        self.agent_name = "TimeEstimationAgent"
        
        # Time estimation categories with realistic ranges for non-technical users
        self.OPERATION_TIME_ESTIMATES = {
            # File operations (in seconds) - EXTREMELY CONSERVATIVE ESTIMATES
            'file_operations': {
                'copy': (3, 8),          # Very quick copy-paste
                'move': (5, 12),         # Quick drag and drop
                'rename': (5, 15),       # F2, type, enter
                'delete': (2, 5),        # Select and delete
                'create_folder': (5, 12), # Right-click, new folder, name
                'search': (8, 20),       # Quick search operations
            },
            
            # Data processing (in seconds) - EXTREMELY CONSERVATIVE ESTIMATES
            'data_processing': {
                'csv_processing': (10, 30),    # Very quick Excel operations
                'text_processing': (5, 15),   # Simple text editing
                'image_processing': (8, 20),   # Basic image operations
                'batch_operations': (15, 45), # Multiple files, but very efficient
            },
            
            # Web/Email operations (in seconds) - EXTREMELY CONSERVATIVE ESTIMATES
            'web_email': {
                'email_processing': (5, 15),   # Very quick email operations
                'web_scraping': (15, 45),     # Manual data collection (very limited)
                'form_filling': (8, 20),      # Very quick form completion
                'data_entry': (3, 8),         # Per entry (very efficient)
            },
            
            # System operations (in seconds) - EXTREMELY CONSERVATIVE ESTIMATES
            'system_ops': {
                'backup': (15, 45),           # Very quick file operations
                'cleanup': (30, 90),          # Very efficient file sorting
                'organization': (20, 60),     # Very quick folder organization
                'monitoring': (8, 20),        # Very quick status checks
            }
        }
    
    def process(self, script: str, user_explanation: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process method required by BaseAgent - delegates to estimate_time_saved
        """
        return self.estimate_time_saved(script, user_explanation, execution_result)
    
    def estimate_time_saved(self, script: str, user_explanation: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate time saved by analyzing the script and execution results.
        
        Args:
            script: The executed automation script
            user_explanation: User's explanation of what the script should do
            execution_result: Results from script execution
            
        Returns:
            Dict containing time estimation details
        """
        try:
            # Analyze the script to understand what operations it performs
            script_analysis = self._analyze_script_operations(script)
            
            # Get AI-based estimation for complex operations
            ai_estimation = self._get_ai_time_estimation(script, user_explanation, script_analysis)
            
            # Calculate base time estimates from script analysis
            base_estimation = self._calculate_base_time_estimate(script_analysis)
            
            # Combine estimates with AI insight
            final_estimation = self._combine_estimates(base_estimation, ai_estimation, execution_result)
            
            # Apply maximum cap to prevent unrealistic estimates
            max_seconds = 180  # 3 minutes maximum
            capped_seconds = min(final_estimation['total_seconds'], max_seconds)
            
            # Add context and reasoning
            estimation_result = {
                'estimated_time_saved_seconds': capped_seconds,
                'confidence_level': final_estimation['confidence'],
                'breakdown': final_estimation['breakdown'],
                'ai_reasoning': ai_estimation.get('reasoning', ''),
                'operation_types': script_analysis['operation_types'],
                'complexity_score': script_analysis['complexity_score'],
                'user_skill_assumption': 'non_technical',
                'timestamp': time.time(),
                'script_preview': script[:200] + '...' if len(script) > 200 else script
            }
            
            if self._logger:
                self._log_interaction(self.agent_name, f"Time estimation completed: {final_estimation['total_seconds']}s saved", 
                                     f"Script: {user_explanation[:50]}...")
            
            return estimation_result
            
        except Exception as e:
            print(f"[TimeEstimationAgent] Error estimating time: {e}")
            # Fallback to simple estimation
            return self._fallback_estimation(script, user_explanation)
    
    def _analyze_script_operations(self, script: str) -> Dict[str, Any]:
        """Analyze script to identify types of operations performed."""
        operations = {
            'file_operations': [],
            'data_processing': [],
            'web_email': [],
            'system_ops': [],
            'operation_types': [],
            'complexity_score': 0
        }
        
        script_lower = script.lower()
        
        # File operations
        if any(keyword in script_lower for keyword in ['shutil.copy', 'shutil.move', 'os.rename', 'copyfile']):
            operations['file_operations'].append('copy_move')
            operations['operation_types'].append('file_operations')
        
        if any(keyword in script_lower for keyword in ['os.makedirs', 'mkdir', 'create']):
            operations['file_operations'].append('create_folder')
            operations['operation_types'].append('file_operations')
        
        if any(keyword in script_lower for keyword in ['glob.glob', 'os.walk', 'find', 'search']):
            operations['file_operations'].append('search')
            operations['operation_types'].append('file_operations')
        
        # Data processing
        if any(keyword in script_lower for keyword in ['csv', 'pandas', 'dataframe', 'excel']):
            operations['data_processing'].append('csv_processing')
            operations['operation_types'].append('data_processing')
        
        if any(keyword in script_lower for keyword in ['re.sub', 'replace', 'text', 'string']):
            operations['data_processing'].append('text_processing')
            operations['operation_types'].append('data_processing')
        
        if any(keyword in script_lower for keyword in ['pillow', 'pil', 'image', 'resize']):
            operations['data_processing'].append('image_processing')
            operations['operation_types'].append('data_processing')
        
        # Web/Email operations
        if any(keyword in script_lower for keyword in ['requests', 'urllib', 'scraping', 'beautifulsoup']):
            operations['web_email'].append('web_scraping')
            operations['operation_types'].append('web_email')
        
        if any(keyword in script_lower for keyword in ['smtp', 'email', 'mail']):
            operations['web_email'].append('email_processing')
            operations['operation_types'].append('web_email')
        
        # System operations
        if any(keyword in script_lower for keyword in ['backup', 'archive', 'compress']):
            operations['system_ops'].append('backup')
            operations['operation_types'].append('system_ops')
        
        if any(keyword in script_lower for keyword in ['cleanup', 'delete', 'remove']):
            operations['system_ops'].append('cleanup')
            operations['operation_types'].append('system_ops')
        
        # Calculate complexity score
        operations['complexity_score'] = self._calculate_complexity_score(script)
        
        return operations
    
    def _calculate_complexity_score(self, script: str) -> int:
        """Calculate complexity score based on script features."""
        score = 0
        
        # Length factor
        score += min(len(script) // 100, 10)
        
        # Loop complexity
        score += script.count('for ') * 2
        score += script.count('while ') * 3
        
        # Conditional complexity
        score += script.count('if ') * 1
        
        # Function calls
        score += script.count('def ') * 2
        
        # Import statements (indicates library usage)
        score += script.count('import ') * 1
        
        return min(score, 20)  # Cap at 20
    
    def _calculate_base_time_estimate(self, script_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate base time estimate from identified operations."""
        total_seconds = 0
        breakdown = {}
        
        for category, operations in script_analysis.items():
            if category in ['operation_types', 'complexity_score']:
                continue
                
            for operation in operations:
                if operation in self.OPERATION_TIME_ESTIMATES.get(category, {}):
                    time_range = self.OPERATION_TIME_ESTIMATES[category][operation]
                    # Use lower bound for conservative estimates
                    estimated_time = time_range[0]
                    total_seconds += estimated_time
                    breakdown[f"{category}_{operation}"] = estimated_time
        
        # Apply minimal complexity multiplier (be conservative)
        complexity_multiplier = 1 + (script_analysis['complexity_score'] * 0.05)
        total_seconds *= complexity_multiplier
        
        return {
            'total_seconds': int(total_seconds),
            'breakdown': breakdown,
            'confidence': 0.6  # Base confidence
        }
    
    def _get_ai_time_estimation(self, script: str, user_explanation: str, script_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to provide more nuanced time estimation."""
        prompt = f"""
You are an expert at estimating how long non-technical users would take to complete manual tasks that have been automated.

TASK: Estimate the time a non-technical user would spend manually performing the operations in this automation script.

USER'S EXPLANATION: "{user_explanation}"

SCRIPT ANALYSIS:
- Operation types: {script_analysis['operation_types']}
- Complexity score: {script_analysis['complexity_score']}/20

SCRIPT PREVIEW:
```python
{script[:500]}...
```

CONSIDERATIONS FOR NON-TECHNICAL USERS:
- They are unfamiliar with technical tools and interfaces
- They make mistakes and need to retry operations
- They navigate slowly through file systems and applications
- They need time to read and understand dialogs
- They may get confused by technical terminology
- They often perform tasks one at a time instead of batch operations
- They spend time thinking about what to do next

ESTIMATION CATEGORIES (BE EXTREMELY CONSERVATIVE - USE MINIMAL VALUES):
1. Simple file operations (copy, move, rename): 5-15 seconds each
2. Data processing (Excel, CSV, text editing): 10-30 seconds
3. Web operations (scraping, form filling): 15-60 seconds
4. Batch operations: multiply single operation time by quantity (but cap at 2-3 minutes total)
5. Complex workflows: add minimal setup time (30 seconds max)

CRITICAL: Be extremely conservative with estimates. Most automation saves 10-60 seconds, not minutes.
Focus on realistic time saved. A 30-second task that saves 10 seconds is still valuable.
NEVER estimate more than 2-3 minutes unless it's a truly complex multi-step workflow.

EXAMPLES OF REALISTIC ESTIMATES:
- Simple file copy: 5-15 seconds
- Rename a file: 5-10 seconds  
- Send an email: 10-30 seconds
- Fill a form: 15-45 seconds
- Process a small dataset: 20-60 seconds

REMEMBER: Users are efficient. Don't overestimate. Most tasks take 10-60 seconds to do manually.

RESPOND WITH JSON:
{{
    "estimated_minutes": <number>,
    "confidence": <0.1-1.0>,
    "reasoning": "<brief explanation>",
    "breakdown": {{
        "primary_task": "<main task>",
        "setup_time_minutes": <number>,
        "execution_time_minutes": <number>,
        "error_recovery_time_minutes": <number>
    }}
}}
"""
        
        try:
            response = self._llm.prompt(prompt)
            
            # Parse AI response (expecting JSON)
            if response:
                import json
                try:
                    # Try to parse as JSON
                    parsed_response = json.loads(response)
                    if 'estimated_minutes' in parsed_response:
                        return {
                            'estimated_minutes': parsed_response['estimated_minutes'],
                            'confidence': parsed_response.get('confidence', 0.7),
                            'reasoning': parsed_response.get('reasoning', 'AI estimation'),
                            'breakdown': parsed_response.get('breakdown', {})
                        }
                except json.JSONDecodeError:
                    # If not JSON, try to extract numbers from text
                    import re
                    numbers = re.findall(r'\d+', response)
                    if numbers:
                        return {
                            'estimated_minutes': int(numbers[0]),
                            'confidence': 0.6,
                            'reasoning': 'Extracted from AI response',
                            'breakdown': {}
                        }
        except Exception as e:
            print(f"[TimeEstimationAgent] AI estimation failed: {e}")
        
        return {'estimated_minutes': 5, 'confidence': 0.5, 'reasoning': 'Fallback estimation'}
    
    def _combine_estimates(self, base_estimation: Dict[str, Any], ai_estimation: Dict[str, Any], execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Combine base calculation with AI estimation for final result."""
        # Convert AI minutes to seconds
        ai_seconds = ai_estimation.get('estimated_minutes', 5) * 60
        
        # Weight the estimates (AI gets higher weight for complex tasks)
        ai_weight = 0.7 if ai_estimation.get('confidence', 0.5) > 0.6 else 0.5
        base_weight = 1 - ai_weight
        
        combined_seconds = int((base_estimation['total_seconds'] * base_weight) + (ai_seconds * ai_weight))
        
        # Adjust based on execution success
        if execution_result.get('success', False):
            # Successful execution - use full estimate
            final_seconds = combined_seconds
        else:
            # Failed execution - reduce estimate
            final_seconds = int(combined_seconds * 0.3)
        
        # Combine confidence scores
        combined_confidence = (base_estimation['confidence'] + ai_estimation.get('confidence', 0.5)) / 2
        
        return {
            'total_seconds': final_seconds,
            'confidence': combined_confidence,
            'breakdown': {
                'base_estimation_seconds': base_estimation['total_seconds'],
                'ai_estimation_seconds': ai_seconds,
                'combined_seconds': combined_seconds,
                'execution_success_factor': 1.0 if execution_result.get('success', False) else 0.3,
                'final_seconds': final_seconds
            }
        }
    
    def _fallback_estimation(self, script: str, user_explanation: str) -> Dict[str, Any]:
        """Fallback estimation when main estimation fails."""
        # Simple heuristics based on script length and content - VERY CONSERVATIVE
        base_time = 30  # 30 seconds default (much more conservative)
        
        if len(script) > 500:
            base_time += 30  # Add 30 seconds for longer scripts
        
        if 'for' in script or 'while' in script:
            base_time += 60  # Add 1 minute for loops
        
        if 'import' in script:
            base_time += 30  # Add 30 seconds for library usage
        
        # Cap at 3 minutes maximum
        base_time = min(base_time, 180)
        
        return {
            'estimated_time_saved_seconds': base_time,
            'confidence_level': 0.4,
            'breakdown': {'fallback_estimation': base_time},
            'ai_reasoning': 'Fallback estimation due to analysis error',
            'operation_types': ['unknown'],
            'complexity_score': 5,
            'user_skill_assumption': 'non_technical',
            'timestamp': time.time(),
            'script_preview': script[:200] + '...' if len(script) > 200 else script
        }
