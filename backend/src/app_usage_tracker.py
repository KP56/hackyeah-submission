"""
App Usage Tracker
Efficiently tracks and aggregates application usage statistics
Stores data by hour to minimize storage while providing detailed insights
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import time


class AppUsageTracker:
    """Tracks application usage with efficient hourly aggregation"""
    
    def __init__(self, data_file: str = "data/app_usage.json"):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(exist_ok=True)
        
        self._lock = threading.Lock()
        
        # Current session tracking (in-memory)
        self._current_app = None
        self._current_app_start = None
        
        # Hourly aggregated data structure:
        # {
        #   "2024-10-04_14": {  # date_hour key
        #     "chrome": 1800,  # seconds spent in Chrome during this hour
        #     "vscode": 2400,
        #     ...
        #   }
        # }
        self._hourly_data: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Load existing data
        self._load_from_file()
        
        # Background save thread
        self._save_interval = 60  # Save every minute
        self._running = False
        self._save_thread = None
    
    def start(self):
        """Start the background save thread"""
        if self._running:
            return
        
        self._running = True
        self._save_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_thread.start()
        print("App usage tracker started")
    
    def stop(self):
        """Stop the background save thread"""
        if not self._running:
            return
        
        # Record any ongoing session
        self._end_current_session()
        
        self._running = False
        if self._save_thread:
            self._save_thread.join(timeout=2.0)
        
        # Final save
        self._save_to_file()
        print("App usage tracker stopped")
    
    def record_app_switch(self, app_name: str):
        """Record when user switches to a different app"""
        with self._lock:
            # End current session
            self._end_current_session()
            
            # Start new session
            self._current_app = app_name
            self._current_app_start = time.time()
    
    def _end_current_session(self):
        """End the current app session and record the duration"""
        if self._current_app and self._current_app_start:
            duration = time.time() - self._current_app_start
            
            # Only record if session was longer than 1 second
            if duration >= 1.0:
                # Get the hour key for when this session started
                start_dt = datetime.fromtimestamp(self._current_app_start)
                hour_key = start_dt.strftime("%Y-%m-%d_%H")
                
                # Add to hourly data
                self._hourly_data[hour_key][self._current_app] += duration
            
            self._current_app = None
            self._current_app_start = None
    
    def _save_worker(self):
        """Background worker that periodically saves data"""
        while self._running:
            time.sleep(self._save_interval)
            if self._running:
                self._save_to_file()
    
    def _save_to_file(self):
        """Save hourly data to file"""
        try:
            with self._lock:
                # End current session before saving
                current_app_backup = self._current_app
                current_start_backup = self._current_app_start
                
                self._end_current_session()
                
                # Convert defaultdict to regular dict for JSON serialization
                data_to_save = {
                    "hourly_data": {k: dict(v) for k, v in self._hourly_data.items()},
                    "last_updated": time.time()
                }
                
                # Restore current session
                self._current_app = current_app_backup
                self._current_app_start = current_start_backup
            
            with open(self.data_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            
            print(f"App usage data saved ({len(self._hourly_data)} hours tracked)")
        except Exception as e:
            print(f"Error saving app usage data: {e}")
    
    def _load_from_file(self):
        """Load hourly data from file"""
        try:
            if self.data_file.exists():
                print(f"[APP USAGE] Loading app usage data from: {self.data_file.absolute()}")
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                with self._lock:
                    self._hourly_data.clear()
                    hourly_data = data.get("hourly_data", {})
                    for hour_key, apps in hourly_data.items():
                        self._hourly_data[hour_key] = defaultdict(float, apps)
                
                # Debug: Show sample of loaded data
                sample_keys = list(self._hourly_data.keys())[:5]
                print(f"[APP USAGE] Loaded app usage data ({len(self._hourly_data)} hours tracked)")
                print(f"[APP USAGE] Sample hour keys: {sample_keys}")
                if sample_keys:
                    first_key = sample_keys[0]
                    print(f"[APP USAGE] Sample data for {first_key}: {dict(self._hourly_data[first_key])}")
            else:
                print(f"[APP USAGE] WARNING: App usage data file does not exist: {self.data_file.absolute()}")
        except Exception as e:
            print(f"[APP USAGE] ERROR loading app usage data: {e}")
            import traceback
            traceback.print_exc()
    
    def get_today_usage(self) -> Dict[str, float]:
        """Get app usage for today"""
        with self._lock:
            # End current session to include ongoing time
            current_app_backup = self._current_app
            current_start_backup = self._current_app_start
            self._end_current_session()
            
            today = datetime.now().strftime("%Y-%m-%d")
            print(f"[APP USAGE] get_today_usage: Looking for data with date: {today}")
            usage = defaultdict(float)
            
            matching_hours = []
            for hour_key, apps in self._hourly_data.items():
                if hour_key.startswith(today):
                    matching_hours.append(hour_key)
                    for app, duration in apps.items():
                        usage[app] += duration
            
            print(f"[APP USAGE] get_today_usage: Found {len(matching_hours)} hours for today")
            print(f"[APP USAGE] Matching hour keys: {matching_hours[:5]}")
            print(f"[APP USAGE] Total apps for today: {len(usage)}, Total time: {sum(usage.values()):.1f}s")
            
            # Restore current session
            self._current_app = current_app_backup
            self._current_app_start = current_start_backup
            
            return dict(usage)
    
    def get_week_usage(self) -> Dict[str, Dict[str, float]]:
        """Get app usage for the past 7 days, grouped by day"""
        with self._lock:
            # End current session to include ongoing time
            current_app_backup = self._current_app
            current_start_backup = self._current_app_start
            self._end_current_session()
            
            week_usage = {}
            
            # Get last 7 days
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                day_usage = defaultdict(float)
                
                for hour_key, apps in self._hourly_data.items():
                    if hour_key.startswith(date):
                        for app, duration in apps.items():
                            day_usage[app] += duration
                
                if day_usage:  # Only include days with data
                    week_usage[date] = dict(day_usage)
            
            # Restore current session
            self._current_app = current_app_backup
            self._current_app_start = current_start_backup
            
            return week_usage
    
    def get_hourly_usage(self, date: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """Get hourly breakdown for a specific date (defaults to today)"""
        with self._lock:
            # End current session to include ongoing time
            current_app_backup = self._current_app
            current_start_backup = self._current_app_start
            self._end_current_session()
            
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            hourly_usage = {}
            
            for hour in range(24):
                hour_key = f"{date}_{hour:02d}"
                if hour_key in self._hourly_data:
                    hourly_usage[f"{hour:02d}:00"] = dict(self._hourly_data[hour_key])
            
            # Restore current session
            self._current_app = current_app_backup
            self._current_app_start = current_start_backup
            
            return hourly_usage
    
    def get_current_app(self) -> Optional[str]:
        """Get the currently active application"""
        with self._lock:
            return self._current_app
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        with self._lock:
            # End current session to include ongoing time
            current_app_backup = self._current_app
            current_start_backup = self._current_app_start
            self._end_current_session()
            
            # Calculate today usage directly (avoid calling get_today_usage which would deadlock)
            today = datetime.now().strftime("%Y-%m-%d")
            today_usage = defaultdict(float)
            
            for hour_key, apps in self._hourly_data.items():
                if hour_key.startswith(today):
                    for app, duration in apps.items():
                        today_usage[app] += duration
            
            # Calculate total time today
            total_today = sum(today_usage.values())
            
            # Find most used app today
            most_used_today = None
            most_used_duration = 0
            if today_usage:
                most_used_today = max(today_usage, key=today_usage.get)
                most_used_duration = today_usage[most_used_today]
            
            # Get unique apps count
            unique_apps = set()
            for apps in self._hourly_data.values():
                unique_apps.update(apps.keys())
            
            # Restore current session
            self._current_app = current_app_backup
            self._current_app_start = current_start_backup
            
            return {
                "total_time_today_seconds": total_today,
                "most_used_app_today": most_used_today,
                "most_used_app_duration_seconds": most_used_duration,
                "unique_apps_tracked": len(unique_apps),
                "current_app": self._current_app
            }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove data older than specified days to prevent file from growing too large"""
        with self._lock:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
            
            keys_to_remove = []
            for hour_key in self._hourly_data.keys():
                if hour_key < cutoff_date:
                    keys_to_remove.append(hour_key)
            
            for key in keys_to_remove:
                del self._hourly_data[key]
            
            if keys_to_remove:
                print(f"Cleaned up {len(keys_to_remove)} old hour entries")
                self._save_to_file()


# Global instance
app_usage_tracker = AppUsageTracker()

