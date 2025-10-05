"""
Persistence module for saving and loading application data across restarts.
Handles file operations, AI interactions, and automation histories.
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class DataPersistence:
    """Handles persistence of application data to JSON files."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths for different data types
        self.file_ops_path = self.data_dir / "file_operations.json"
        self.ai_interactions_path = self.data_dir / "ai_interactions.json"
        self.automation_history_path = self.data_dir / "automation_history.json"
        self.execution_history_path = self.data_dir / "execution_history.json"
        self.minute_summaries_path = self.data_dir / "minute_summaries.json"
        self.ten_minute_summaries_path = self.data_dir / "ten_minute_summaries.json"
        self.time_saved_path = self.data_dir / "time_saved.json"
    
    def save_file_operations(self, operations: List[Dict[str, Any]]) -> None:
        """Save file operations to disk."""
        try:
            with open(self.file_ops_path, 'w', encoding='utf-8') as f:
                json.dump(operations, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(operations)} file operations to {self.file_ops_path}")
        except Exception as e:
            print(f"Error saving file operations: {e}")
    
    def load_file_operations(self) -> List[Dict[str, Any]]:
        """Load file operations from disk."""
        try:
            if self.file_ops_path.exists():
                with open(self.file_ops_path, 'r', encoding='utf-8') as f:
                    operations = json.load(f)
                print(f"Loaded {len(operations)} file operations from {self.file_ops_path}")
                return operations
        except Exception as e:
            print(f"Error loading file operations: {e}")
        return []
    
    def save_ai_interactions(self, interactions: List[Dict[str, Any]]) -> None:
        """Save AI interactions to disk using atomic write."""
        try:
            # Write to temporary file first, then rename (atomic operation)
            temp_path = self.ai_interactions_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(interactions, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(self.ai_interactions_path)
            print(f"Saved {len(interactions)} AI interactions to {self.ai_interactions_path}")
        except Exception as e:
            print(f"Error saving AI interactions: {e}")
            # Clean up temp file if it exists
            temp_path = self.ai_interactions_path.with_suffix('.tmp')
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
    
    def load_ai_interactions(self) -> List[Dict[str, Any]]:
        """Load AI interactions from disk with retry mechanism."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.ai_interactions_path.exists():
                    # Check if file is empty or too small
                    if self.ai_interactions_path.stat().st_size == 0:
                        print("AI interactions file is empty, returning empty list")
                        return []
                    
                    with open(self.ai_interactions_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            print("AI interactions file is empty, returning empty list")
                            return []
                        
                        interactions = json.loads(content)
                    print(f"Loaded {len(interactions)} AI interactions from {self.ai_interactions_path}")
                    return interactions
                else:
                    print("AI interactions file does not exist, returning empty list")
                    return []
            except json.JSONDecodeError as e:
                print(f"JSON decode error loading AI interactions (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"File size: {self.ai_interactions_path.stat().st_size if self.ai_interactions_path.exists() else 'N/A'}")
                
                if attempt == max_retries - 1:  # Last attempt
                    # Try to backup the corrupted file
                    try:
                        backup_path = self.ai_interactions_path.with_suffix('.json.backup')
                        import shutil
                        shutil.copy2(self.ai_interactions_path, backup_path)
                        print(f"Backed up corrupted file to {backup_path}")
                    except Exception as backup_e:
                        print(f"Failed to backup corrupted file: {backup_e}")
                else:
                    # Wait before retry
                    time.sleep(0.1)
            except Exception as e:
                print(f"Error loading AI interactions (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.1)
        return []
    
    def save_automation_history(self, history: List[Dict[str, Any]]) -> None:
        """Save automation history to disk."""
        try:
            with open(self.automation_history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(history)} automation history entries to {self.automation_history_path}")
        except Exception as e:
            print(f"Error saving automation history: {e}")
    
    def load_automation_history(self) -> List[Dict[str, Any]]:
        """Load automation history from disk."""
        try:
            if self.automation_history_path.exists():
                with open(self.automation_history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                print(f"Loaded {len(history)} automation history entries from {self.automation_history_path}")
                return history
        except Exception as e:
            print(f"Error loading automation history: {e}")
        return []
    
    def save_execution_history(self, history: List[Dict[str, Any]]) -> None:
        """Save script execution history to disk."""
        try:
            with open(self.execution_history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(history)} execution history entries to {self.execution_history_path}")
        except Exception as e:
            print(f"Error saving execution history: {e}")
    
    def load_execution_history(self) -> List[Dict[str, Any]]:
        """Load script execution history from disk."""
        try:
            if self.execution_history_path.exists():
                with open(self.execution_history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                print(f"Loaded {len(history)} execution history entries from {self.execution_history_path}")
                return history
        except Exception as e:
            print(f"Error loading execution history: {e}")
        return []
    
    def append_ai_interaction(self, interaction: Dict[str, Any]) -> None:
        """Append a single AI interaction to the file."""
        try:
            interactions = self.load_ai_interactions()
            interactions.append(interaction)
            # Keep only the last 1000 interactions to prevent file from growing too large
            if len(interactions) > 1000:
                interactions = interactions[-1000:]
            self.save_ai_interactions(interactions)
        except Exception as e:
            print(f"Error appending AI interaction: {e}")
    
    def append_file_operation(self, operation: Dict[str, Any]) -> None:
        """Append a single file operation to the file."""
        try:
            operations = self.load_file_operations()
            operations.append(operation)
            # Keep only the last 5000 operations to prevent file from growing too large
            if len(operations) > 5000:
                operations = operations[-5000:]
            self.save_file_operations(operations)
        except Exception as e:
            print(f"Error appending file operation: {e}")
    
    def append_execution_history(self, execution: Dict[str, Any]) -> None:
        """Append a single execution to the file."""
        try:
            history = self.load_execution_history()
            history.append(execution)
            # Keep only the last 500 executions to prevent file from growing too large
            if len(history) > 500:
                history = history[-500:]
            self.save_execution_history(history)
        except Exception as e:
            print(f"Error appending execution history: {e}")
    
    def save_minute_summaries(self, summaries: List[Dict[str, Any]]) -> None:
        """Save 1-minute summaries to disk."""
        try:
            with open(self.minute_summaries_path, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(summaries)} minute summaries to {self.minute_summaries_path}")
        except Exception as e:
            print(f"Error saving minute summaries: {e}")
    
    def load_minute_summaries(self) -> List[Dict[str, Any]]:
        """Load 1-minute summaries from disk."""
        try:
            if self.minute_summaries_path.exists():
                with open(self.minute_summaries_path, 'r', encoding='utf-8') as f:
                    summaries = json.load(f)
                print(f"Loaded {len(summaries)} minute summaries from {self.minute_summaries_path}")
                return summaries
        except Exception as e:
            print(f"Error loading minute summaries: {e}")
        return []
    
    def append_minute_summary(self, summary: Dict[str, Any]) -> None:
        """Append a single minute summary to the file."""
        try:
            summaries = self.load_minute_summaries()
            summaries.append(summary)
            # Keep only the last 1000 summaries (about 16 hours)
            if len(summaries) > 1000:
                summaries = summaries[-1000:]
            self.save_minute_summaries(summaries)
        except Exception as e:
            print(f"Error appending minute summary: {e}")
    
    def delete_minute_summary(self, summary_id: str) -> bool:
        """Delete a minute summary by ID."""
        try:
            summaries = self.load_minute_summaries()
            original_count = len(summaries)
            summaries = [s for s in summaries if s.get("id") != summary_id]
            if len(summaries) < original_count:
                self.save_minute_summaries(summaries)
                return True
            return False
        except Exception as e:
            print(f"Error deleting minute summary: {e}")
            return False
    
    def save_ten_minute_summaries(self, summaries: List[Dict[str, Any]]) -> None:
        """Save 10-minute summaries to disk."""
        try:
            with open(self.ten_minute_summaries_path, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(summaries)} 10-minute summaries to {self.ten_minute_summaries_path}")
        except Exception as e:
            print(f"Error saving 10-minute summaries: {e}")
    
    def load_ten_minute_summaries(self) -> List[Dict[str, Any]]:
        """Load 10-minute summaries from disk."""
        try:
            if self.ten_minute_summaries_path.exists():
                with open(self.ten_minute_summaries_path, 'r', encoding='utf-8') as f:
                    summaries = json.load(f)
                print(f"Loaded {len(summaries)} 10-minute summaries from {self.ten_minute_summaries_path}")
                return summaries
        except Exception as e:
            print(f"Error loading 10-minute summaries: {e}")
        return []
    
    def append_ten_minute_summary(self, summary: Dict[str, Any]) -> None:
        """Append a single 10-minute summary to the file."""
        try:
            summaries = self.load_ten_minute_summaries()
            summaries.append(summary)
            # Keep only the last 500 summaries (about 3 days)
            if len(summaries) > 500:
                summaries = summaries[-500:]
            self.save_ten_minute_summaries(summaries)
        except Exception as e:
            print(f"Error appending 10-minute summary: {e}")
    
    def delete_ten_minute_summary(self, summary_id: str) -> bool:
        """Delete a 10-minute summary by ID."""
        try:
            summaries = self.load_ten_minute_summaries()
            original_count = len(summaries)
            summaries = [s for s in summaries if s.get("id") != summary_id]
            if len(summaries) < original_count:
                self.save_ten_minute_summaries(summaries)
                return True
            return False
        except Exception as e:
            print(f"Error deleting 10-minute summary: {e}")
            return False

    def save_time_saved_data(self, time_saved_data: Dict[str, Any]) -> None:
        """Save time saved data to disk."""
        try:
            with open(self.time_saved_path, 'w', encoding='utf-8') as f:
                json.dump(time_saved_data, f, indent=2, ensure_ascii=False)
            print(f"Saved time saved data to {self.time_saved_path}")
        except Exception as e:
            print(f"Error saving time saved data: {e}")

    def load_time_saved_data(self) -> Dict[str, Any]:
        """Load time saved data from disk."""
        try:
            if self.time_saved_path.exists():
                with open(self.time_saved_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"Loaded time saved data from {self.time_saved_path}")
                return data
            else:
                print("Time saved data file does not exist, returning default")
                return {
                    "total_time_saved_seconds": 0,
                    "daily_breakdown": [],
                    "automation_executions": []
                }
        except Exception as e:
            print(f"Error loading time saved data: {e}")
            return {
                "total_time_saved_seconds": 0,
                "daily_breakdown": [],
                "automation_executions": []
            }

    def add_automation_time_saved(self, suggestion_id: str, time_saved_seconds: float, timestamp: float = None) -> None:
        """Add a new automation time saved entry."""
        try:
            if timestamp is None:
                timestamp = time.time()
            
            data = self.load_time_saved_data()
            
            # Add new automation execution
            automation_entry = {
                "suggestion_id": suggestion_id,
                "time_saved_seconds": time_saved_seconds,
                "timestamp": timestamp
            }
            
            if "automation_executions" not in data:
                data["automation_executions"] = []
            
            data["automation_executions"].append(automation_entry)
            
            # Update total
            data["total_time_saved_seconds"] = data.get("total_time_saved_seconds", 0) + time_saved_seconds
            
            # Save updated data
            self.save_time_saved_data(data)
            
        except Exception as e:
            print(f"Error adding automation time saved: {e}")


# Global persistence instance
persistence = DataPersistence()
