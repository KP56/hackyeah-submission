from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import asyncio
import threading
import time
import os
from datetime import datetime

from .config import load_config
from .recent_ops import RecentFileOperations
from .gemini_client import Gemini
from .agents import (
    PatternDetectorAgent, 
    PatternSpotterAgent, 
    ActionFilterAgent, 
    AutomationAgent, 
    PythonAgent,
    ShortTermPatternAgent,
    LongTermPatternAgent,
    ScriptSummarizerAgent,
    TimeEstimationAgent
)
from .nylas_handler import NylasHandler
from .error_logger import ErrorLogger
from .emails import EmailAccounts, ImapEmailAccount, NylasEmailAccount, Pop3EmailAccount, discover_email_servers
from .persistence import persistence
from .action_registry import ActionRegistry, UserAction
from .automation_executor import AutomationExecutor
from .app_monitor import AppSwitchMonitor
from .keyboard_monitor import KeyboardMonitor
from .app_usage_tracker import app_usage_tracker
from .services.email_polling import EmailPoller
from .error_handler import global_error_handler, safe_agent_method_call, safe_agent_method_call_with_fallback

app = FastAPI(title="ProcessBot Automation Backend", version="1.0.0")

# CORS middleware for Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
config = load_config()
recent_ops = None
gemini_client = None
gemini_code_client = None
pattern_agent = None
planner = None
python_agent = None
script_executor = None
nylas_handler = None
accounts = EmailAccounts()
ai_interactions = []
error_logger = ErrorLogger()

# Agent instances
action_filter = None
pattern_detector = None
pattern_spotter = None
automation_agent = None
short_term_agent = None
long_term_agent = None
script_summarizer = None
automation_executor = None
app_switch_monitor = None
keyboard_monitor = None
action_registry = None
email_poller = None
time_estimation_agent = None

# Pattern detection globals
pattern_detection_thread = None
pattern_detection_stop = threading.Event()

# Periodic save thread
save_thread = None
save_stop = threading.Event()

# Long-term summarization threads and state
minute_summary_thread = None
minute_summary_stop = threading.Event()
ten_minute_summary_thread = None
ten_minute_summary_stop = threading.Event()
minute_summaries = []  # List of 1-minute summaries
ten_minute_summaries = []  # List of 10-minute summaries
minute_summaries_lock = threading.Lock()
ten_minute_summaries_lock = threading.Lock()
last_minute_summary_time = 0
last_ten_minute_summary_time = 0

# Short-term pattern detection globals
short_term_detection_thread = None
short_term_detection_stop = threading.Event()
last_check_timestamp = 0
last_suggestion_time = 0
muted_until = 0

# Automation execution state
total_time_saved_seconds = 0

# Load time saved data from persistence on startup
try:
    time_saved_data = persistence.load_time_saved_data()
    total_time_saved_seconds = time_saved_data.get("total_time_saved_seconds", 0)
    print(f"Loaded total time saved: {total_time_saved_seconds}s ({total_time_saved_seconds/60:.1f}min)")
except Exception as e:
    print(f"Error loading time saved data: {e}")
    total_time_saved_seconds = 0

# Automation suggestion management
pending_suggestions = []
ignored_patterns = set()

# Lock objects for thread safety
pending_lock = threading.Lock()
last_check_lock = threading.Lock()
muted_until_lock = threading.Lock()
ignored_patterns_lock = threading.Lock()
time_saved_lock = threading.Lock()
last_suggestion_lock = threading.Lock()

# Constants
SUGGESTION_COOLDOWN = 60  # 60 seconds between suggestions

def log_ai_interaction(agent_name: str, prompt: str, response: str, context: Optional[Dict[str, Any]] = None):
    """Log an AI interaction for display in the frontend"""
    interaction = {
        "agent": agent_name,
        "prompt": prompt,
        "response": response,
        "timestamp": datetime.now().isoformat(),
        "context": context or {},
        "prompt_length": len(prompt),
        "response_length": len(response)
    }
    ai_interactions.append(interaction)
    
    # Save to persistence
    persistence.append_ai_interaction(interaction)
    
    print(f"AI interaction logged: {agent_name} - {prompt[:50]}... -> {response[:50]}...")
    print(f"Total AI interactions: {len(ai_interactions)}")

# Pydantic models
class ConfigUpdate(BaseModel):
    nylas_api_key: Optional[str] = None
    nylas_client_id: Optional[str] = None
    nylas_redirect_uri: Optional[str] = None
    nylas_api_uri: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    watch_dirs: Optional[List[str]] = None
    pattern_agent_interval_seconds: Optional[int] = None
    recent_ops_capacity: Optional[int] = None
    logging_enabled: Optional[bool] = None
    backend_port: Optional[int] = None

class EmailAccountRequest(BaseModel):
    email: str
    password: str

class OAuthRequest(BaseModel):
    code: str

class AIInteraction(BaseModel):
    prompt: str
    response: str
    timestamp: str

# Callback functions for monitors
def on_app_switch(app_name: str, window_title: str):
    """Called when user switches to a different application"""
    global action_registry
    
    # Clean up app name (remove .exe extension)
    if app_name.lower().endswith('.exe'):
        app_name = app_name[:-4]
    
    # Record app switch for usage tracking
    app_usage_tracker.record_app_switch(app_name)
    
    if action_registry:
        action_registry.register_action(
            action_type="app_switch",
            details={
                "app_name": app_name,
                "window_title": window_title,
                "description": f"Opened {app_name}"
            },
            source="app_monitor"
        )
        print(f"[APP SWITCH] User opened: {app_name} - {window_title}")

def on_key_sequence(keys: List[str]):
    """Called when keyboard buffer updates"""
    global action_registry, keyboard_monitor
    
    # Don't register every single key press, only meaningful sequences
    # We'll register when we detect common patterns like Ctrl+C, Ctrl+V, etc.
    
    if not action_registry or not keyboard_monitor:
        return
    
    # Check for common shortcuts in the last few keys
    recent_keys = keys[-3:] if len(keys) >= 3 else keys
    key_string = ' '.join(recent_keys)
    
    # Detect common shortcuts
    shortcuts = {
        'Ctrl+c': 'Copy',
        'Ctrl+v': 'Paste',
        'Ctrl+x': 'Cut',
        'Ctrl+z': 'Undo',
        'Ctrl+y': 'Redo',
        'Ctrl+s': 'Save',
        'Ctrl+a': 'Select All',
        'Ctrl+f': 'Find',
        'Ctrl+h': 'Replace',
        'Ctrl+p': 'Print',
        'Ctrl+n': 'New',
        'Ctrl+o': 'Open',
        'Ctrl+w': 'Close',
        'Alt+Tab': 'Switch Window',
        'Alt+F4': 'Close Application',
    }
    
    for shortcut, action_name in shortcuts.items():
        if shortcut.replace('+', ' ').lower() in key_string.lower() or shortcut in ' '.join(keys[-2:]):
            action_registry.register_action(
                action_type="keyboard_shortcut",
                details={
                    "shortcut": shortcut,
                    "action": action_name,
                    "description": f"Pressed {shortcut} ({action_name})",
                    "recent_keys": ' '.join(keys[-10:])  # Last 10 keys for context
                },
                source="keyboard_monitor"
            )
            print(f"[KEYBOARD] User pressed: {shortcut} ({action_name})")
            break

# Initialize services
def initialize_services():
    global recent_ops, gemini_client, pattern_agent, planner, python_agent, script_executor, nylas_handler, accounts, error_logger, action_filter, pattern_detector, pattern_spotter, automation_agent
    global short_term_agent, long_term_agent, script_summarizer, automation_executor, app_switch_monitor, keyboard_monitor, action_registry, gemini_code_client, email_poller, time_estimation_agent
    
    # Stop existing file watcher if it exists
    if recent_ops is not None:
        print("Stopping existing file watcher...")
        try:
            recent_ops.stop()
            print("Existing file watcher stopped")
        except Exception as e:
            print(f"Error stopping file watcher: {e}")
    
    recent_ops = RecentFileOperations(
        directories=config.watch_dirs, 
        capacity=config.recent_ops_capacity, 
        verbose=config.logging_enabled,
        error_logger=error_logger
    )
    
    # Set up callback to register file operations in action registry
    original_handler = recent_ops._handler
    def on_file_operation_detected(text: str):
        """Callback when a file operation is detected"""
        # Get the latest operation
        if len(recent_ops._ops) > 0:
            latest_op = recent_ops._ops[-1]
            register_file_operation_as_action(latest_op)
    
    # Replace the handler with one that calls our callback
    if recent_ops._handler is not None:
        recent_ops._handler.on_action = on_file_operation_detected
    else:
        print("Warning! recent_ops._handler is None")
    
    gemini_client = Gemini(
        api_key=config.gemini_api_key, 
        model=config.gemini_model,
        verbose=config.logging_enabled,
        on_interaction=lambda p, r: log_ai_interaction("Gemini", p, r)
    )
    
    # Initialize code-specific client with better model for code generation
    gemini_code_client = Gemini(
        api_key=config.gemini_api_key, 
        model="gemini-1.5-pro",  # Better model for code
        verbose=config.logging_enabled,
        on_interaction=lambda p, r: log_ai_interaction("Gemini-Code", p, r)
    )
    
    nylas_client = None
    if config.nylas_api_key:
        try:
            from nylas import Client
            nylas_client = Client(api_key=config.nylas_api_key, api_uri=config.nylas_api_uri)
        except Exception:
            pass
    
    nylas_handler = NylasHandler(nylas_client=nylas_client)
    
    # Initialize action registry
    print("Initializing action registry...")
    action_registry = ActionRegistry()
    
    # Initialize email poller
    print("Initializing email poller...")
    email_poller = EmailPoller(
        email_accounts=accounts,
        action_registry=action_registry,
        interval=15  # Poll every 15 seconds
    )
    
    # Initialize agents
    action_filter = ActionFilterAgent(llm=gemini_client, logger=log_ai_interaction)
    pattern_detector = PatternDetectorAgent(llm=gemini_client, logger=log_ai_interaction)
    pattern_spotter = PatternSpotterAgent(llm=gemini_client, logger=log_ai_interaction)
    automation_agent = AutomationAgent(llm=gemini_client, logger=log_ai_interaction)
    python_agent = PythonAgent(llm=gemini_client, logger=log_ai_interaction)
    
    # Initialize new agents
    short_term_agent = ShortTermPatternAgent(llm=gemini_client, logger=log_ai_interaction)
    long_term_agent = LongTermPatternAgent(llm=gemini_client, logger=log_ai_interaction)
    script_summarizer = ScriptSummarizerAgent(llm=gemini_client, logger=log_ai_interaction)  # Use main client
    automation_executor = AutomationExecutor(max_retries=3, verbose=True)  # Always verbose for debugging
    
    # Initialize time estimation agent
    print("Initializing time estimation agent...")
    time_estimation_agent = TimeEstimationAgent(llm=gemini_client, logger=log_ai_interaction)
    
    # Initialize user activity monitors
    print("Initializing app switch monitor...")
    app_switch_monitor = AppSwitchMonitor(
        on_app_switch=on_app_switch,
        poll_interval=1.0  # Check every second
    )
    app_switch_monitor.start()
    
    print("Initializing keyboard monitor...")
    keyboard_monitor = KeyboardMonitor(
        buffer_size=30,  # Keep last 30 keys
        on_key_sequence=on_key_sequence
    )
    keyboard_monitor.start()
    
    print("Starting app usage tracker...")
    app_usage_tracker.start()
    
    # Start the file watcher
    if recent_ops:
        print("Starting file watcher from initialize_services...")
        recent_ops.start()
        print("File watcher started from initialize_services")

