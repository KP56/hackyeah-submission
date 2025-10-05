"""
Automation Executor
Handles script generation, library installation, execution with retry logic and security policies
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
import subprocess
import tempfile
import os
import sys
from pathlib import Path
import time
import re


class AutomationExecutor:
    """Executes automation scripts with retry logic, library installation, and security policies"""
    
    def __init__(self, max_retries: int = 3, verbose: bool = False, config_dir: str = "security"):
        self.max_retries = max_retries
        self.verbose = verbose
        self._execution_history = []
        self._config_dir = Path(config_dir)
        
        # Load security configuration
        self._allowed_builtins = self._load_allowed_builtins()
        self._disallowed_modules = self._load_disallowed_modules()
        self._allowed_modules = self._load_allowed_modules()
    
    def execute_automation(self, script: str, user_explanation: str) -> Dict[str, Any]:
        """
        Execute automation script with retry logic and security checks
        
        Returns:
            Dict with execution results including success status, output, errors
        """
        execution_id = len(self._execution_history) + 1
        execution_record = {
            "execution_id": execution_id,
            "user_explanation": user_explanation,
            "script": script,
            "timestamp": time.time(),
            "attempts": [],
            "success": False,
            "final_output": "",
            "final_error": ""
        }
        
        print(f"\n[AutomationExecutor] ====== STARTING EXECUTION #{execution_id} ======")
        print(f"[AutomationExecutor] User explanation: {user_explanation}")
        print(f"[AutomationExecutor] Script preview: {script[:100]}...")
        
        # Security checks
        if self._is_script_dangerous(script):
            execution_record["final_error"] = "Script contains potentially dangerous operations"
            execution_record["success"] = False
            self._execution_history.append(execution_record)
            print(f"[AutomationExecutor] [SECURITY] Script blocked due to security policy")
            return execution_record
        
        # Extract required libraries from script
        required_libraries = self._extract_required_libraries(script)
        print(f"[AutomationExecutor] Required libraries: {required_libraries if required_libraries else 'None'}")
        
        # Install required libraries
        if required_libraries:
            print(f"[AutomationExecutor] Installing libraries: {', '.join(required_libraries)}")
            install_result = self._install_libraries(required_libraries)
            execution_record["library_installation"] = install_result
            
            if not install_result["success"]:
                execution_record["final_error"] = f"Failed to install required libraries: {install_result['error']}"
                print(f"[AutomationExecutor] [ERROR] Library installation failed: {install_result['error']}")
                self._execution_history.append(execution_record)
                return execution_record
            print(f"[AutomationExecutor] [OK] Libraries installed successfully")
        
        # Try executing the script with retries
        for attempt in range(1, self.max_retries + 1):
            print(f"\n[AutomationExecutor] --- Attempt {attempt}/{self.max_retries} ---")
            
            attempt_result = self._execute_script_once(script, attempt)
            execution_record["attempts"].append(attempt_result)
            
            print(f"[AutomationExecutor] Attempt {attempt} result: success={attempt_result['success']}, return_code={attempt_result.get('return_code', 'N/A')}")
            
            if attempt_result["success"]:
                execution_record["success"] = True
                execution_record["final_output"] = attempt_result["output"]
                execution_record["final_error"] = attempt_result.get("error", "")
                
                # Clean up the temporary script file if it was created
                if attempt_result.get("script_file"):
                    self._cleanup_script_file(attempt_result["script_file"])
                    print(f"[AutomationExecutor] [OK] Cleaned up temp file: {attempt_result['script_file']}")
                
                print(f"[AutomationExecutor] [SUCCESS] Execution SUCCESSFUL on attempt {attempt}")
                print(f"[AutomationExecutor] Output: {attempt_result['output'][:200] if attempt_result['output'] else '(no output)'}")
                break
            else:
                # If not the last attempt, try to debug the error
                if attempt < self.max_retries:
                    error_msg = attempt_result.get("error", "Unknown error")
                    print(f"[AutomationExecutor] [ERROR] Attempt {attempt} failed: {error_msg[:200]}")
                    print(f"[AutomationExecutor] Will retry...")
                    
                    # Try to fix common errors (optional - can be enhanced)
                    # For now, we just retry as-is
                else:
                    execution_record["final_error"] = attempt_result.get("error", "Unknown error")
                    print(f"[AutomationExecutor] [FAILED] All {self.max_retries} attempts FAILED")
                    print(f"[AutomationExecutor] Final error: {execution_record['final_error'][:300]}")
        
        self._execution_history.append(execution_record)
        print(f"[AutomationExecutor] ====== EXECUTION #{execution_id} COMPLETE ======\n")
        return execution_record
    
    def _execute_script_once(self, script: str, attempt_number: int) -> Dict[str, Any]:
        """Execute script once and return result"""
        try:
            # Create a temporary file for the script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(script)
                script_file = f.name
            
            if self.verbose:
                print(f"[AutomationExecutor] Created temporary script file: {script_file}")
            
            # Execute the script
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, script_file],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            execution_time = time.time() - start_time
            
            success = result.returncode == 0
            
            return {
                "attempt": attempt_number,
                "success": success,
                "output": result.stdout,
                "error": result.stderr if not success else "",
                "return_code": result.returncode,
                "execution_time": execution_time,
                "script_file": script_file
            }
            
        except subprocess.TimeoutExpired:
            return {
                "attempt": attempt_number,
                "success": False,
                "output": "",
                "error": "Script execution timed out after 60 seconds",
                "return_code": -1,
                "execution_time": 60,
                "script_file": script_file if 'script_file' in locals() else None
            }
        except Exception as e:
            return {
                "attempt": attempt_number,
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1,
                "execution_time": 0,
                "script_file": script_file if 'script_file' in locals() else None
            }
    
    def _extract_required_libraries(self, script: str) -> List[str]:
        """Extract required libraries from import statements"""
        libraries = set()
        
        # Match import statements
        import_patterns = [
            r'^import\s+(\w+)',
            r'^from\s+(\w+)\s+import'
        ]
        
        for line in script.split('\n'):
            line = line.strip()
            for pattern in import_patterns:
                match = re.match(pattern, line)
                if match:
                    library = match.group(1)
                    # Skip standard library modules
                    if library not in self._get_standard_library_modules():
                        libraries.add(library)
        
        return list(libraries)
    
    def _get_standard_library_modules(self) -> set:
        """Get a set of standard library module names"""
        return {
            'os', 'sys', 'pathlib', 'shutil', 'glob', 'fnmatch',
            'datetime', 'time', 'json', 'csv', 're', 'string',
            'collections', 'itertools', 'functools', 'operator',
            'math', 'random', 'statistics', 'decimal', 'fractions',
            'io', 'tempfile', 'subprocess', 'threading', 'multiprocessing',
            'argparse', 'logging', 'pickle', 'sqlite3', 'urllib',
            'http', 'email', 'html', 'xml', 'configparser', 'platform'
        }
    
    def _fix_library_name(self, library: str) -> str:
        """Fix common library name mistakes"""
        # Map of wrong names to correct pip package names
        library_mapping = {
            'PIL': 'Pillow',
            'cv2': 'opencv-python',
            'sklearn': 'scikit-learn',
            'yaml': 'PyYAML',
            'Image': 'Pillow',
            'ImageDraw': 'Pillow',
            'ImageFont': 'Pillow',
        }
        
        return library_mapping.get(library, library)
    
    def _install_libraries(self, libraries: List[str]) -> Dict[str, Any]:
        """Install required libraries using pip"""
        if not libraries:
            return {"success": True, "installed": []}
        
        # Fix common library name mistakes
        fixed_libraries = []
        for lib in libraries:
            fixed = self._fix_library_name(lib)
            if fixed != lib and self.verbose:
                print(f"[AutomationExecutor] Auto-correcting library name: '{lib}' -> '{fixed}'")
            fixed_libraries.append(fixed)
        
        # Remove duplicates
        fixed_libraries = list(set(fixed_libraries))
        
        if self.verbose:
            print(f"[AutomationExecutor] Installing libraries: {', '.join(fixed_libraries)}")
        
        installed = []
        failed = []
        
        for library in fixed_libraries:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", library],
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout per library
                )
                
                if result.returncode == 0:
                    installed.append(library)
                    if self.verbose:
                        print(f"[AutomationExecutor] Successfully installed: {library}")
                else:
                    failed.append({
                        "library": library,
                        "error": result.stderr
                    })
                    if self.verbose:
                        print(f"[AutomationExecutor] Failed to install {library}: {result.stderr}")
            
            except Exception as e:
                failed.append({
                    "library": library,
                    "error": str(e)
                })
                if self.verbose:
                    print(f"[AutomationExecutor] Exception installing {library}: {e}")
        
        return {
            "success": len(failed) == 0,
            "installed": installed,
            "failed": failed
        }
    
    def _cleanup_script_file(self, script_file: str):
        """Delete the temporary script file"""
        try:
            if os.path.exists(script_file):
                os.remove(script_file)
                if self.verbose:
                    print(f"[AutomationExecutor] Cleaned up script file: {script_file}")
        except Exception as e:
            if self.verbose:
                print(f"[AutomationExecutor] Failed to cleanup script file: {e}")
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self._execution_history.copy()
    
    def get_execution_by_id(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """Get specific execution by ID"""
        for record in self._execution_history:
            if record["execution_id"] == execution_id:
                return record
        return None
    
    def clear_history(self):
        """Clear execution history"""
        self._execution_history.clear()
    
    def reload_security_config(self):
        """Reload security configuration from files."""
        self._allowed_builtins = self._load_allowed_builtins()
        self._disallowed_modules = self._load_disallowed_modules()
        self._allowed_modules = self._load_allowed_modules()
    
    def _load_allowed_builtins(self) -> Dict[str, Any]:
        """Load allowed built-in functions from config file."""
        config_file = self._config_dir / "allowed_builtins.txt"
        if not config_file.exists():
            self._create_default_configs()
        
        allowed = {}
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        # Get the builtin function
                        if hasattr(__builtins__, line):
                            allowed[line] = getattr(__builtins__, line)
                        elif line in __builtins__:
                            allowed[line] = __builtins__[line]
                    except (AttributeError, KeyError):
                        pass
        return allowed
    
    def _load_disallowed_modules(self) -> List[str]:
        """Load disallowed module names from config file."""
        config_file = self._config_dir / "disallowed_modules.txt"
        if not config_file.exists():
            self._create_default_configs()
        
        disallowed = []
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    disallowed.append(line)
        return disallowed
    
    def _load_allowed_modules(self) -> Dict[str, Any]:
        """Load allowed modules from config file."""
        config_file = self._config_dir / "allowed_modules.txt"
        if not config_file.exists():
            self._create_default_configs()
        
        allowed = {}
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        allowed[line] = __import__(line)
                    except ImportError:
                        pass
        return allowed
    
    def _create_default_configs(self):
        """Create default configuration files."""
        self._config_dir.mkdir(exist_ok=True)
        
        # Default allowed builtins
        with open(self._config_dir / "allowed_builtins.txt", 'w') as f:
            f.write("# Allowed built-in functions for script execution\n")
            f.write("print\nlen\nstr\nint\nfloat\nlist\ndict\ntuple\nset\nbool\ntype\n")
            f.write("isinstance\nhasattr\ngetattr\nsetattr\ndir\nenumerate\nzip\n")
            f.write("map\nfilter\nsorted\nreversed\nrange\nopen\ninput\nmin\nmax\n")
            f.write("sum\nabs\nround\npow\ndivmod\nbin\nhex\noct\nord\nchr\n")
            f.write("repr\nascii\nformat\nvars\nlocals\nglobals\ncompile\n")
            f.write("exec\neval\n")
        
        # Default disallowed modules
        with open(self._config_dir / "disallowed_modules.txt", 'w') as f:
            f.write("# Disallowed modules for security\n")
            f.write("subprocess\nos.system\nos.popen\nos.spawn\n")
            f.write("ctypes\nmultiprocessing\nthreading\n")
            f.write("socket\nurllib\nrequests\nhttp\n")
            f.write("pickle\nmarshal\nshelve\ndbm\n")
            f.write("sqlite3\npsycopg2\npymongo\n")
            f.write("cryptography\nhashlib\nhmac\n")
            f.write("tempfile\nshutil.rmtree\n")
        
        # Default allowed modules
        with open(self._config_dir / "allowed_modules.txt", 'w') as f:
            f.write("# Allowed modules for script execution\n")
            f.write("os\npathlib\ntime\nshutil\njson\ncsv\n")
            f.write("datetime\nmath\nrandom\nitertools\n")
            f.write("collections\nfunctools\noperator\n")
            f.write("re\nstring\ntextwrap\n")
    
    def _is_script_dangerous(self, code: str) -> bool:
        """Check if script contains dangerous operations."""
        code_lower = code.lower()
        
        # Check for disallowed modules
        for module in self._disallowed_modules:
            if f"import {module}" in code_lower or f"from {module}" in code_lower:
                return True
        
        # Check for dangerous patterns
        dangerous_patterns = [
            'subprocess',
            'os.system',
            'os.popen',
            'eval(',
            'exec(',
            '__import__',
            'getattr(',
            'setattr(',
            'delattr(',
            'globals()',
            'locals()',
            'vars(',
            'dir(',
            'compile(',
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return True
        
        return False

