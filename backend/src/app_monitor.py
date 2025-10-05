"""
Application Switching Monitor
Tracks when the user switches between applications
"""

import threading
import time
from typing import Optional, Callable
import sys

# Windows-specific imports
if sys.platform == 'win32':
    import win32gui
    import win32process
    import psutil


class AppSwitchMonitor:
    """Monitors application switching on Windows"""
    
    def __init__(self, on_app_switch: Optional[Callable[[str, str], None]] = None, poll_interval: float = 1.0):
        """
        Args:
            on_app_switch: Callback function(app_name, window_title) called when app switches
            poll_interval: How often to check for app changes (in seconds)
        """
        self.on_app_switch = on_app_switch
        self.poll_interval = poll_interval
        self._running = False
        self._thread = None
        self._last_app = None
        self._last_window_title = None
    
    def _get_active_window_info(self):
        """Get the currently active window's application name and title"""
        if sys.platform != 'win32':
            return None, None
        
        try:
            # Get foreground window handle
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None, None
            
            # Get window title
            window_title = win32gui.GetWindowText(hwnd)
            
            # Get process ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            # Get process name
            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "Unknown"
            
            return app_name, window_title
        except Exception as e:
            print(f"Error getting active window info: {e}")
            return None, None
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                app_name, window_title = self._get_active_window_info()
                
                if app_name and app_name != self._last_app:
                    # App switched
                    if self._last_app is not None:  # Skip first detection
                        if self.on_app_switch:
                            self.on_app_switch(app_name, window_title)
                    
                    self._last_app = app_name
                    self._last_window_title = window_title
                elif app_name and window_title != self._last_window_title:
                    # Same app but different window/document
                    if self._last_window_title is not None:
                        if self.on_app_switch:
                            self.on_app_switch(app_name, window_title)
                    self._last_window_title = window_title
                
            except Exception as e:
                print(f"Error in app monitor loop: {e}")
            
            time.sleep(self.poll_interval)
    
    def start(self):
        """Start monitoring"""
        if self._running:
            return
        
        if sys.platform != 'win32':
            print("App switching monitor only works on Windows")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("App switching monitor started")
    
    def stop(self):
        """Stop monitoring"""
        if not self._running:
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("App switching monitor stopped")
    
    def is_running(self):
        """Check if monitor is running"""
        return self._running


# Test code
if __name__ == "__main__":
    def on_switch(app_name, window_title):
        print(f"[APP SWITCH] {app_name}: {window_title}")
    
    monitor = AppSwitchMonitor(on_app_switch=on_switch, poll_interval=0.5)
    monitor.start()
    
    try:
        print("Monitoring app switches... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        monitor.stop()