def pattern_detection_worker():
    """Background worker for pattern detection using two-stage approach"""
    while not pattern_detection_stop.is_set():
        try:
            # Check if agents are initialized
            if not action_filter or not pattern_detector or not pattern_spotter:
                print("Pattern detection: Agents not yet initialized, waiting...")
                print("DEBUG: Sleeping for 5 seconds (agents not initialized)")
                time.sleep(5)
                continue
                
            ops = recent_ops.snapshot()[-50:] if recent_ops else []
            print(f"Pattern detection: Checking for operations, found {len(ops)} operations")
            if ops:
                print(f"Pattern detection: Processing {len(ops)} operations")
                print(f"Sample operations: {[f'{op.event_type}: {op.src_path}' for op in ops[:3]]}")
                
                # Stage 1: Filter out program-generated actions - with error handling
                filtered_ops = safe_agent_method_call_with_fallback(
                    action_filter, 'filter_user_actions', global_error_handler, [], ops
                )
                if filtered_ops is None:
                    print("Pattern detection: Failed to filter operations, skipping this cycle")
                    print(f"DEBUG: Sleeping for {config.pattern_agent_interval_seconds} seconds (filter failed)")
                    time.sleep(config.pattern_agent_interval_seconds)
                    continue
                    
                print(f"Pattern detection: Filtered to {len(filtered_ops)} user actions")
                
                if filtered_ops:
                    # Stage 2: Analyze patterns - with error handling
                    analysis = safe_agent_method_call(
                        pattern_detector, 'analyze_patterns', global_error_handler, filtered_ops
                    )
                    if analysis is None:
                        print("Pattern detection: Failed to analyze patterns, skipping this cycle")
                        print(f"DEBUG: Sleeping for {config.pattern_agent_interval_seconds} seconds (analysis failed)")
                        time.sleep(config.pattern_agent_interval_seconds)
                        continue
                        
                    print(f"Pattern detection: Analysis completed")
                    
                    # Stage 3: Make final spotting decision - with error handling
                    spotting_response = safe_agent_method_call(
                        pattern_spotter, 'spot_pattern', global_error_handler, analysis, filtered_ops
                    )
                    if spotting_response is None:
                        print("Pattern detection: Failed to spot patterns, skipping this cycle")
                        print(f"DEBUG: Sleeping for {config.pattern_agent_interval_seconds} seconds (spotting failed)")
                        time.sleep(config.pattern_agent_interval_seconds)
                        continue
                        
                    print(f"Pattern detection: Spotting response: {spotting_response[:100]}...")
                    
                    # Check if pattern was spotted - with error handling
                    has_pattern = safe_agent_method_call_with_fallback(
                        pattern_spotter, 'has_spotted_pattern', global_error_handler, False, spotting_response
                    )
                    
                    if has_pattern:
                        print(f"Pattern spotted: {spotting_response}")
                        
                        # Create automation script using the AutomationAgent - with error handling
                        if automation_agent:
                            automation_script = safe_agent_method_call(
                                automation_agent, 'create_automation_script', global_error_handler, 
                                spotting_response, filtered_ops
                            )
                            
                            if automation_script:
                                print(f"Automation script created: {automation_script[:100]}...")
                                
                                # Log the automation creation
                                try:
                                    log_ai_interaction(
                                        "AutomationAgent", 
                                        f"Created automation for pattern: {spotting_response[:100]}...",
                                        f"Generated script: {automation_script[:200]}...",
                                        {
                                            "pattern_description": spotting_response,
                                            "operations_count": len(filtered_ops),
                                            "script_length": len(automation_script),
                                            "automation_created": True
                                        }
                                    )
                                except Exception as log_error:
                                    print(f"Failed to log automation creation: {log_error}")
                                
                                # TODO: You could save the automation script to a file or execute it here
                                # For now, we just log it
                            else:
                                print("Failed to create automation script")
                                try:
                                    log_ai_interaction(
                                        "AutomationAgent", 
                                        f"Failed to create automation for pattern: {spotting_response[:100]}...",
                                        "Script generation failed",
                                        {
                                            "pattern_description": spotting_response,
                                            "operations_count": len(filtered_ops),
                                            "automation_created": False
                                        }
                                    )
                                except Exception as log_error:
                                    print(f"Failed to log automation failure: {log_error}")
                        else:
                            print("AutomationAgent not available")
                            try:
                                log_ai_interaction(
                                    "PatternSpotterAgent", 
                                    f"Pattern spotted but no automation agent available: {spotting_response[:100]}...",
                                    "AutomationAgent not initialized",
                                    {
                                        "pattern_description": spotting_response,
                                        "operations_count": len(filtered_ops),
                                        "automation_available": False
                                    }
                                )
                            except Exception as log_error:
                                print(f"Failed to log automation unavailability: {log_error}")
            else:
                print("Pattern detection: No operations to process")
                        
        except Exception as e:
            print(f"Pattern detection error: {e}")
            global_error_handler.handle_agent_error("PatternDetectionWorker", "main_loop", e, {
                'worker': True,
                'cycle_failed': True
            })
            # Wait a bit before retrying to prevent rapid error loops
            print("DEBUG: Sleeping for 5 seconds (error recovery)")
            time.sleep(5)
        
        print(f"DEBUG: Sleeping for {config.pattern_agent_interval_seconds} seconds (normal cycle)")
        time.sleep(config.pattern_agent_interval_seconds)

def short_term_pattern_detection_worker():
    """Background worker for short-term pattern detection (checks every 5s, looks at last 30s)"""
    global last_check_timestamp, last_suggestion_time
    
    while not short_term_detection_stop.is_set():
        try:
            # Check if agents are initialized
            if not short_term_agent or not action_registry:
                print("Short-term detection: Agents not yet initialized, waiting...")
                print("DEBUG: Sleeping for 5 seconds (short-term agents not initialized)")
                time.sleep(5)
                continue
            
            current_time = time.time()
            
            # Look for actions in the last 30 seconds
            time_window_seconds = 30
            window_start_time = current_time - time_window_seconds
            
            # Get only the last 50 actions for processing - with error handling
            try:
                all_actions = action_registry.get_all_actions()
                last_50_actions = list(all_actions)[-50:] if len(all_actions) >= 50 else list(all_actions)
            except Exception as e:
                print(f"Short-term detection: Failed to get actions: {e}")
                global_error_handler.handle_agent_error("ShortTermDetectionWorker", "get_actions", e)
                print("DEBUG: Sleeping for 5 seconds (get actions failed)")
                time.sleep(5)
                continue
            
            # Filter to actions within the time window
            recent_actions = [a for a in last_50_actions if a.timestamp >= window_start_time]
            
            if len(recent_actions) >= 3:  # Need at least 3 actions for a pattern
                print(f"Short-term detection: Analyzing {len(recent_actions)} actions from last {time_window_seconds} seconds")
                
                # Send everything to Gemini - let it decide - with error handling
                pattern_result = safe_agent_method_call(
                    short_term_agent, 'detect_pattern', global_error_handler, recent_actions
                )
                if pattern_result is None:
                    print("Short-term detection: Failed to detect pattern, skipping this cycle")
                    print("DEBUG: Sleeping for 5 seconds (pattern detection failed)")
                    time.sleep(5)
                    continue
                
                if pattern_result:
                    # Check if user is already working on a suggestion
                    with pending_lock:
                        active_suggestion = any(
                            s["status"] in ["accepted", "explained"] 
                            for s in pending_suggestions
                        )
                        if active_suggestion:
                            print(f"BUSY: User is already working on a suggestion. Skipping new detection.")
                            print("DEBUG: Sleeping for 3 seconds (user busy with suggestion)")
                            time.sleep(3)
                            continue
                    
                    # Check if automation is muted
                    with muted_until_lock:
                        if current_time < muted_until:
                            remaining_minutes = int((muted_until - current_time) / 60)
                            print(f"MUTED: Automation is muted for {remaining_minutes} more minutes. Skipping.")
                            print("DEBUG: Sleeping for 3 seconds (automation muted)")
                            time.sleep(3)
                            continue
                    
                    # Check cooldown - only allow 1 suggestion per minute
                    with last_suggestion_lock:
                        time_since_last_suggestion = current_time - last_suggestion_time
                        if time_since_last_suggestion < SUGGESTION_COOLDOWN:
                            print(f"COOLDOWN: Only {time_since_last_suggestion:.0f}s since last suggestion, need {SUGGESTION_COOLDOWN}s. Skipping.")
                            print("DEBUG: Sleeping for 10 seconds (cooldown period)")
                            time.sleep(10)
                            continue
                    
                    # Check if this pattern should be ignored
                    pattern_hash = get_pattern_hash(recent_actions)
                    with ignored_patterns_lock:
                        if pattern_hash in ignored_patterns:
                            print(f"Skipping ignored pattern: {pattern_hash}")
                            print("DEBUG: Sleeping for 10 seconds (ignored pattern)")
                            time.sleep(10)
                            continue
                        
                        print(f"Short-term pattern detected: {pattern_result.get('description', '')}")
                        
                        # Create a pending automation suggestion
                        with pending_lock:
                            suggestion = {
                                "suggestion_id": f"suggestion_{int(time.time())}_{len(pending_suggestions)}",
                                "timestamp": time.time(),
                                "pattern_description": pattern_result.get("description", ""),
                                "confidence": pattern_result.get("confidence", "medium"),
                                "actions": [a.to_dict() for a in recent_actions],
                                "pattern_hash": pattern_hash,
                                "status": "pending",  # pending, accepted, rejected, completed
                                "user_explanation": None,
                                "generated_script": None,
                                "execution_result": None,
                                "time_saved_seconds": None
                            }
                            pending_suggestions.append(suggestion)
                            print(f"Created automation suggestion: {suggestion['suggestion_id']}")
                        
                        # IMPORTANT: Update last check timestamp so we don't check these actions again
                        with last_check_lock:
                            last_check_timestamp = current_time
                        
                        # Update last suggestion time
                        with last_suggestion_lock:
                            last_suggestion_time = current_time
                        
                        # Add pattern to ignored so we don't suggest it again immediately
                        with ignored_patterns_lock:
                            ignored_patterns.add(pattern_hash)
                        
                        print(f"Pattern suggestion created successfully")
                        print(f"Next suggestion allowed in {SUGGESTION_COOLDOWN} seconds")
                else:
                    print(f"Short-term detection: No pattern detected by Gemini")
            else:
                print(f"Short-term detection: Only {len(recent_actions)} actions in last {time_window_seconds} seconds (need 3+)")
        
        except Exception as e:
            print(f"Short-term pattern detection error: {e}")
            global_error_handler.handle_agent_error("ShortTermDetectionWorker", "main_loop", e, {
                'worker': True,
                'cycle_failed': True
            })
            # Wait a bit before retrying to prevent rapid error loops
            print("DEBUG: Sleeping for 5 seconds (short-term error recovery)")
            time.sleep(5)
        
        # Check every 5 seconds
        print("DEBUG: Sleeping for 5 seconds (short-term normal cycle)")
        time.sleep(5)

def calculate_time_saved(action_count: int, pattern_type: str = "file_operations") -> int:
    """
    Calculate estimated time saved in seconds
    Assumes user is slow and methodical with tasks
    """
    if pattern_type == "file_operations":
        # Assume 15-30 seconds per file operation (clicking, typing, etc.)
        seconds_per_action = 20
        return action_count * seconds_per_action
    elif pattern_type == "renaming":
        # Renaming takes longer (thinking, typing new name, confirming)
        seconds_per_action = 25
        return action_count * seconds_per_action
    else:
        # Default: 20 seconds per action
        return action_count * 20

def get_pattern_hash(actions: List) -> str:
    """Create a hash from actions to identify similar patterns"""
    import hashlib
    # Create a string representation of the pattern
    pattern_str = ""
    for action in actions:
        if hasattr(action, 'to_dict'):
            details = action.to_dict()['details']
        else:
            details = action.get('details', {})
        pattern_str += f"{details.get('event_type', '')}:{details.get('file_extension', '')}:"
    return hashlib.md5(pattern_str.encode()).hexdigest()[:16]

def register_file_operation_as_action(file_op):
    """Register a file operation as an action in the action registry"""
    if action_registry:
        print(f"[FILE WATCHER] [OK] Registered: {file_op.event_type} | {file_op.src_path}")
        action_registry.register_action(
            action_type="file_operation",
            details={
                "event_type": file_op.event_type,
                "src_path": file_op.src_path,
                "dest_path": file_op.dest_path,
                "file_size": file_op.file_size,
                "file_extension": file_op.file_extension,
                "operation_category": file_op.operation_category
            },
            source="file_watcher",
            metadata={
                "timestamp": file_op.timestamp
            }
        )

