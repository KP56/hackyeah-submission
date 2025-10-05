"""
Central Action Registry
Stores all user actions for pattern detection and analysis
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from collections import deque
import threading
import time
import json
from pathlib import Path
import os

# Third-party libraries for encryption and secure key storage
import keyring
from cryptography.fernet import Fernet, InvalidToken

# --- Configuration ---
# Default service name for storing the key in the keyring.
# This should be unique to your application.
KEYRING_SERVICE_NAME = "flowmo-progressbot-encrypted-storage"
# Default username associated with the key in the keyring.
KEYRING_USERNAME = "action-registry"
# Default file path to store the encrypted data.
ENCRYPTED_DATA_FILE = Path.home() / "./flowmo-progressbot" / "action_registry.dat"


@dataclass
class UserAction:
    """Represents a single user action"""
    action_id: str
    action_type: str  # file_operation, email_action, etc.
    timestamp: float
    details: Dict[str, Any]
    source: str  # which component detected this
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "timestamp": self.timestamp,
            "details": self.details,
            "source": self.source,
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserAction:
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            timestamp=data["timestamp"],
            details=data["details"],
            source=data["source"],
            metadata=data.get("metadata")
        )
    

# --- Secure Storage Class ---

class SecureStorage:
    """
    Handles the encryption, decryption, saving, and loading of data.
    """
    def __init__(self, service_name: str, username: str, filepath: str):
        """
        Initializes the SecureStorage service.

        Args:
            service_name: The service name for the keyring.
            username: The username for the keyring.
            filepath: The path to the file where encrypted data is stored.
        """
        self.service_name = service_name
        self.username = username
        self.filepath = filepath
        self._cipher_suite = self._get_cipher_suite()

    def _get_or_create_key(self) -> bytes:
        """
        Retrieves the encryption key from the system's keyring.
        If the key does not exist, it generates a new one and stores it.
        """
        stored_key = keyring.get_password(self.service_name, self.username)

        if stored_key:
            return stored_key.encode('utf-8')
        else:
            print("No encryption key found. Generating a new one and storing it in the keyring.")
            new_key = Fernet.generate_key()
            keyring.set_password(self.service_name, self.username, new_key.decode('utf-8'))
            return new_key

    def _get_cipher_suite(self) -> Fernet:
        """
        Initializes the cryptographic cipher suite with the encryption key.
        """
        key = self._get_or_create_key()
        return Fernet(key)

    def save(self, data: List[Dict[str, Any]]):
        """
        Encrypts and saves a list of dictionaries to the file.

        Args:
            actions_data: A list of dictionaries representing the data to save.
        """
        try:
            # 1. Serialize the list of dictionaries to a JSON string.
            json_string = json.dumps(data, indent=2) # indent is optional, but nice for debugging
            
            # 2. Encode the JSON string to bytes for encryption.
            json_bytes = json_string.encode('utf-8')

            # 3. Encrypt the bytes.
            encrypted_data = self._cipher_suite.encrypt(json_bytes)
            
            # 4. Write the encrypted data to the file.
            with open(self.filepath, "wb") as f:
                f.write(encrypted_data)
            
            print(f"Successfully saved {len(data)} actions to {self.filepath}")

        except TypeError as e:
            print(f"Error: Could not serialize the data to JSON. Ensure all items are JSON-serializable. Details: {e}")
            raise
        except Exception as e:
            print(f"Error: An unexpected error occurred while saving data: {e}")
            raise

    def load(self) -> Optional[List[Dict[str, Any]]]:
        """
        Loads, decrypts, and returns data from the file as a list of dictionaries.

        Returns:
            A list of dictionaries if successful, otherwise None.
        """
        if not os.path.exists(self.filepath):
            print(f"Info: Data file not found at '{self.filepath}'.")
            return None
        
        try:
            # 1. Read the encrypted bytes from the file.
            with open(self.filepath, "rb") as f:
                encrypted_data = f.read()

            # 2. Decrypt the data.
            decrypted_bytes = self._cipher_suite.decrypt(encrypted_data)

            # 3. Decode bytes back to a JSON string.
            json_string = decrypted_bytes.decode('utf-8')

            # 4. Parse the JSON string into a Python list of dictionaries.
            data = json.loads(json_string)
            
            print(f"Successfully loaded {len(data)} actions from {self.filepath}")
            return data

        except InvalidToken: # from cryptography.fernet
            print("Error: Failed to decrypt data. The key may be incorrect or the data corrupted.")
            return None
        except json.JSONDecodeError:
            print("Error: Failed to parse JSON. The decrypted data is not valid JSON.")
            return None
        except Exception as e:
            print(f"Error: An unexpected error occurred while loading data: {e}")
            return None


class ActionRegistry:
    """Central registry for all user actions"""
    
    def __init__(self, capacity: int = 100000, persistence_file: Optional[str] = None):
        self.capacity = capacity
        self._actions: deque[UserAction] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self._persistence_file = Path(persistence_file) if persistence_file else None
        self._action_counter = 0
        self._secure_storage = SecureStorage(KEYRING_SERVICE_NAME, KEYRING_USERNAME, persistence_file if persistence_file else ENCRYPTED_DATA_FILE)
        
        # Load persisted actions if available
        # if self._persistence_file and self._persistence_file.exists():
        self._load_from_file()
    
    def register_action(self, action_type: str, details: Dict[str, Any], source: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Register a new user action"""
        print("registering new action")
        with self._lock:
            self._action_counter += 1
            action_id = f"action_{int(time.time())}_{self._action_counter}"
            
            action = UserAction(
                action_id=action_id,
                action_type=action_type,
                timestamp=time.time(),
                details=details,
                source=source,
                metadata=metadata
            )
            
            self._actions.append(action)
            return action_id
    
    def get_actions(self, since: Optional[float] = None, action_type: Optional[str] = None, limit: Optional[int] = None) -> List[UserAction]:
        """Get actions with optional filtering"""
        with self._lock:
            actions = list(self._actions)
        
        # Filter by timestamp
        if since is not None:
            actions = [a for a in actions if a.timestamp >= since]
        
        # Filter by type
        if action_type is not None:
            actions = [a for a in actions if a.action_type == action_type]
        
        # Apply limit
        if limit is not None:
            actions = actions[-limit:]
        
        return actions
    
    def get_recent_actions(self, seconds: int = 20) -> List[UserAction]:
        """Get actions from the last N seconds"""
        cutoff_time = time.time() - seconds
        return self.get_actions(since=cutoff_time)
    
    def get_action_by_id(self, action_id: str) -> Optional[UserAction]:
        """Get a specific action by ID"""
        with self._lock:
            for action in self._actions:
                if action.action_id == action_id:
                    return action
        return None
    
    def get_all_actions(self) -> List[UserAction]:
        """Get all stored actions"""
        with self._lock:
            return list(self._actions)
    
    def clear_old_actions(self, older_than_seconds: int = 3600):
        """Clear actions older than specified seconds"""
        cutoff_time = time.time() - older_than_seconds
        with self._lock:
            self._actions = deque(
                (a for a in self._actions if a.timestamp >= cutoff_time),
                maxlen=self.capacity
            )
    
    def get_action_stats(self) -> Dict[str, Any]:
        """Get statistics about stored actions"""
        with self._lock:
            actions = list(self._actions)
        
        if not actions:
            return {
                "total_actions": 0,
                "action_types": {},
                "sources": {},
                "time_range": None
            }
        
        action_types = {}
        sources = {}
        
        for action in actions:
            action_types[action.action_type] = action_types.get(action.action_type, 0) + 1
            sources[action.source] = sources.get(action.source, 0) + 1
        
        return {
            "total_actions": len(actions),
            "action_types": action_types,
            "sources": sources,
            "time_range": {
                "oldest": min(a.timestamp for a in actions),
                "newest": max(a.timestamp for a in actions)
            }
        }
    
    def save_to_file(self):
        """Save actions to persistence file"""
        if not self._persistence_file:
            return
        
        with self._lock:
            actions_data = [action.to_dict() for action in self._actions]
        
        try:
            # self._persistence_file.parent.mkdir(parents=True, exist_ok=True)
            # with open(self._persistence_file, 'w') as f:
            #     json.dump({
            #         "actions": actions_data,
            #         "action_counter": self._action_counter
            #     }, f, indent=2)
            self._secure_storage.save(actions_data)

        except Exception as e:
            print(f"Failed to save actions to file: {e}")
    
    def _load_from_file(self):
        """Load actions from persistence file"""
        try:
            # with open(self._persistence_file, 'r') as f:
            #     data = json.load(f)
            data = self._secure_storage.load()
            
            with self._lock:
                self._actions.clear()
                for action_data in data.get("actions", []):
                    self._actions.append(UserAction.from_dict(action_data))
                self._action_counter = data.get("action_counter", 0)
            
            print(f"Loaded {len(self._actions)} actions from persistence file")
        except Exception as e:
            print(f"Failed to load actions from file: {e}")
