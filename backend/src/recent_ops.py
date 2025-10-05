from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Callable, Optional
import threading
import time
import os
import platform

# Import watchdog components with Windows compatibility
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# Windows-specific imports
if platform.system() == "Windows":
    try:
        from watchdog.observers.polling import PollingObserver
        POLLING_AVAILABLE = True
    except ImportError:
        POLLING_AVAILABLE = False
else:
    POLLING_AVAILABLE = False


@dataclass
class FileOp:
    event_type: str  # created, modified, moved, deleted
    src_path: str
    dest_path: str | None
    timestamp: float
    file_size: int | None = None
    file_extension: str | None = None
    operation_category: str | None = None  # file_management, content_edit, system, etc.


class _Handler(FileSystemEventHandler):
    def __init__(self, queue: Deque[FileOp], verbose: bool = False, on_action: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.queue = queue
        self.verbose = verbose
        self.on_action = on_action

    def _push(self, text: str, op: FileOp):
        self.queue.append(op)
        if self.verbose:
            print(text)
        if self.on_action:
            self.on_action(text)

    def _get_file_details(self, path: str) -> tuple[int | None, str | None, str]:
        """Get file size, extension, and operation category"""
        try:
            if os.path.exists(path):
                file_size = os.path.getsize(path) if os.path.isfile(path) else None
                file_extension = os.path.splitext(path)[1].lower() if os.path.isfile(path) else None
            else:
                file_size = None
                file_extension = os.path.splitext(path)[1].lower()
            
            # Categorize operation based on file type and path
            if any(ext in path.lower() for ext in ['.pyc', '.pyo', '__pycache__', '.pack', '.idx']):
                category = "system"
            elif any(ext in path.lower() for ext in ['.tmp', '.temp', '.cache', '.log']):
                category = "system"
            elif file_extension in ['.py', '.js', '.ts', '.html', '.css', '.json', '.yaml', '.md']:
                category = "content_edit"
            else:
                category = "file_management"
            
            return file_size, file_extension, category
        except:
            return None, None, "unknown"

    def on_created(self, event):
        file_size, file_extension, category = self._get_file_details(event.src_path)
        # Override category for created files to be "file_creation"
        op = FileOp("created", event.src_path, None, time.time(), file_size, file_extension, "file_creation")
        self._push(f"[watch] created: {event.src_path}", op)

    def on_modified(self, event):
        file_size, file_extension, category = self._get_file_details(event.src_path)
        # Override category for modified files to be "file_edit"
        op = FileOp("modified", event.src_path, None, time.time(), file_size, file_extension, "file_edit")
        self._push(f"[watch] modified: {event.src_path}", op)

    def on_deleted(self, event):
        file_size, file_extension, category = self._get_file_details(event.src_path)
        # Override category for deleted files to be "removal"
        op = FileOp("deleted", event.src_path, None, time.time(), file_size, file_extension, "removal")
        self._push(f"[watch] deleted: {event.src_path}", op)

    def on_moved(self, event):
        file_size, file_extension, category = self._get_file_details(event.src_path)
        dest_path = getattr(event, "dest_path", None)
        # Override category for moved files to be "move"
        op = FileOp("moved", event.src_path, dest_path, time.time(), file_size, file_extension, "move")
        self._push(f"[watch] moved: {event.src_path} -> {dest_path}", op)




class RecentFileOperations:
    def __init__(self, directories: List[str], capacity: int = 100, verbose: bool = False, on_action: Optional[Callable[[str], None]] = None, error_logger=None):
        self.capacity = capacity
        self._ops: Deque[FileOp] = deque(maxlen=capacity)
        self._directories = list(directories)
        self._error_logger = error_logger
        self._valid_directories = []
        self._observer = None
        self._handler = None
        self._lock = threading.Lock()
        
        # Validate directories first
        for d in self._directories:
            try:
                if not os.path.exists(d):
                    error_msg = f"Directory does not exist: {d}"
                    if verbose:
                        print(f"[recent_ops] {error_msg}")
                    if self._error_logger:
                        self._error_logger.log_warning(error_msg, "file_watcher", f"Path: {d}")
                    continue
                if not os.path.isdir(d):
                    error_msg = f"Path is not a directory: {d}"
                    if verbose:
                        print(f"[recent_ops] {error_msg}")
                    if self._error_logger:
                        self._error_logger.log_warning(error_msg, "file_watcher", f"Path: {d}")
                    continue
                
                self._valid_directories.append(d)
                if verbose:
                    print(f"[recent_ops] Successfully scheduled directory: {d}")
            except Exception as e:
                error_msg = f"Failed to validate directory: {d}"
                if verbose:
                    print(f"[recent_ops] {error_msg}: {e}")
                if self._error_logger:
                    self._error_logger.log_error(error_msg, "file_watcher", f"Path: {d}, Error: {str(e)}")
                continue
        
        if not self._valid_directories and verbose:
            print("[recent_ops] Warning: No valid directories to watch")
        
        # Initialize observer and handler based on availability
        print(f"[DEBUG] Initializing observer for {len(self._valid_directories)} directories")
        self._init_observer(verbose)
        print(f"[DEBUG] Observer initialized: {self._observer is not None}")

    def _init_observer(self, verbose: bool = False):
        """Initialize the appropriate observer based on platform and availability."""
        if not self._valid_directories:
            return
            
        # Try different observer types in order of preference
        observers_to_try = []
        
        # On Windows, prefer polling observer to avoid threading issues
        if platform.system() == "Windows" and POLLING_AVAILABLE:
            observers_to_try.append(("PollingObserver", PollingObserver))
        
        # Try regular observer if available
        if WATCHDOG_AVAILABLE:
            observers_to_try.append(("Observer", Observer))
        
        # Fallback to polling if available
        if POLLING_AVAILABLE and ("PollingObserver", PollingObserver) not in observers_to_try:
            observers_to_try.append(("PollingObserver", PollingObserver))
        
        for observer_name, observer_class in observers_to_try:
            try:
                if observer_name == "PollingObserver":
                    # Use a shorter polling interval for better responsiveness
                    self._observer = observer_class(timeout=1)
                else:
                    self._observer = observer_class()
                
                # Create handler
                self._handler = _Handler(self._ops, verbose=verbose, on_action=None)
                
                # Schedule directories
                for d in self._valid_directories:
                    try:
                        self._observer.schedule(self._handler, path=d, recursive=True)
                    except Exception as e:
                        if verbose:
                            print(f"[recent_ops] Failed to schedule directory '{d}' on {observer_name}: {e}")
                        if self._error_logger:
                            self._error_logger.log_warning(f"Failed to schedule directory: {d}", "file_watcher", f"Observer: {observer_name}, Error: {str(e)}")
                        continue
                
                if verbose:
                    print(f"[recent_ops] Successfully initialized {observer_name} for {len(self._valid_directories)} directories")
                return
                
            except Exception as e:
                if verbose:
                    print(f"[recent_ops] Failed to initialize {observer_name}: {e}")
                if self._error_logger:
                    self._error_logger.log_error(f"Failed to initialize {observer_name}", "file_watcher", f"Error: {str(e)}")
                continue
        
        # If we get here, no observer worked
        if verbose:
            print("[recent_ops] Warning: No file watcher available, file monitoring disabled")
        if self._error_logger:
            self._error_logger.log_error("No file watcher available", "file_watcher", "All observer types failed to initialize")

    def start(self):
        print(f"[DEBUG] Starting file watcher - valid_dirs: {len(self._valid_directories)}, observer: {self._observer is not None}")
        if not self._valid_directories or not self._observer:
            print("[recent_ops] No valid directories to watch or observer not available, skipping file watcher startup")
            return
            
        try:
            print("[DEBUG] Calling observer.start()...")
            self._observer.start()
            print(f"[recent_ops] File watcher started successfully for {len(self._valid_directories)} directories")
        except Exception as e:
            print(f"[recent_ops] Failed to start file watcher: {e}")
            if self._error_logger:
                self._error_logger.log_error("Failed to start file watcher", "file_watcher", f"Error: {str(e)}")

    def stop(self):
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=2)
                if self._handler and self._handler.verbose:
                    print("[recent_ops] File watcher stopped successfully")
            except Exception as e:
                if self._handler and self._handler.verbose:
                    print(f"[recent_ops] Error stopping file watcher: {e}")
                if self._error_logger:
                    self._error_logger.log_warning("Error stopping file watcher", "file_watcher", f"Error: {str(e)}")

    def snapshot(self) -> List[FileOp]:
        with self._lock:
            return list(self._ops)
    
    def get_operations_by_category(self, category: str = None) -> List[FileOp]:
        """Get operations filtered by category"""
        with self._lock:
            if category:
                return [op for op in self._ops if op.operation_category == category]
            return list(self._ops)
    
    def get_operations_with_details(self) -> List[dict]:
        """Get operations with enhanced details for display"""
        with self._lock:
            result = []
            for op in self._ops:
                result.append({
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
            return result