def periodic_save_worker():
    """Background worker for periodic data saving"""
    while not save_stop.is_set():
        try:
            # Save AI interactions every 30 seconds - with error handling
            if ai_interactions:
                try:
                    persistence.save_ai_interactions(ai_interactions)
                    print(f"Periodic save: Saved {len(ai_interactions)} AI interactions")
                except Exception as e:
                    print(f"Periodic save: Failed to save AI interactions: {e}")
                    global_error_handler.handle_agent_error("PeriodicSaveWorker", "save_ai_interactions", e)
            
            # Save file operations every 60 seconds - with error handling
            if recent_ops:
                try:
                    operations = recent_ops.snapshot()
                    file_ops_data = []
                    for op in operations:
                        file_ops_data.append({
                            "event_type": op.event_type,
                            "src_path": op.src_path,
                            "dest_path": op.dest_path,
                            "timestamp": op.timestamp,
                            "file_size": op.file_size,
                            "file_extension": op.file_extension,
                            "operation_category": op.operation_category
                        })
                    persistence.save_file_operations(file_ops_data)
                    print(f"Periodic save: Saved {len(file_ops_data)} file operations")
                except Exception as e:
                    print(f"Periodic save: Failed to save file operations: {e}")
                    global_error_handler.handle_agent_error("PeriodicSaveWorker", "save_file_operations", e)
            
            # Save execution history every 60 seconds - with error handling
            if python_agent and hasattr(python_agent, 'get_execution_history'):
                try:
                    execution_history = python_agent.get_execution_history()
                    persistence.save_execution_history(execution_history)
                    print(f"Periodic save: Saved {len(execution_history)} execution history entries")
                except Exception as e:
                    print(f"Periodic save: Failed to save execution history: {e}")
                    global_error_handler.handle_agent_error("PeriodicSaveWorker", "save_execution_history", e)
            
            # Save action registry - with error handling
            if action_registry:
                try:
                    action_registry.save_to_file()
                    print(f"Periodic save: Saved action registry")
                except Exception as e:
                    print(f"Periodic save: Failed to save action registry: {e}")
                    global_error_handler.handle_agent_error("PeriodicSaveWorker", "save_action_registry", e)
            
            # Save summaries - with error handling
            try:
                with minute_summaries_lock:
                    if minute_summaries:
                        persistence.save_minute_summaries(minute_summaries)
            except Exception as e:
                print(f"Periodic save: Failed to save minute summaries: {e}")
                global_error_handler.handle_agent_error("PeriodicSaveWorker", "save_minute_summaries", e)
            
            try:
                with ten_minute_summaries_lock:
                    if ten_minute_summaries:
                        persistence.save_ten_minute_summaries(ten_minute_summaries)
            except Exception as e:
                print(f"Periodic save: Failed to save ten-minute summaries: {e}")
                global_error_handler.handle_agent_error("PeriodicSaveWorker", "save_ten_minute_summaries", e)
                
        except Exception as e:
            print(f"Periodic save error: {e}")
            global_error_handler.handle_agent_error("PeriodicSaveWorker", "main_loop", e, {
                'worker': True,
                'cycle_failed': True
            })
            # Wait a bit before retrying to prevent rapid error loops
            print("DEBUG: Sleeping for 30 seconds (periodic save error recovery)")
            time.sleep(30)
        
        # Save every 30 seconds
        print("DEBUG: Sleeping for 30 seconds (periodic save normal cycle)")
        time.sleep(30)

def minute_summary_worker():
    """Background worker that creates 1-minute summaries of user activity"""
    global last_minute_summary_time, minute_summaries
    
    # Wait 60 seconds before starting to accumulate some actions
    print("DEBUG: Sleeping for 60 seconds (minute summary initial wait)")
    time.sleep(60)
    
    while not minute_summary_stop.is_set():
        try:
            if not long_term_agent or not action_registry:
                print("Minute summary: Agents not yet initialized, waiting...")
                print("DEBUG: Sleeping for 60 seconds (minute summary agents not initialized)")
                time.sleep(60)
                continue
            
            current_time = time.time()
            
            # Get actions from the last minute - with error handling
            one_minute_ago = current_time - 60
            try:
                all_actions = action_registry.get_all_actions()
                recent_actions = [a for a in all_actions if a.timestamp >= one_minute_ago]
            except Exception as e:
                print(f"Minute summary: Failed to get actions: {e}")
                global_error_handler.handle_agent_error("MinuteSummaryWorker", "get_actions", e)
                print("DEBUG: Sleeping for 60 seconds (minute summary get actions failed)")
                time.sleep(60)
                continue
            
            if len(recent_actions) > 0:
                print(f"Minute summary: Creating summary for {len(recent_actions)} actions")
                
                # Create summary using long-term agent - with error handling
                summary_text = safe_agent_method_call(
                    long_term_agent, 'create_minute_summary', global_error_handler, recent_actions
                )
                
                if summary_text:
                    # Create summary object
                    summary = {
                        "id": f"minute_{int(current_time)}",
                        "timestamp": current_time,
                        "summary": summary_text,
                        "action_count": len(recent_actions),
                        "action_types": list(set(a.action_type for a in recent_actions))
                    }
                    
                    # Add to in-memory list - with error handling
                    try:
                        with minute_summaries_lock:
                            minute_summaries.append(summary)
                            # Keep only last 1000 summaries in memory
                            if len(minute_summaries) > 1000:
                                minute_summaries.pop(0)
                    except Exception as e:
                        print(f"Minute summary: Failed to add to memory: {e}")
                        global_error_handler.handle_agent_error("MinuteSummaryWorker", "add_to_memory", e)
                    
                    # Save to persistence - with error handling
                    try:
                        persistence.append_minute_summary(summary)
                    except Exception as e:
                        print(f"Minute summary: Failed to save to persistence: {e}")
                        global_error_handler.handle_agent_error("MinuteSummaryWorker", "save_to_persistence", e)
                    
                    print(f"Minute summary created: {summary_text[:100]}...")
                else:
                    print("Minute summary: No summary generated (possibly no meaningful actions)")
            else:
                print(f"Minute summary: No actions in the last minute")
            
            last_minute_summary_time = current_time
            
        except Exception as e:
            print(f"Minute summary error: {e}")
            global_error_handler.handle_agent_error("MinuteSummaryWorker", "main_loop", e, {
                'worker': True,
                'cycle_failed': True
            })
            # Wait a bit before retrying to prevent rapid error loops
            print("DEBUG: Sleeping for 60 seconds (minute summary error recovery)")
            time.sleep(60)
        
        # Wait 60 seconds before next summary
        print("DEBUG: Sleeping for 60 seconds (minute summary normal cycle)")
        time.sleep(60)

def ten_minute_summary_worker():
    """Background worker that creates 10-minute summaries from minute summaries"""
    global last_ten_minute_summary_time, ten_minute_summaries, minute_summaries
    
    # Wait 10 minutes before starting
    print("DEBUG: Sleeping for 600 seconds (ten-minute summary initial wait)")
    time.sleep(600)
    
    while not ten_minute_summary_stop.is_set():
        try:
            if not long_term_agent:
                print("10-minute summary: Agent not yet initialized, waiting...")
                print("DEBUG: Sleeping for 600 seconds (ten-minute summary agent not initialized)")
                time.sleep(600)
                continue
            
            current_time = time.time()
            
            # Get the last 10 minute summaries - with error handling
            try:
                with minute_summaries_lock:
                    # Get summaries from the last 10 minutes
                    ten_minutes_ago = current_time - 600
                    recent_minute_summaries = [
                        s for s in minute_summaries 
                        if s["timestamp"] >= ten_minutes_ago
                    ]
                    
                    # Extract just the text summaries
                    summary_texts = [s["summary"] for s in recent_minute_summaries]
            except Exception as e:
                print(f"10-minute summary: Failed to get minute summaries: {e}")
                global_error_handler.handle_agent_error("TenMinuteSummaryWorker", "get_minute_summaries", e)
                print("DEBUG: Sleeping for 600 seconds (ten-minute summary get summaries failed)")
                time.sleep(600)
                continue
            
            if len(summary_texts) >= 5:  # Need at least 5 minute summaries
                print(f"10-minute summary: Creating summary from {len(summary_texts)} minute summaries")
                
                # Create 10-minute summary - with error handling
                summary_text = safe_agent_method_call(
                    long_term_agent, 'create_ten_minute_summary', global_error_handler, summary_texts
                )
                
                if summary_text:
                    # Create summary object
                    summary = {
                        "id": f"ten_minute_{int(current_time)}",
                        "timestamp": current_time,
                        "summary": summary_text,
                        "minute_summaries_count": len(summary_texts),
                        "total_actions": sum(s.get("action_count", 0) for s in recent_minute_summaries)
                    }
                    
                    # Add to in-memory list - with error handling
                    try:
                        with ten_minute_summaries_lock:
                            ten_minute_summaries.append(summary)
                            # Keep only last 500 summaries in memory
                            if len(ten_minute_summaries) > 500:
                                ten_minute_summaries.pop(0)
                    except Exception as e:
                        print(f"10-minute summary: Failed to add to memory: {e}")
                        global_error_handler.handle_agent_error("TenMinuteSummaryWorker", "add_to_memory", e)
                    
                    # Save to persistence - with error handling
                    try:
                        persistence.append_ten_minute_summary(summary)
                    except Exception as e:
                        print(f"10-minute summary: Failed to save to persistence: {e}")
                        global_error_handler.handle_agent_error("TenMinuteSummaryWorker", "save_to_persistence", e)
                    
                    print(f"10-minute summary created: {summary_text[:100]}...")
                else:
                    print("10-minute summary: No summary generated")
            else:
                print(f"10-minute summary: Only {len(summary_texts)} minute summaries available (need at least 5)")
            
            last_ten_minute_summary_time = current_time
            
        except Exception as e:
            print(f"10-minute summary error: {e}")
            global_error_handler.handle_agent_error("TenMinuteSummaryWorker", "main_loop", e, {
                'worker': True,
                'cycle_failed': True
            })
            # Wait a bit before retrying to prevent rapid error loops
            time.sleep(600)
        
        # Wait 10 minutes before next summary
        time.sleep(600)

# Startup event
@app.on_event("startup")
async def startup_event():
    global ai_interactions, last_check_timestamp, minute_summaries, ten_minute_summaries
    global action_filter, pattern_detector, pattern_spotter, automation_agent, python_agent
    global short_term_agent, long_term_agent, script_summarizer, automation_executor
    global app_switch_monitor, keyboard_monitor, action_registry, gemini_client, gemini_code_client
    global recent_ops, script_executor, nylas_handler, email_poller, time_estimation_agent
    
    print("Starting services...")
    
    # Load persisted data first
    print("Loading persisted data...")
    ai_interactions = persistence.load_ai_interactions()
    print(f"Loaded {len(ai_interactions)} AI interactions from persistence")
    
    # Load summaries
    minute_summaries = persistence.load_minute_summaries()
    print(f"Loaded {len(minute_summaries)} minute summaries from persistence")
    
    ten_minute_summaries = persistence.load_ten_minute_summaries()
    print(f"Loaded {len(ten_minute_summaries)} 10-minute summaries from persistence")
    
    # Initialize last_check_timestamp to current time
    # This prevents checking old actions from before the system started
    with last_check_lock:
        last_check_timestamp = time.time()
        print(f"Initialized last_check_timestamp to {last_check_timestamp}")
    
    initialize_services()
    print(f"Recent ops initialized: {recent_ops is not None}")
    print(f"Gemini client initialized: {gemini_client is not None}")
    print(f"Script executor initialized: {script_executor is not None}")
    print(f"Short-term agent initialized: {short_term_agent is not None}")
    print(f"Action registry initialized: {action_registry is not None}")
    print(f"App switch monitor initialized: {app_switch_monitor is not None}")
    print(f"Keyboard monitor initialized: {keyboard_monitor is not None}")
    
    if gemini_client and gemini_client.is_configured:
        print("Starting pattern detection...")
        # Start pattern detection thread
        pattern_detection_stop.clear()
        pattern_detection_thread = threading.Thread(target=pattern_detection_worker, daemon=True)
        pattern_detection_thread.start()
        print("Pattern detection started")
        
        # Start short-term pattern detection thread
        print("Starting short-term pattern detection...")
        short_term_detection_stop.clear()
        short_term_detection_thread = threading.Thread(target=short_term_pattern_detection_worker, daemon=True)
        short_term_detection_thread.start()
        print("Short-term pattern detection started")
        
        # Start minute summary thread
        print("Starting minute summary generation...")
        minute_summary_stop.clear()
        minute_summary_thread = threading.Thread(target=minute_summary_worker, daemon=True)
        minute_summary_thread.start()
        print("Minute summary generation started")
        
        # Start 10-minute summary thread
        print("Starting 10-minute summary generation...")
        ten_minute_summary_stop.clear()
        ten_minute_summary_thread = threading.Thread(target=ten_minute_summary_worker, daemon=True)
        ten_minute_summary_thread.start()
        print("10-minute summary generation started")
    
    # Start periodic save thread
    print("Starting periodic save...")
    save_stop.clear()
    save_thread = threading.Thread(target=periodic_save_worker, daemon=True)
    save_thread.start()
    print("Periodic save started")
    
    # Start email poller if we have accounts
    if email_poller and len(accounts.accounts) > 0:
        print("Starting email poller...")
        email_poller.start()
        print("Email poller started")
    else:
        print("Email poller not started - no email accounts configured")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    global ai_interactions
    
    print("Shutting down services...")
    
    # Stop monitors
    if app_switch_monitor:
        print("Stopping app switch monitor...")
        app_switch_monitor.stop()
    
    if keyboard_monitor:
        print("Stopping keyboard monitor...")
        keyboard_monitor.stop()
    
    # Stop app usage tracker
    print("Stopping app usage tracker...")
    app_usage_tracker.stop()
    
    # Save all data to persistence
    print("Saving data to persistence...")
    persistence.save_ai_interactions(ai_interactions)
    
    if recent_ops:
        # Save file operations
        operations = recent_ops.snapshot()
        file_ops_data = []
        for op in operations:
            file_ops_data.append({
                "event_type": op.event_type,
                "src_path": op.src_path,
                "dest_path": op.dest_path,
                "timestamp": op.timestamp,
                "file_size": op.file_size,
                "file_extension": op.file_extension,
                "operation_category": op.operation_category
            })
        persistence.save_file_operations(file_ops_data)
    
    if python_agent and hasattr(python_agent, 'get_execution_history'):
        # Save execution history
        execution_history = python_agent.get_execution_history()
        persistence.save_execution_history(execution_history)
    
    if pattern_detection_thread:
        pattern_detection_stop.set()
        pattern_detection_thread.join(timeout=2)
    
    if short_term_detection_thread:
        short_term_detection_stop.set()
        short_term_detection_thread.join(timeout=2)
    
    if minute_summary_thread:
        minute_summary_stop.set()
        minute_summary_thread.join(timeout=2)
    
    if ten_minute_summary_thread:
        ten_minute_summary_stop.set()
        ten_minute_summary_thread.join(timeout=2)
    
    if save_thread:
        save_stop.set()
        save_thread.join(timeout=2)
    
    if recent_ops:
        recent_ops.stop()
    
    print("Shutdown complete")

