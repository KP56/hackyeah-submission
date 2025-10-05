"""
Keyboard Monitor
Tracks the last N keys pressed by the user to detect patterns like Ctrl+C, Ctrl+V, etc.
"""

import threading
from collections import deque
from typing import Optional, Callable, List
from pynput import keyboard


class KeyboardMonitor:
    """Monitors keyboard input to track recent key presses"""
    
    def __init__(self, buffer_size: int = 30, on_key_sequence: Optional[Callable[[List[str]], None]] = None):
        """
        Args:
            buffer_size: Number of recent keys to keep (default 30)
            on_key_sequence: Callback function(keys_list) called when buffer updates
        """
        self.buffer_size = buffer_size
        self.on_key_sequence = on_key_sequence
        self._key_buffer = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
        self._listener = None
        self._running = False
        
        # Track modifier keys state
        self._modifiers = {
            'ctrl': False,
            'alt': False,
            'shift': False,
            'win': False
        }
    
    def _format_key(self, key) -> str:
        """Format a key into a readable string"""
        try:
            # Handle special keys
            if isinstance(key, keyboard.Key):
                key_name = key.name
                
                # Map special keys to readable names
                key_map = {
                    'ctrl_l': 'Ctrl',
                    'ctrl_r': 'Ctrl',
                    'alt_l': 'Alt',
                    'alt_r': 'Alt',
                    'shift_l': 'Shift',
                    'shift_r': 'Shift',
                    'cmd': 'Win',
                    'cmd_l': 'Win',
                    'cmd_r': 'Win',
                    'space': 'Space',
                    'enter': 'Enter',
                    'tab': 'Tab',
                    'backspace': 'Backspace',
                    'delete': 'Delete',
                    'esc': 'Esc',
                    'up': 'UP',
                    'down': 'DOWN',
                    'left': 'LEFT',
                    'right': 'RIGHT',
                    'home': 'Home',
                    'end': 'End',
                    'page_up': 'PgUp',
                    'page_down': 'PgDn',
                    'caps_lock': 'CapsLock'
                }
                
                return key_map.get(key_name, key_name.capitalize())
            
            # Handle character keys
            elif hasattr(key, 'char') and key.char:
                return key.char
            
            else:
                return str(key)
        except:
            return 'Unknown'
    
    def _on_press(self, key):
        """Handle key press event"""
        try:
            key_str = self._format_key(key)
            
            # Update modifier state
            if key_str in ['Ctrl', 'Alt', 'Shift', 'Win']:
                self._modifiers[key_str.lower()] = True
            
            # Build key representation with modifiers
            if self._modifiers['ctrl'] or self._modifiers['alt'] or self._modifiers['shift'] or self._modifiers['win']:
                # For modifier combinations
                combo = []
                if self._modifiers['ctrl']:
                    combo.append('Ctrl')
                if self._modifiers['alt']:
                    combo.append('Alt')
                if self._modifiers['shift']:
                    combo.append('Shift')
                if self._modifiers['win']:
                    combo.append('Win')
                
                # Add the actual key if it's not a modifier itself
                if key_str not in ['Ctrl', 'Alt', 'Shift', 'Win']:
                    combo.append(key_str)
                    key_str = '+'.join(combo)
            
            with self._lock:
                self._key_buffer.append(key_str)
                
                # Call callback if provided
                if self.on_key_sequence:
                    self.on_key_sequence(list(self._key_buffer))
        
        except Exception as e:
            print(f"Error in keyboard monitor: {e}")
    
    def _on_release(self, key):
        """Handle key release event"""
        try:
            key_str = self._format_key(key)
            
            # Update modifier state
            if key_str in ['Ctrl', 'Alt', 'Shift', 'Win']:
                self._modifiers[key_str.lower()] = False
        
        except Exception as e:
            pass
    
    def start(self):
        """Start monitoring keyboard"""
        if self._running:
            return
        
        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()
        print("Keyboard monitor started")
    
    def stop(self):
        """Stop monitoring keyboard"""
        if not self._running:
            return
        
        self._running = False
        if self._listener:
            self._listener.stop()
        print("Keyboard monitor stopped")
    
    def is_running(self):
        """Check if monitor is running"""
        return self._running
    
    def get_recent_keys(self) -> List[str]:
        """Get the recent key presses"""
        with self._lock:
            return list(self._key_buffer)
    
    def clear_buffer(self):
        """Clear the key buffer"""
        with self._lock:
            self._key_buffer.clear()
    
    def get_key_sequence_string(self) -> str:
        """Get recent keys as a readable string"""
        with self._lock:
            return ' '.join(self._key_buffer)


# Test code
if __name__ == "__main__":
    import time
    
    def on_sequence(keys):
        print(f"Recent keys: {' '.join(keys[-10:])}")  # Print last 10 keys
    
    monitor = KeyboardMonitor(buffer_size=30)
    monitor.start()
    
    try:
        print("Monitoring keyboard... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
            print(f"Buffer: {monitor.get_key_sequence_string()}")
    except KeyboardInterrupt:
        print("\nStopping...")
        monitor.stop()