def calculate_time_saved_stats(file_operations, ai_interactions, execution_history):
    """Calculate time saved statistics from real historical data"""
    from datetime import datetime, timedelta
    import statistics
    import random
    
    # Time estimates for different operations (in minutes) - CONSERVATIVE
    OPERATION_TIME_ESTIMATES = {
        'file_creation': 0.5,    # Creating files manually (30 seconds)
        'file_edit': 0.5,         # Editing files manually (30 seconds)
        'file_move': 0.25,        # Moving files manually (15 seconds)
        'removal': 0.1,           # Deleting files manually (6 seconds)
        'ai_interaction': 0.5     # Time saved per AI interaction (30 seconds)
    }
    
    # Calculate total time saved
    total_time_saved = 0
    
    # Count operations by type
    operation_counts = {}
    for op in file_operations:
        op_type = op.get('operation_category', 'unknown')
        operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
        total_time_saved += OPERATION_TIME_ESTIMATES.get(op_type, 1)
    
    # Add time saved from AI interactions
    ai_time_saved = len(ai_interactions) * OPERATION_TIME_ESTIMATES['ai_interaction']
    total_time_saved += ai_time_saved
    
    # Add time saved from automation executions using real LLM estimations
    automation_time_saved = 0
    for execution in execution_history:
        # Use the actual time saved from LLM estimation if available
        if 'time_saved_seconds' in execution:
            automation_time_saved += execution['time_saved_seconds'] / 60  # Convert to minutes
        else:
            # Fallback to default estimation
            automation_time_saved += 5  # 5 minutes default
    
    total_time_saved += automation_time_saved
    
    # Calculate daily breakdown for last 30 days with realistic patterns
    daily_breakdown = []
    today = datetime.now().date()
    
    for i in range(30):
        date = today - timedelta(days=i)
        daily_time_saved = 0
        
        # Count operations for this day
        for op in file_operations:
            op_date = datetime.fromtimestamp(op.get('timestamp', 0)).date()
            if op_date == date:
                op_type = op.get('operation_category', 'unknown')
                daily_time_saved += OPERATION_TIME_ESTIMATES.get(op_type, 1)
        
        # Count AI interactions for this day
        for interaction in ai_interactions:
            try:
                interaction_date = datetime.fromisoformat(interaction.get('timestamp', '')).date()
                if interaction_date == date:
                    daily_time_saved += OPERATION_TIME_ESTIMATES['ai_interaction']
            except:
                # Handle different timestamp formats
                pass
        
        # Count executions for this day using real LLM estimations
        for execution in execution_history:
            exec_date = datetime.fromtimestamp(execution.get('timestamp', 0)).date()
            if exec_date == date:
                # Use actual time saved from LLM estimation if available
                if 'time_saved_seconds' in execution:
                    daily_time_saved += execution['time_saved_seconds'] / 60  # Convert to minutes
                else:
                    # Fallback to default estimation
                    daily_time_saved += 5  # 5 minutes default
        
        daily_breakdown.append({
            'date': date.isoformat(),
            'time_saved': round(daily_time_saved, 1)
        })
    
    # Calculate predictions for next 7 days
    predictions = []
    recent_days = [day['time_saved'] for day in daily_breakdown[:7] if day['time_saved'] > 0]
    
    if recent_days and len(recent_days) >= 3:
        # Calculate trend from recent activity (conservative)
        avg_daily = statistics.mean(recent_days)
        
        # Calculate trend (more conservative)
        if len(recent_days) >= 6:
            recent_avg = statistics.mean(recent_days[-3:])
            older_avg = statistics.mean(recent_days[:3])
            trend = (recent_avg - older_avg) / 3  # Per day trend
        else:
            trend = 0
        
        # Generate conservative predictions
        for i in range(1, 8):
            future_date = today + timedelta(days=i)
            # Base prediction with minimal trend and small variation
            base_prediction = avg_daily + (trend * i * 0.3)  # Reduce trend impact
            variation = random.uniform(-1, 2)  # Small variation
            predicted_time = max(0, base_prediction + variation)
            
            predictions.append({
                'date': future_date.isoformat(),
                'predicted_time_saved': round(predicted_time, 1)
            })
    elif recent_days:
        # Some data but not enough for trend analysis
        avg_daily = statistics.mean(recent_days)
        for i in range(1, 8):
            future_date = today + timedelta(days=i)
            predicted_time = max(0, avg_daily + random.uniform(-0.5, 1))
            predictions.append({
                'date': future_date.isoformat(),
                'predicted_time_saved': round(predicted_time, 1)
            })
    else:
        # No recent data, use very conservative predictions
        for i in range(1, 8):
            future_date = today + timedelta(days=i)
            predictions.append({
                'date': future_date.isoformat(),
                'predicted_time_saved': round(random.uniform(0.5, 3), 1)  # Very conservative
            })
    
    # Calculate automation efficiency
    total_operations = len(file_operations) + len(ai_interactions) + len(execution_history)
    automation_efficiency = (total_time_saved / max(total_operations, 1)) * 100
    
    return {
        'total_time_saved': round(total_time_saved, 1),
        'daily_breakdown': daily_breakdown,
        'predictions': predictions,
        'automation_efficiency': round(automation_efficiency, 1),
        'operation_counts': operation_counts,
        'ai_interactions_count': len(ai_interactions),
        'automation_executions_count': len(execution_history)
    }

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Hackyeah Automation Backend", "status": "running"}

@app.get("/config")
async def get_config():
    return {
        "nylas": {
            "api_key": config.nylas_api_key,
            "client_id": config.nylas_client_id,
            "redirect_uri": config.nylas_redirect_uri,
            "api_uri": config.nylas_api_uri
        },
        "gemini": {
            "api_key": config.gemini_api_key,
            "model": config.gemini_model
        },
        "watch": {
            "dirs": config.watch_dirs,
            "recent_ops_capacity": config.recent_ops_capacity,
            "pattern_interval_seconds": config.pattern_agent_interval_seconds
        },
        "logging": {
            "enabled": config.logging_enabled
        },
        "backend": {
            "port": config.backend_port
        }
    }

@app.put("/config")
async def update_config(config_update: ConfigUpdate):
    global config
    try:
        # Load current config
        import yaml
        with open("config.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        # Update with new values
        if config_update.nylas_api_key is not None:
            data.setdefault("nylas", {})["api_key"] = config_update.nylas_api_key
        if config_update.nylas_client_id is not None:
            data.setdefault("nylas", {})["client_id"] = config_update.nylas_client_id
        if config_update.nylas_redirect_uri is not None:
            data.setdefault("nylas", {})["redirect_uri"] = config_update.nylas_redirect_uri
        if config_update.nylas_api_uri is not None:
            data.setdefault("nylas", {})["api_uri"] = config_update.nylas_api_uri
        if config_update.gemini_api_key is not None:
            data.setdefault("gemini", {})["api_key"] = config_update.gemini_api_key
        if config_update.gemini_model is not None:
            data.setdefault("gemini", {})["model"] = config_update.gemini_model
        if config_update.watch_dirs is not None:
            data.setdefault("watch", {})["dirs"] = config_update.watch_dirs
        if config_update.pattern_agent_interval_seconds is not None:
            data.setdefault("watch", {})["pattern_interval_seconds"] = config_update.pattern_agent_interval_seconds
        if config_update.recent_ops_capacity is not None:
            data.setdefault("watch", {})["recent_ops_capacity"] = config_update.recent_ops_capacity
        if config_update.logging_enabled is not None:
            data.setdefault("logging", {})["enabled"] = config_update.logging_enabled
        if config_update.backend_port is not None:
            data.setdefault("backend", {})["port"] = config_update.backend_port
        
        # Check if backend port changed
        port_changed = config_update.backend_port is not None and config_update.backend_port != config.backend_port
        
        # Save updated config
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        
        # Reload config and reinitialize services
        config = load_config()
        initialize_services()
        
        print(f"File watcher restarted with directories: {config.watch_dirs}")
        
        response = {"message": "Config updated successfully"}
        if port_changed:
            response["restart_required"] = True
            response["message"] = "Config updated successfully. Backend port changed - restart required."
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts")
async def get_accounts():
    return {"accounts": accounts.list_identifiers()}

@app.post("/accounts/oauth")
async def add_oauth_account():
    if not nylas_handler:
        error_msg = "Nylas API key not configured"
        error_logger.log_error(error_msg, "oauth", "Please set Nylas API key in Settings")
        raise HTTPException(status_code=400, detail=f"{error_msg}. Please set it in Settings.")
    
    if not config.nylas_client_id:
        error_msg = "Nylas Client ID not configured"
        error_logger.log_error(error_msg, "oauth", "Please set Nylas Client ID in Settings")
        raise HTTPException(status_code=400, detail=f"{error_msg}. Please set it in Settings.")
    
    if not config.nylas_redirect_uri:
        error_msg = "Nylas Redirect URI not configured"
        error_logger.log_error(error_msg, "oauth", "Please set Nylas Redirect URI in Settings")
        raise HTTPException(status_code=400, detail=f"{error_msg}. Please set it in Settings.")
    
    try:
        url = nylas_handler.get_oauth_url(config.nylas_client_id, config.nylas_redirect_uri)
        if not url:
            error_msg = "Failed to create OAuth URL"
            error_logger.log_error(error_msg, "oauth", f"Client ID: {config.nylas_client_id}, Redirect URI: {config.nylas_redirect_uri}")
            raise HTTPException(status_code=500, detail=f"{error_msg}. Please check your Nylas configuration.")
        
        error_logger.log_info("OAuth URL generated successfully", "oauth", f"URL: {url}")
        return {"auth_url": url}
    except Exception as e:
        error_msg = f"OAuth URL generation failed: {str(e)}"
        error_logger.log_error(error_msg, "oauth", f"Client ID: {config.nylas_client_id}, Redirect URI: {config.nylas_redirect_uri}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/accounts/oauth/exchange")
async def exchange_oauth_code(request: OAuthRequest):
    if not nylas_handler:
        raise HTTPException(status_code=400, detail="Nylas not configured")
    
    result = nylas_handler.exchange_code_for_grant(
        request.code, 
        config.nylas_client_id, 
        config.nylas_redirect_uri
    )
    
    if not result:
        raise HTTPException(status_code=400, detail="Failed to exchange code")
    
    account = NylasEmailAccount(
        nylas_handler._nylas, 
        grant_id=result.grant_id, 
        email_address=result.email_address,
        verbose=config.logging_enabled
    )
    accounts.add(account)
    
    return {"message": "Account added successfully", "account_id": account.identifier}

@app.post("/accounts/email")
async def add_email_account(request: EmailAccountRequest):
    imap_host, pop3_host, smtp_host, domain = discover_email_servers(request.email)
    
    if not imap_host and not pop3_host:
        raise HTTPException(status_code=400, detail=f"Could not discover servers for {domain}")
    
    success = False
    account_id = None
    
    # Try IMAP first
    if imap_host:
        try:
            account = ImapEmailAccount(
                host=imap_host, 
                username=request.email, 
                password=request.password, 
                ssl=True, 
                smtp_host=smtp_host,
                verbose=config.logging_enabled
            )
            accounts.add(account)
            account_id = account.identifier
            success = True
        except Exception:
            pass
    
    # Try POP3 if IMAP failed
    if not success and pop3_host:
        try:
            account = Pop3EmailAccount(
                host=pop3_host, 
                username=request.email, 
                password=request.password, 
                ssl=True, 
                smtp_host=smtp_host,
                verbose=config.logging_enabled
            )
            accounts.add(account)
            account_id = account.identifier
            success = True
        except Exception:
            pass
    
    if not success:
        raise HTTPException(status_code=400, detail="Could not connect to discovered servers")
    
    return {"message": "Account added successfully", "account_id": account_id}

@app.delete("/accounts/{account_id}")
async def remove_account(account_id: str):
    accounts.remove(account_id)
    return {"message": "Account removed successfully"}

@app.get("/recent-actions")
async def get_recent_actions(category: Optional[str] = None):
    if not recent_ops:
        return {"actions": []}
    
    if category:
        operations = recent_ops.get_operations_by_category(category)
    else:
        operations = recent_ops.snapshot()
    
    actions = []
    for op in operations:
        actions.append({
            "id": f"{op.timestamp}_{op.src_path}",
            "type": op.event_type,
            "path": op.src_path,
            "dest_path": op.dest_path,
            "timestamp": op.timestamp,
            "file_size": op.file_size,
            "file_extension": op.file_extension,
            "operation_category": op.operation_category,
            "filename": os.path.basename(op.src_path),
            "directory": os.path.dirname(op.src_path),
            "is_file_move": op.event_type == "moved",
            "is_content_edit": op.operation_category == "content_edit",
            "is_system_operation": op.operation_category == "system"
        })
    
    # Sort by timestamp (newest first)
    actions.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"actions": actions}

@app.get("/recent-actions/detailed")
async def get_detailed_actions():
    """Get recent actions with enhanced details"""
    if not recent_ops:
        return {"actions": []}
    
    operations = recent_ops.get_operations_with_details()
    # Sort by timestamp (newest first)
    operations.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    
    return {"actions": operations}

@app.get("/recent-actions/filtered")
async def get_filtered_actions():
    """Get recent actions filtered to show only user-initiated actions"""
    if not recent_ops or not gemini_client:
        return {"actions": []}
    
    # Get all operations
    all_ops = recent_ops.snapshot()
    
    # Create action filter agent
    action_filter = ActionFilterAgent(gemini_client)
    
    # Filter out program-generated actions
    filtered_ops = action_filter.filter_user_actions(all_ops)
    
    # Convert to detailed format
    actions = []
    for op in filtered_ops:
        actions.append({
            "id": f"{op.timestamp}_{op.src_path}",
            "event_type": op.event_type,
            "src_path": op.src_path,
            "dest_path": op.dest_path,
            "timestamp": op.timestamp,
            "file_size": op.file_size,
            "file_extension": op.file_extension,
            "operation_category": op.operation_category,
            "filename": os.path.basename(op.src_path),
            "directory": os.path.dirname(op.src_path),
            "is_file_move": op.event_type == "moved",
            "is_content_edit": op.operation_category == "content_edit",
            "is_system_operation": op.operation_category == "system"
        })
    
    # Sort by timestamp (newest first)
    actions.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"actions": actions}

@app.get("/ai-interactions")
async def get_ai_interactions():
    print(f"AI interactions endpoint called, returning {len(ai_interactions)} interactions")
    # Sort by timestamp (newest first)
    sorted_interactions = sorted(ai_interactions, key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"interactions": sorted_interactions}

@app.get("/automation-history")
async def get_automation_history():
    """Get automation history from AI interactions"""
    # Filter AI interactions to only include automation-related ones
    automation_interactions = [
        interaction for interaction in ai_interactions 
        if interaction.get("agent") == "AutomationAgent" and 
           interaction.get("context", {}).get("automation_created", False)
    ]
    
    # Sort by timestamp (newest first)
    sorted_automations = sorted(automation_interactions, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    print(f"Automation history endpoint called, returning {len(sorted_automations)} automations")
    return {"automations": sorted_automations}

@app.get("/debug-status")
async def debug_status():
    """Debug endpoint to check system status"""
    ops_count = len(recent_ops.snapshot()) if recent_ops else 0
    agents_initialized = {
        "action_filter": action_filter is not None,
        "pattern_detector": pattern_detector is not None,
        "pattern_spotter": pattern_spotter is not None,
        "automation_agent": automation_agent is not None,
        "python_agent": python_agent is not None
    }
    gemini_configured = gemini_client.is_configured if gemini_client else False
    
    return {
        "file_operations_count": ops_count,
        "ai_interactions_count": len(ai_interactions),
        "agents_initialized": agents_initialized,
        "gemini_configured": gemini_configured,
        "pattern_detection_running": pattern_detection_thread is not None and pattern_detection_thread.is_alive(),
        "recent_ops_running": recent_ops is not None and hasattr(recent_ops, 'observer') and recent_ops.observer.is_alive() if recent_ops else False
    }

@app.post("/test-ai-interaction")
async def test_ai_interaction():
    """Test endpoint to manually trigger an AI interaction"""
    test_prompt = "Test prompt for AI interaction logging"
    test_response = "Test response from AI system"
    log_ai_interaction("TestAgent", test_prompt, test_response)
    return {"message": "Test AI interaction logged", "total_interactions": len(ai_interactions)}

@app.post("/test-pattern-detection")
async def test_pattern_detection():
    """Test endpoint to manually trigger pattern detection with fake data"""
    if not action_filter or not pattern_detector or not pattern_spotter:
        return {"error": "Agents not initialized"}
    
    # Create fake file operations for testing
    from src.recent_ops import FileOp
    import time
    
    fake_ops = [
        FileOp("created", "C:\\Users\\test\\Desktop\\test1.txt", None, time.time(), 1024, ".txt", "file_creation"),
        FileOp("created", "C:\\Users\\test\\Desktop\\test2.txt", None, time.time(), 2048, ".txt", "file_creation"),
        FileOp("modified", "C:\\Users\\test\\Desktop\\test1.txt", None, time.time(), 1024, ".txt", "file_edit"),
    ]
    
    print(f"Testing pattern detection with {len(fake_ops)} fake operations")
    
    # Stage 1: Filter out program-generated actions
    filtered_ops = action_filter.filter_user_actions(fake_ops)
    print(f"Filtered to {len(filtered_ops)} user actions")
    
    if filtered_ops:
        # Stage 2: Analyze patterns
        analysis = pattern_detector.analyze_patterns(filtered_ops)
        print(f"Analysis completed: {analysis[:100]}...")
        
        # Stage 3: Make final spotting decision
        spotting_response = pattern_spotter.spot_pattern(analysis, filtered_ops)
        print(f"Spotting response: {spotting_response[:100]}...")
        
        # Stage 4: Create automation if pattern spotted
        automation_created = False
        automation_script = None
        if pattern_spotter.has_spotted_pattern(spotting_response) and automation_agent:
            try:
                print("Creating automation script...")
                automation_script = automation_agent.create_automation_script(spotting_response, filtered_ops)
                automation_created = True
                print(f"Automation script created: {automation_script[:100]}...")
            except Exception as e:
                print(f"Error creating automation script: {e}")
        
        return {
            "message": "Pattern detection test completed",
            "original_ops": len(fake_ops),
            "filtered_ops": len(filtered_ops),
            "analysis": analysis[:200],
            "spotting_response": spotting_response[:200],
            "pattern_spotted": pattern_spotter.has_spotted_pattern(spotting_response),
            "automation_created": automation_created,
            "automation_script": automation_script[:200] if automation_script else None,
            "ai_interactions": len(ai_interactions)
        }
    else:
        return {"message": "No operations after filtering", "ai_interactions": len(ai_interactions)}

@app.post("/test-automation-creation")
async def test_automation_creation():
    """Test endpoint to manually create an automation script"""
    if not automation_agent:
        return {"error": "AutomationAgent not initialized"}
    
    # Create fake pattern description and operations
    from src.recent_ops import FileOp
    import time
    
    fake_ops = [
        FileOp("created", "C:\\Users\\test\\Desktop\\document1.txt", None, time.time(), 1024, ".txt", "file_creation"),
        FileOp("created", "C:\\Users\\test\\Desktop\\document2.txt", None, time.time(), 2048, ".txt", "file_creation"),
        FileOp("modified", "C:\\Users\\test\\Desktop\\document1.txt", None, time.time(), 1024, ".txt", "file_edit"),
    ]
    
    pattern_description = "User is creating and modifying text documents in the Desktop folder"
    
    try:
        automation_script = automation_agent.create_automation_script(pattern_description, fake_ops)
        return {
            "message": "Automation script created successfully",
            "pattern_description": pattern_description,
            "operations_count": len(fake_ops),
            "script_length": len(automation_script),
            "script_preview": automation_script[:300],
            "ai_interactions": len(ai_interactions)
        }
    except Exception as e:
        return {"error": f"Failed to create automation script: {str(e)}", "ai_interactions": len(ai_interactions)}

@app.post("/save-data")
async def save_data():
    """Manually save all data to persistence"""
    try:
        # Save AI interactions
        persistence.save_ai_interactions(ai_interactions)
        
        # Save file operations
        if recent_ops:
            operations = recent_ops.snapshot()
            file_ops_data = []
            for op in operations:
                file_ops_data.append({
                    "event_type": op.event_type,
                    "src_path": op.src_path,
                    "dest_path": op.dest_path,
                    "timestamp": op.timestamp,
                    "file_size": op.file_size,
                    "file_extension": op.file_extension,
                    "operation_category": op.operation_category
                })
            persistence.save_file_operations(file_ops_data)
        
        # Save execution history
        if python_agent and hasattr(python_agent, 'get_execution_history'):
            execution_history = python_agent.get_execution_history()
            persistence.save_execution_history(execution_history)
        
        return {"message": "Data saved successfully", "ai_interactions": len(ai_interactions)}
    except Exception as e:
        return {"error": f"Failed to save data: {str(e)}"}

@app.get("/emails")
async def get_emails(limit: int = 50):
    emails = accounts.fetch_aggregated_recent(limit=limit)
    result = []
    for email in emails:
        result.append({
            "subject": email.subject,
            "from": email.from_addr,
            "to": email.to_addr,
            "date": email.date.isoformat(),
            "uid": email.uid
        })
    return {"emails": result}

@app.post("/emails/send")
async def send_email(request: dict):
    """Send an email through a configured account"""
    try:
        account_id = request.get("account_id")
        to_email = request.get("to")
        subject = request.get("subject")
        body = request.get("body")
        
        if not all([account_id, to_email, subject, body]):
            raise HTTPException(status_code=400, detail="Missing required fields: account_id, to, subject, body")
        
        # Find the account
        account = None
        for acc in accounts.accounts:
            if acc.identifier == account_id:
                account = acc
                break
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account.send_email(to_email, subject, body)
        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patterns")
async def get_patterns():
    """Get recent patterns detected by the pattern agent"""
    if not planner:
        return {"patterns": []}
    
    return {"patterns": planner.get_patterns()}

@app.post("/patterns/execute")
async def execute_pattern(request: dict):
    """Execute a pattern-based automation"""
    try:
        pattern_description = request.get("description")
        if not pattern_description:
            raise HTTPException(status_code=400, detail="Pattern description required")
        
        if not planner:
            raise HTTPException(status_code=500, detail="Planner not available")
        
        steps = planner.plan_from_pattern(pattern_description)
        return {"steps": steps, "message": "Pattern analyzed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/patterns/generate-script")
async def generate_script_from_pattern(request: dict):
    """Generate a Python script from a detected pattern"""
    try:
        pattern_description = request.get("description")
        if not pattern_description:
            raise HTTPException(status_code=400, detail="Pattern description required")
        
        if not automation_agent:
            raise HTTPException(status_code=500, detail="Automation agent not available")
        
        # Get recent operations for context
        ops = recent_ops.snapshot()[-20:] if recent_ops else []
        script = automation_agent.create_automation_script(pattern_description, ops)
        return {"script": script, "message": "Script generated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/python/execute")
async def execute_python_script(request: dict):
    """Execute a Python automation script"""
    try:
        script = request.get("script")
        if not script:
            raise HTTPException(status_code=400, detail="Script required")
        
        if not python_agent:
            raise HTTPException(status_code=500, detail="Python agent not available")
        
        result = python_agent.execute_script(script)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/python/history")
async def get_python_execution_history():
    """Get Python script execution history"""
    if not python_agent:
        return {"history": []}
    
    return {"history": python_agent.get_execution_history()}

@app.post("/python/generate-from-conversation")
async def generate_script_from_conversation(request: dict):
    """Generate a Python script from conversation transcript"""
    try:
        transcript = request.get("transcript")
        if not transcript:
            raise HTTPException(status_code=400, detail="Transcript required")
        
        if not python_agent:
            raise HTTPException(status_code=500, detail="Python agent not available")
        
        script = python_agent.script_from_conversation(transcript)
        return {"script": script, "message": "Script generated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/python/execution/{execution_id}")
async def get_execution_by_id(execution_id: int):
    """Get specific execution record by ID"""
    if not python_agent:
        raise HTTPException(status_code=500, detail="Python agent not available")
    
    execution = python_agent.get_execution_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return execution

@app.delete("/python/history")
async def clear_execution_history():
    """Clear execution history"""
    if not python_agent:
        raise HTTPException(status_code=500, detail="Python agent not available")
    
    python_agent.clear_execution_history()
    return {"message": "Execution history cleared"}

@app.post("/python/reload-security")
async def reload_security_config():
    """Reload security configuration"""
    if not python_agent:
        raise HTTPException(status_code=500, detail="Python agent not available")
    
    python_agent.reload_security_config()
    return {"message": "Security configuration reloaded"}

@app.get("/errors")
async def get_errors(limit: int = 50, source: Optional[str] = None):
    """Get recent errors"""
    if source:
        return {"errors": error_logger.get_errors_by_source(source)}
    return {"errors": error_logger.get_errors(limit)}

@app.delete("/errors")
async def clear_errors():
    """Clear all errors"""
    error_logger.clear_errors()
    return {"message": "Errors cleared successfully"}

@app.get("/errors/count")
async def get_error_count():
    """Get total error count"""
    return {"count": error_logger.get_error_count()}

# Automation Agent endpoints
@app.get("/patterns")
async def get_patterns():
    """Get all detected patterns"""
    if not planner:
        return {"patterns": []}
    return {"patterns": planner.get_patterns()}

@app.post("/generate-automation-plan")
async def generate_automation_plan(request: dict):
    """Generate automation plan from pattern"""
    if not planner or not request.get("pattern_description"):
        return {"plan": ""}
    
    pattern_description = request["pattern_description"]
    plan = planner.plan_from_pattern(pattern_description)
    return {"plan": plan}


@app.get("/execution-history")
async def get_execution_history():
    """Get script execution history"""
    try:
        if not python_agent:
            return {"executions": []}
        
        # Check if the method exists
        if not hasattr(python_agent, 'get_execution_history'):
            print(f"ERROR: python_agent does not have get_execution_history method")
            return {"executions": []}
        
        result = python_agent.get_execution_history()
        return {"executions": result}
    except Exception as e:
        print(f"ERROR in get_execution_history: {e}")
        import traceback
        traceback.print_exc()
        return {"executions": []}

@app.get("/shutdown")
async def shutdown_backend_get():
    """Test endpoint for shutdown"""
    return {"message": "Shutdown endpoint is working", "method": "GET"}

@app.post("/shutdown")
async def shutdown_backend():
    """Shutdown the backend server"""
    import os
    import signal
    
    print("Backend shutdown requested via API endpoint")
    print("Shutdown endpoint called successfully")
    
    # Kill all frontend processes (Node.js, Electron, React dev server)
    try:
        import subprocess
        import platform
        
        print("Terminating frontend processes...")
        if platform.system() == "Windows":
            # Kill Node.js processes related to the project
            subprocess.run([
                "taskkill", "/F", "/IM", "node.exe", 
                "/FI", "WINDOWTITLE eq *localhost:3000*"
            ], capture_output=True)
            
            subprocess.run([
                "taskkill", "/F", "/IM", "electron.exe"
            ], capture_output=True)
            
            subprocess.run([
                "taskkill", "/F", "/IM", "node.exe", 
                "/FI", "COMMANDLINE eq *react-scripts*"
            ], capture_output=True)
            
            subprocess.run([
                "taskkill", "/F", "/IM", "node.exe", 
                "/FI", "COMMANDLINE eq *webpack*"
            ], capture_output=True)
            
            subprocess.run([
                "taskkill", "/F", "/IM", "node.exe", 
                "/FI", "COMMANDLINE eq *hackyeah*"
            ], capture_output=True)
        else:
            # Unix-like systems
            subprocess.run(["pkill", "-f", "react-scripts"], capture_output=True)
            subprocess.run(["pkill", "-f", "webpack"], capture_output=True)
            subprocess.run(["pkill", "-f", "electron"], capture_output=True)
            subprocess.run(["pkill", "-f", "hackyeah"], capture_output=True)
            
        print("Frontend processes terminated")
    except Exception as e:
        print(f"Error terminating frontend processes: {e}")
    
    # Check if we're running in tray mode
    try:
        # Try to import and use the tray app's shutdown method
        from tray_backend import BackendTrayApp
        # If we can import it, we might be in tray mode
        # We'll use a global variable to signal shutdown
        global tray_app_instance
        if 'tray_app_instance' in globals() and tray_app_instance:
            tray_app_instance.request_shutdown()
            return {"message": "Backend shutdown requested via tray", "status": "shutting_down"}
    except ImportError:
        pass
    
    # Fallback for non-tray mode
    # Stop pattern detection
    if pattern_detection_thread:
        pattern_detection_stop.set()
        pattern_detection_thread.join(timeout=2)
    
    # Stop file watcher
    if recent_ops:
        recent_ops.stop()
    
    # Shutdown the server
    def shutdown_server():
        import threading
        import time
        time.sleep(1)  # Give time for response to be sent
        os._exit(0)
    
    # Start shutdown in a separate thread
    shutdown_thread = threading.Thread(target=shutdown_server, daemon=True)
    shutdown_thread.start()
    
    return {"message": "Backend shutdown initiated", "status": "shutting_down"}

@app.get("/app-usage/today")
async def get_today_app_usage():
    """Get app usage statistics for today"""
    try:
        print("\n" + "="*60)
        print("[API] /app-usage/today")
        usage = app_usage_tracker.get_today_usage()
        
        print(f"[API] Received from tracker: {len(usage)} apps, {sum(usage.values()):.1f} total seconds")
        
        # Convert seconds to minutes for better readability
        usage_minutes = {app: round(seconds / 60, 1) for app, seconds in usage.items()}
        
        # Sort by usage time (descending)
        sorted_usage = dict(sorted(usage_minutes.items(), key=lambda x: x[1], reverse=True))
        
        response = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "usage": sorted_usage,
            "total_minutes": round(sum(usage.values()) / 60, 1)
        }
        
        print(f"[API] Sending to frontend: {len(response['usage'])} apps, {response['total_minutes']} total minutes")
        print(f"[API] Top 5 apps: {list(sorted_usage.items())[:5]}")
        print("="*60 + "\n")
        
        return response
    except Exception as e:
        print(f"[API] ERROR getting today's app usage: {e}")
        import traceback
        traceback.print_exc()
        return {"date": datetime.now().strftime("%Y-%m-%d"), "usage": {}, "total_minutes": 0}

@app.get("/app-usage/week")
async def get_week_app_usage():
    """Get app usage statistics for the past 7 days"""
    try:
        print("\n[API] /app-usage/week")
        week_usage = app_usage_tracker.get_week_usage()
        
        print(f"[API] Received from tracker: {len(week_usage)} days of data")
        
        # Convert seconds to minutes for each day
        formatted_week = {}
        for date, apps in week_usage.items():
            formatted_week[date] = {
                "apps": {app: round(seconds / 60, 1) for app, seconds in apps.items()},
                "total_minutes": round(sum(apps.values()) / 60, 1)
            }
        
        # Sort by date (most recent first)
        sorted_week = dict(sorted(formatted_week.items(), reverse=True))
        
        print(f"[API] Sending to frontend: {list(sorted_week.keys())}\n")
        
        return {"week_usage": sorted_week}
    except Exception as e:
        print(f"[API] ERROR getting week app usage: {e}")
        import traceback
        traceback.print_exc()
        return {"week_usage": {}}

@app.get("/app-usage/hourly")
async def get_hourly_app_usage(date: Optional[str] = None):
    """Get hourly breakdown of app usage for a specific date (defaults to today)"""
    try:
        print(f"\n[API] /app-usage/hourly (date={date})")
        hourly_usage = app_usage_tracker.get_hourly_usage(date)
        
        print(f"[API] Received from tracker: {len(hourly_usage)} hours")
        
        # Convert seconds to minutes for each hour
        formatted_hourly = {}
        for hour, apps in hourly_usage.items():
            formatted_hourly[hour] = {
                "apps": {app: round(seconds / 60, 1) for app, seconds in apps.items()},
                "total_minutes": round(sum(apps.values()) / 60, 1)
            }
        
        response = {
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "hourly_usage": formatted_hourly
        }
        
        print(f"[API] Sending to frontend: {len(formatted_hourly)} hours\n")
        
        return response
    except Exception as e:
        print(f"[API] ERROR getting hourly app usage: {e}")
        import traceback
        traceback.print_exc()
        return {"date": date or datetime.now().strftime("%Y-%m-%d"), "hourly_usage": {}}

@app.get("/app-usage/stats")
async def get_app_usage_stats():
    """Get summary statistics about app usage"""
    try:
        print("\n[API] /app-usage/stats")
        stats = app_usage_tracker.get_stats_summary()
        
        print(f"[API] Stats from tracker: {stats}")
        
        # Convert seconds to minutes
        if stats.get("total_time_today_seconds"):
            stats["total_time_today_minutes"] = round(stats["total_time_today_seconds"] / 60, 1)
        if stats.get("most_used_app_duration_seconds"):
            stats["most_used_app_duration_minutes"] = round(stats["most_used_app_duration_seconds"] / 60, 1)
        
        print(f"[API] Sending stats to frontend: {stats}\n")
        
        return stats
    except Exception as e:
        print(f"[API] ERROR getting app usage stats: {e}")
        import traceback
        traceback.print_exc()
        return {
            "total_time_today_seconds": 0,
            "total_time_today_minutes": 0,
            "most_used_app_today": None,
            "most_used_app_duration_seconds": 0,
            "most_used_app_duration_minutes": 0,
            "unique_apps_tracked": 0,
            "current_app": None
        }

@app.get("/app-usage/debug")
async def debug_app_usage():
    """Debug endpoint to check data loading"""
    import os
    return {
        "data_file_path": str(app_usage_tracker.data_file),
        "data_file_absolute": str(app_usage_tracker.data_file.absolute()),
        "file_exists": app_usage_tracker.data_file.exists(),
        "file_size": app_usage_tracker.data_file.stat().st_size if app_usage_tracker.data_file.exists() else 0,
        "cwd": os.getcwd(),
        "hourly_data_keys_count": len(app_usage_tracker._hourly_data),
        "sample_keys": list(app_usage_tracker._hourly_data.keys())[:10]
    }

@app.get("/time-saved-stats")
async def get_time_saved_stats():
    """Return real time saved statistics for frontend plot"""
    from datetime import datetime, timedelta
    import json
    global total_time_saved_seconds
    
    try:
        # Get real data from persistence
        file_operations = persistence.load_file_operations()
        ai_interactions = persistence.load_ai_interactions()
        
        # Get execution history from persisted data
        time_saved_data = persistence.load_time_saved_data()
        execution_history = time_saved_data.get("automation_executions", [])
        
        # Also include any recent completions from pending suggestions
        with pending_lock:
            for suggestion in pending_suggestions:
                if suggestion.get("status") == "completed" and suggestion.get("time_saved_seconds"):
                    # Check if this suggestion is already in persisted data
                    suggestion_id = suggestion.get("suggestion_id")
                    if not any(exec["suggestion_id"] == suggestion_id for exec in execution_history):
                        execution_history.append({
                            "suggestion_id": suggestion_id,
                            "timestamp": suggestion.get("timestamp", time.time()),
                            "time_saved_seconds": suggestion.get("time_saved_seconds", 0)
                        })
        
        # Calculate real statistics
        stats = calculate_time_saved_stats(file_operations, ai_interactions, execution_history)
        
        # Use the calculated total time saved (already in minutes)
        # Don't override with global variable to avoid inconsistencies
        
        # Add real automation execution count
        completed_automations = len([s for s in pending_suggestions if s.get("status") == "completed"])
        stats["automation_executions_count"] = completed_automations
        
        return {"status": "success", "stats": stats}
        
    except Exception as e:
        print(f"Error calculating time saved stats: {e}")
        # Fallback to basic stats if calculation fails
        # Use persisted data instead of global variable
        try:
            time_saved_data = persistence.load_time_saved_data()
            total_minutes = time_saved_data.get("total_time_saved_seconds", 0) / 60
        except:
            total_minutes = 0
        
        return {
            "status": "success", 
            "stats": {
                "total_time_saved": total_minutes,
                "daily_breakdown": [],
                "predictions": [],
                "automation_efficiency": 0,
                "operation_counts": {},
                "ai_interactions_count": 0,
                "automation_executions_count": 0
            }
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "recent_ops": recent_ops is not None,
            "gemini": gemini_client is not None,
            "pattern_agent": pattern_agent is not None,
            "planner": planner is not None,
            "python_agent": python_agent is not None,
            "nylas_handler": nylas_handler is not None,
            "accounts": len(accounts.accounts) if accounts else 0
        }
    }

@app.get("/code")
async def oauth_code_handler(code: str = None):
    """OAuth code handler - displays code and allows copying"""
    from fastapi.responses import HTMLResponse
    
    if not code:
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>OAuth Code Required</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    background: white;
                    border-radius: 15px;
                    padding: 40px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                    width: 100%;
                }
                .icon {
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #333;
                    margin-bottom: 20px;
                    font-size: 24px;
                }
                p {
                    color: #666;
                    margin-bottom: 30px;
                    line-height: 1.6;
                }
                .error {
                    background: #fee;
                    border: 1px solid #fcc;
                    color: #c33;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">🔑</div>
                <h1>OAuth Code Required</h1>
                <p>This endpoint expects an OAuth authorization code as a query parameter.</p>
                <div class="error">
                    <strong>No code parameter provided.</strong><br>
                    Please include the authorization code in the URL.
                </div>
                <p>Expected format: <code>/code?code=YOUR_OAUTH_CODE</code></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=400)
    
    # Create HTML page with the OAuth code and copy functionality
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OAuth Code - Hackyeah</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: white;
                border-radius: 15px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 600px;
                width: 100%;
            }}
            .icon {{
                font-size: 48px;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
                font-size: 28px;
            }}
            .success {{
                background: #efe;
                border: 1px solid #cfc;
                color: #363;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                font-size: 16px;
            }}
            .code-container {{
                background: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                position: relative;
            }}
            .code-label {{
                color: #6c757d;
                font-size: 14px;
                margin-bottom: 10px;
                font-weight: 500;
            }}
            .code-value {{
                font-family: 'Courier New', monospace;
                font-size: 18px;
                color: #495057;
                word-break: break-all;
                background: white;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #e9ecef;
                margin-bottom: 15px;
            }}
            .copy-button {{
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);
            }}
            .copy-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4);
            }}
            .copy-button:active {{
                transform: translateY(0);
            }}
            .copy-button.copied {{
                background: linear-gradient(135deg, #17a2b8, #138496);
            }}
            .instructions {{
                color: #6c757d;
                margin-top: 20px;
                font-size: 14px;
                line-height: 1.5;
            }}
            .close-button {{
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 15px;
                font-size: 14px;
                cursor: pointer;
                margin-top: 20px;
                transition: background 0.3s ease;
            }}
            .close-button:hover {{
                background: #5a6268;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✅</div>
            <h1>OAuth Authorization Complete!</h1>
            <div class="success">
                <strong>Success!</strong> Your OAuth authorization code has been received.
            </div>
            
            <div class="code-container">
                <div class="code-label">Authorization Code:</div>
                <div class="code-value" id="authCode">{code}</div>
                <button class="copy-button" onclick="copyCode()" id="copyBtn">
                    📋 Copy Code
                </button>
            </div>
            
            <div class="instructions">
                <strong>Next Steps:</strong><br>
                1. Click "Copy Code" to copy the authorization code to your clipboard<br>
                2. Paste this code into the Hackyeah application<br>
                3. Your email account will be configured automatically
            </div>
            
            <button class="close-button" onclick="closeWindow()">
                Close Window
            </button>
        </div>

        <script>
            function copyCode() {{
                const codeElement = document.getElementById('authCode');
                const copyButton = document.getElementById('copyBtn');
                
                // Select and copy the code
                const textArea = document.createElement('textarea');
                textArea.value = codeElement.textContent;
                document.body.appendChild(textArea);
                textArea.select();
                
                try {{
                    document.execCommand('copy');
                    copyButton.innerHTML = '✅ Copied!';
                    copyButton.classList.add('copied');
                    
                    // Reset button after 2 seconds
                    setTimeout(() => {{
                        copyButton.innerHTML = '📋 Copy Code';
                        copyButton.classList.remove('copied');
                    }}, 2000);
                }} catch (err) {{
                    // Fallback for older browsers
                    alert('Code copied: ' + codeElement.textContent);
                }}
                
                document.body.removeChild(textArea);
            }}
            
            function closeWindow() {{
                window.close();
            }}
            
            // Auto-copy on page load (optional)
            // setTimeout(copyCode, 500);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

# New API Endpoints for Automation Workflow

@app.get("/automation/pending-suggestions")
async def get_pending_suggestions():
    """Get pending automation suggestions waiting for user response"""
    with pending_lock:
        # Return only pending suggestions
        pending = [s for s in pending_suggestions if s["status"] == "pending"]
        return {"suggestions": pending, "count": len(pending)}

@app.post("/automation/suggestion/{suggestion_id}/accept")
async def accept_suggestion(suggestion_id: str):
    """User accepts an automation suggestion"""
    with pending_lock:
        for suggestion in pending_suggestions:
            if suggestion["suggestion_id"] == suggestion_id:
                suggestion["status"] = "accepted"
                return {
                    "message": "Suggestion accepted",
                    "suggestion_id": suggestion_id,
                    "next_step": "Please provide an explanation of what you want to automate"
                }
        raise HTTPException(status_code=404, detail="Suggestion not found")

@app.post("/automation/suggestion/{suggestion_id}/reject")
async def reject_suggestion(suggestion_id: str):
    """User rejects an automation suggestion"""
    with pending_lock:
        for suggestion in pending_suggestions:
            if suggestion["suggestion_id"] == suggestion_id:
                suggestion["status"] = "rejected"
                
                # Add to ignored patterns so we don't suggest it again
                pattern_hash = suggestion.get("pattern_hash")
                if pattern_hash:
                    with ignored_patterns_lock:
                        ignored_patterns.add(pattern_hash)
                        print(f"Added pattern {pattern_hash} to ignored list")
                
                return {
                    "message": "Suggestion rejected",
                    "suggestion_id": suggestion_id
                }
        raise HTTPException(status_code=404, detail="Suggestion not found")

@app.post("/automation/suggestion/{suggestion_id}/explain")
async def provide_explanation(suggestion_id: str, request: dict):
    """User provides explanation for what they want to automate"""
    user_explanation = request.get("explanation")
    if not user_explanation:
        raise HTTPException(status_code=400, detail="Explanation required")
    
    with pending_lock:
        for suggestion in pending_suggestions:
            if suggestion["suggestion_id"] == suggestion_id:
                if suggestion["status"] != "accepted":
                    raise HTTPException(status_code=400, detail="Suggestion must be accepted first")
                
                suggestion["user_explanation"] = user_explanation
                suggestion["status"] = "explained"
                
                # Generate script based on explanation
                if automation_agent:
                    try:
                        # Create a combined prompt with pattern and user explanation
                        combined_description = f"{suggestion['pattern_description']}\n\nUser wants: {user_explanation}"
                        
                        # Get actions for context
                        action_details = []
                        for action in suggestion["actions"]:
                            if action["action_type"] == "file_operation":
                                details = action["details"]
                                action_details.append(f"- {details.get('event_type')}: {details.get('src_path')}")
                        
                        # Create a more detailed prompt for script generation
                        from .recent_ops import FileOp
                        file_ops = []
                        for action in suggestion["actions"]:
                            if action["action_type"] == "file_operation":
                                details = action["details"]
                                file_ops.append(FileOp(
                                    event_type=details.get("event_type", ""),
                                    src_path=details.get("src_path", ""),
                                    dest_path=details.get("dest_path"),
                                    timestamp=action["timestamp"],
                                    file_size=details.get("file_size"),
                                    file_extension=details.get("file_extension"),
                                    operation_category=details.get("operation_category")
                                ))
                        
                        script = automation_agent.create_automation_script(combined_description, file_ops)
                        suggestion["generated_script"] = script
                        
                        # Generate user-friendly summary
                        print(f"[SUMMARY] Generating script summary...")
                        print(f"[SUMMARY] script_summarizer available: {script_summarizer is not None}")
                        summary = "Summary not available"
                        if script_summarizer:
                            try:
                                print(f"[SUMMARY] Calling summarize_script with {len(script)} chars of code")
                                summary = script_summarizer.summarize_script(script)
                                print(f"[SUMMARY] Got summary: {len(summary)} chars")
                            except Exception as e:
                                print(f"[SUMMARY ERROR] Failed to generate summary: {e}")
                                import traceback
                                traceback.print_exc()
                                summary = "• The script will automate the detected pattern\n• Please review carefully before executing"
                        else:
                            print(f"[SUMMARY ERROR] script_summarizer is None!")
                        
                        suggestion["script_summary"] = summary
                        
                        return {
                            "message": "Script generated successfully",
                            "suggestion_id": suggestion_id,
                            "script": script,
                            "summary": summary,
                            "next_step": "Please review and confirm the script"
                        }
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Failed to generate script: {str(e)}")
                else:
                    raise HTTPException(status_code=500, detail="Automation agent not available")
        
        raise HTTPException(status_code=404, detail="Suggestion not found")

@app.post("/automation/suggestion/{suggestion_id}/refine")
async def refine_script(suggestion_id: str, request: dict):
    """User requests changes to the generated script"""
    refinement_request = request.get("refinement")
    if not refinement_request:
        raise HTTPException(status_code=400, detail="Refinement request required")
    
    with pending_lock:
        for suggestion in pending_suggestions:
            if suggestion["suggestion_id"] == suggestion_id:
                if not suggestion.get("generated_script"):
                    raise HTTPException(status_code=400, detail="No script generated yet")
                
                # Regenerate script with refinement
                if automation_agent:
                    try:
                        # Build description including any previous errors
                        error_context = ""
                        if suggestion.get("execution_result") and not suggestion["execution_result"].get("success"):
                            error_context = f"\n\nPrevious execution error:\n{suggestion['execution_result'].get('final_error', 'Unknown error')}"
                        
                        # Combine original explanation with refinement and errors
                        combined_description = f"{suggestion['pattern_description']}\n\nUser wants: {suggestion['user_explanation']}\n\nUser feedback: {refinement_request}{error_context}"
                        
                        # Get actions for context
                        from .recent_ops import FileOp
                        file_ops = []
                        for action in suggestion["actions"]:
                            if action["action_type"] == "file_operation":
                                details = action["details"]
                                file_ops.append(FileOp(
                                    event_type=details.get("event_type", ""),
                                    src_path=details.get("src_path", ""),
                                    dest_path=details.get("dest_path"),
                                    timestamp=action["timestamp"],
                                    file_size=details.get("file_size"),
                                    file_extension=details.get("file_extension"),
                                    operation_category=details.get("operation_category")
                                ))
                        
                        script = automation_agent.create_automation_script(combined_description, file_ops)
                        suggestion["generated_script"] = script
                        
                        # Generate new summary
                        print(f"[REFINE SUMMARY] Generating script summary...")
                        summary = "Summary not available"
                        if script_summarizer:
                            try:
                                print(f"[REFINE SUMMARY] Calling summarize_script with {len(script)} chars of code")
                                summary = script_summarizer.summarize_script(script)
                                print(f"[REFINE SUMMARY] Got summary: {len(summary)} chars")
                            except Exception as e:
                                print(f"[REFINE SUMMARY ERROR] Failed to generate summary: {e}")
                                import traceback
                                traceback.print_exc()
                                summary = "• The script will automate the detected pattern\n• Please review carefully before executing"
                        else:
                            print(f"[REFINE SUMMARY ERROR] script_summarizer is None!")
                        
                        suggestion["script_summary"] = summary
                        
                        # Store refinement history
                        if "refinement_history" not in suggestion:
                            suggestion["refinement_history"] = []
                        suggestion["refinement_history"].append(refinement_request)
                        
                        return {
                            "message": "Script refined successfully",
                            "suggestion_id": suggestion_id,
                            "script": script,
                            "summary": summary,
                            "next_step": "Please review and confirm the script"
                        }
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Failed to refine script: {str(e)}")
                else:
                    raise HTTPException(status_code=500, detail="Automation agent not available")
        
        raise HTTPException(status_code=404, detail="Suggestion not found")

@app.post("/automation/suggestion/{suggestion_id}/confirm-and-execute")
async def confirm_and_execute(suggestion_id: str):
    """User confirms the generated script and executes it"""
    global total_time_saved_seconds
    
    print(f"\n{'='*80}")
    print(f"[AUTOMATION EXECUTE] Starting execution for: {suggestion_id}")
    print(f"{'='*80}\n")
    
    with pending_lock:
        for suggestion in pending_suggestions:
            if suggestion["suggestion_id"] == suggestion_id:
                if suggestion["status"] != "explained":
                    raise HTTPException(status_code=400, detail="Script must be generated first")
                
                if not suggestion.get("generated_script"):
                    raise HTTPException(status_code=400, detail="No script available")
                
                if not automation_executor:
                    raise HTTPException(status_code=500, detail="Automation executor not available")
                
                suggestion["status"] = "executing"
                print(f"[AUTOMATION EXECUTE] Executing script ({len(suggestion['generated_script'])} chars)...")
                
                # Execute automation on a separate thread to prevent blocking
                def execute_automation_thread():
                    try:
                        print(f"[AUTOMATION EXECUTE] Starting execution in thread for suggestion {suggestion_id}")
                        execution_result = automation_executor.execute_automation(
                            suggestion["generated_script"],
                            suggestion["user_explanation"]
                        )
                        
                        print(f"[AUTOMATION EXECUTE] Script finished! Success: {execution_result.get('success', False)}")
                        
                        # Update suggestion with results
                        with pending_lock:
                            for s in pending_suggestions:
                                if s["suggestion_id"] == suggestion_id:
                                    s["execution_result"] = execution_result
                                    
                                    if execution_result["success"]:
                                        s["status"] = "completed"
                                        
                                        # Calculate time saved using AI-powered estimation
                                        if time_estimation_agent:
                                            print("[AUTOMATION EXECUTE] Estimating time saved with AI...")
                                            time_estimation = safe_agent_method_call(
                                                time_estimation_agent, 'estimate_time_saved', global_error_handler,
                                                suggestion["generated_script"],
                                                suggestion["user_explanation"],
                                                execution_result
                                            )
                                            if time_estimation:
                                                time_saved = time_estimation["estimated_time_saved_seconds"]
                                                s["time_saved_seconds"] = time_saved
                                                s["time_estimation_details"] = time_estimation
                                                print(f"[AUTOMATION EXECUTE] AI estimated {time_saved}s ({time_saved/60:.1f}min) saved")
                                            else:
                                                # Fallback estimation
                                                time_saved = len(suggestion["generated_script"]) * 2  # 2 seconds per character
                                                s["time_saved_seconds"] = time_saved
                                                print(f"[AUTOMATION EXECUTE] Fallback estimation: {time_saved}s saved")
                                        else:
                                            # Fallback estimation
                                            time_saved = len(suggestion["generated_script"]) * 2  # 2 seconds per character
                                            s["time_saved_seconds"] = time_saved
                                            print(f"[AUTOMATION EXECUTE] Fallback estimation: {time_saved}s saved")
                                        
                                        # Update global time saved counter
                                        global total_time_saved_seconds
                                        total_time_saved_seconds += time_saved
                                        print(f"[AUTOMATION EXECUTE] Total time saved: {total_time_saved_seconds}s ({total_time_saved_seconds/60:.1f}min)")
                                        
                                        # Save to persistence
                                        try:
                                            persistence.add_automation_time_saved(
                                                suggestion_id, 
                                                time_saved, 
                                                time.time()
                                            )
                                        except Exception as e:
                                            print(f"[AUTOMATION EXECUTE] Error saving time saved data: {e}")
                                    else:
                                        s["status"] = "failed"
                                        print(f"[AUTOMATION EXECUTE] Execution failed: {execution_result.get('final_error', 'Unknown error')}")
                                    break
                    except Exception as e:
                        print(f"[AUTOMATION EXECUTE] Error in execution thread: {e}")
                        global_error_handler.handle_agent_error("AutomationExecutor", "threaded_execution", e, {
                            'suggestion_id': suggestion_id,
                            'thread': True
                        })
                        # Update suggestion status to failed
                        with pending_lock:
                            for s in pending_suggestions:
                                if s["suggestion_id"] == suggestion_id:
                                    s["status"] = "failed"
                                    s["execution_result"] = {
                                        "success": False,
                                        "final_error": str(e)
                                    }
                                    break
                
                # Start execution in a separate thread
                execution_thread = threading.Thread(target=execute_automation_thread, daemon=True)
                execution_thread.start()
                print(f"[AUTOMATION EXECUTE] Started execution thread for suggestion {suggestion_id}")
                
                # Return immediately to prevent blocking the API
                return {
                    "message": "Automation execution started in background",
                    "suggestion_id": suggestion_id,
                    "status": "executing"
                }
        
        raise HTTPException(status_code=404, detail="Suggestion not found")

@app.get("/automation/suggestion/{suggestion_id}/status")
async def get_execution_status(suggestion_id: str):
    """Get the current execution status of a suggestion"""
    with pending_lock:
        for suggestion in pending_suggestions:
            if suggestion["suggestion_id"] == suggestion_id:
                execution_result = suggestion.get("execution_result", {})
                
                # Enhanced error information for failed executions
                error_details = None
                if suggestion["status"] == "failed" and execution_result:
                    error_details = {
                        "final_error": execution_result.get("final_error", "Unknown error"),
                        "attempts": execution_result.get("attempts", []),
                        "library_installation": execution_result.get("library_installation"),
                        "execution_id": execution_result.get("execution_id"),
                        "timestamp": execution_result.get("timestamp")
                    }
                
                return {
                    "suggestion_id": suggestion_id,
                    "status": suggestion["status"],
                    "execution_result": execution_result,
                    "time_saved_seconds": suggestion.get("time_saved_seconds"),
                    "time_estimation_details": suggestion.get("time_estimation_details"),
                    "error_details": error_details
                }
    
    raise HTTPException(status_code=404, detail="Suggestion not found")

@app.get("/automation/suggestions/all")
async def get_all_suggestions():
    """Get all automation suggestions (for history)"""
    with pending_lock:
        return {"suggestions": pending_suggestions, "count": len(pending_suggestions)}

@app.get("/automation/action-registry/stats")
async def get_action_registry_stats():
    """Get statistics about the action registry"""
    if not action_registry:
        return {"error": "Action registry not available"}
    return action_registry.get_action_stats()

@app.get("/automation/action-registry/recent")
async def get_recent_actions_from_registry(seconds: int = 300):
    """Get recent actions from the action registry (default last 5 minutes)"""
    if not action_registry:
        return {"actions": []}
    
    actions = action_registry.get_recent_actions(seconds=seconds)
    return {
        "actions": [a.to_dict() for a in actions],
        "count": len(actions)
    }

@app.get("/automation/action-registry/all")
async def get_all_actions_from_registry(limit: int = 100):
    """Get all actions from the action registry (limited to most recent)"""
    if not action_registry:
        return {"actions": []}
    
    all_actions = action_registry.get_all_actions()
    # Get last N actions
    limited_actions = list(all_actions)[-limit:] if len(all_actions) > limit else list(all_actions)
    # Reverse to show newest first
    limited_actions.reverse()
    
    return {
        "actions": [a.to_dict() for a in limited_actions],
        "count": len(limited_actions),
        "total_count": len(all_actions)
    }

@app.get("/automation/keyboard/recent")
async def get_recent_keyboard_activity():
    """Get recent keyboard activity (last 30 keys)"""
    if not keyboard_monitor:
        return {"keys": [], "sequence": ""}
    
    recent_keys = keyboard_monitor.get_recent_keys()
    return {
        "keys": recent_keys,
        "sequence": ' '.join(recent_keys),
        "count": len(recent_keys)
    }

@app.get("/automation/current-activity")
async def get_current_activity():
    """Get current user activity including active app and recent keys"""
    activity = {
        "current_app": None,
        "current_window": None,
        "recent_keys": [],
        "recent_app_switches": [],
        "keyboard_sequence": ""
    }
    
    # Get current active window
    if app_switch_monitor:
        import sys
        if sys.platform == 'win32':
            try:
                import win32gui
                import win32process
                import psutil
                
                hwnd = win32gui.GetForegroundWindow()
                if hwnd != 0:
                    window_title = win32gui.GetWindowText(hwnd)
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        process = psutil.Process(pid)
                        app_name = process.name()
                        if app_name.lower().endswith('.exe'):
                            app_name = app_name[:-4]
                        activity["current_app"] = app_name
                        activity["current_window"] = window_title
                    except:
                        pass
            except Exception as e:
                print(f"Error getting current window: {e}")
    
    # Get recent keyboard activity
    if keyboard_monitor:
        recent_keys = keyboard_monitor.get_recent_keys()
        activity["recent_keys"] = recent_keys
        activity["keyboard_sequence"] = ' '.join(recent_keys)
    
    # Get recent app switches from action registry
    if action_registry:
        app_switch_actions = action_registry.get_actions(action_type="app_switch", limit=10)
        activity["recent_app_switches"] = [
            {
                "app_name": action.details.get("app_name"),
                "window_title": action.details.get("window_title"),
                "timestamp": action.timestamp,
                "time_ago": format_time_ago(action.timestamp)
            }
            for action in app_switch_actions
        ]
    
    return activity

def format_time_ago(timestamp: float) -> str:
    """Format timestamp as 'X seconds/minutes/hours ago'"""
    import time
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return f"{int(diff)}s ago"
    elif diff < 3600:
        return f"{int(diff / 60)}m ago"
    elif diff < 86400:
        return f"{int(diff / 3600)}h ago"
    else:
        return f"{int(diff / 86400)}d ago"

@app.get("/automation/long-term/status")
async def get_long_term_status():
    """Get status of long-term pattern detection"""
    if not long_term_agent:
        return {"status": "not_available"}
    
    result = long_term_agent.detect_long_term_pattern([])
    return result

@app.get("/automation/time-saved")
async def get_time_saved():
    """Get total time saved statistics"""
    global total_time_saved_seconds
    
    with time_saved_lock:
        total_seconds = total_time_saved_seconds
    
    hours = int(total_seconds / 3600)
    minutes = int((total_seconds % 3600) / 60)
    seconds = int(total_seconds % 60)
    
    return {
        "total_seconds": total_seconds,
        "total_minutes": total_seconds / 60,
        "total_hours": total_seconds / 3600,
        "display": f"{hours}h {minutes}m {seconds}s",
        "human_readable": f"{hours} hours, {minutes} minutes, {seconds} seconds" if hours > 0 else f"{minutes} minutes, {seconds} seconds"
    }

@app.get("/automation/time-estimation/{suggestion_id}")
async def get_time_estimation_details(suggestion_id: str):
    """Get detailed time estimation information for a specific automation suggestion"""
    global pending_suggestions
    
    with pending_lock:
        for suggestion in pending_suggestions:
            if suggestion["suggestion_id"] == suggestion_id:
                if "time_estimation_details" in suggestion:
                    return {
                        "suggestion_id": suggestion_id,
                        "time_estimation": suggestion["time_estimation_details"],
                        "time_saved_seconds": suggestion.get("time_saved_seconds", 0)
                    }
                else:
                    return {
                        "suggestion_id": suggestion_id,
                        "error": "No time estimation details available",
                        "time_saved_seconds": suggestion.get("time_saved_seconds", 0)
                    }
    
    raise HTTPException(status_code=404, detail="Suggestion not found")

@app.post("/automation/mute")
async def mute_automation(request: dict):
    """Mute automation suggestions for a specified duration"""
    global muted_until
    
    minutes = request.get("minutes", 10)
    current_time = time.time()
    mute_duration_seconds = minutes * 60
    
    with muted_until_lock:
        muted_until = current_time + mute_duration_seconds
    
    # Calculate muted until time in human readable format
    import datetime
    muted_until_datetime = datetime.datetime.fromtimestamp(muted_until)
    
    print(f"Automation muted for {minutes} minutes until {muted_until_datetime.strftime('%H:%M:%S')}")
    
    return {
        "success": True,
        "muted_for_minutes": minutes,
        "muted_until": muted_until,
        "muted_until_display": muted_until_datetime.strftime('%H:%M:%S'),
        "message": f"Automation suggestions muted for {minutes} minutes"
    }

# Long-term summarization API endpoints

@app.get("/summaries/minute")
async def get_minute_summaries(limit: int = 100):
    """Get minute summaries (most recent first)"""
    with minute_summaries_lock:
        # Return most recent summaries first
        recent_summaries = list(minute_summaries)[-limit:] if len(minute_summaries) > limit else list(minute_summaries)
        recent_summaries.reverse()  # Newest first
        return {
            "summaries": recent_summaries,
            "count": len(recent_summaries),
            "total_count": len(minute_summaries)
        }

@app.get("/summaries/ten-minute")
async def get_ten_minute_summaries(limit: int = 100):
    """Get 10-minute summaries (most recent first)"""
    with ten_minute_summaries_lock:
        # Return most recent summaries first
        recent_summaries = list(ten_minute_summaries)[-limit:] if len(ten_minute_summaries) > limit else list(ten_minute_summaries)
        recent_summaries.reverse()  # Newest first
        return {
            "summaries": recent_summaries,
            "count": len(recent_summaries),
            "total_count": len(ten_minute_summaries)
        }

@app.delete("/summaries/minute/{summary_id}")
async def delete_minute_summary(summary_id: str):
    """Delete a minute summary"""
    global minute_summaries
    
    with minute_summaries_lock:
        original_count = len(minute_summaries)
        minute_summaries = [s for s in minute_summaries if s.get("id") != summary_id]
        
        if len(minute_summaries) < original_count:
            # Also delete from persistence
            persistence.delete_minute_summary(summary_id)
            return {"message": "Minute summary deleted", "summary_id": summary_id}
        else:
            raise HTTPException(status_code=404, detail="Minute summary not found")

@app.delete("/summaries/ten-minute/{summary_id}")
async def delete_ten_minute_summary(summary_id: str):
    """Delete a 10-minute summary"""
    global ten_minute_summaries
    
    with ten_minute_summaries_lock:
        original_count = len(ten_minute_summaries)
        ten_minute_summaries = [s for s in ten_minute_summaries if s.get("id") != summary_id]
        
        if len(ten_minute_summaries) < original_count:
            # Also delete from persistence
            persistence.delete_ten_minute_summary(summary_id)
            return {"message": "10-minute summary deleted", "summary_id": summary_id}
        else:
            raise HTTPException(status_code=404, detail="10-minute summary not found")

@app.delete("/automation/action-registry/{action_id}")
async def delete_action_from_registry(action_id: str):
    """Delete an action from the action registry"""
    if not action_registry:
        raise HTTPException(status_code=500, detail="Action registry not available")
    
    # This would require adding a delete method to ActionRegistry
    # For now, return a not implemented error
    raise HTTPException(status_code=501, detail="Action deletion not yet implemented in ActionRegistry")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=config.backend_port)
