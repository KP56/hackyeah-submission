#!/usr/bin/env python3
"""
Hackyeah Automation Backend - System Tray Version
Backend server with system tray icon for easy management.
"""

import sys
import os
import threading
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import pystray
    from PIL import Image, ImageDraw
    import uvicorn
    from src.main import app, config, ai_interactions, recent_ops, python_agent
    from src.persistence import persistence
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Please install required packages:")
    print("pip install pystray pillow")
    sys.exit(1)

class BackendTrayApp:
    def __init__(self):
        self.icon = None
        self.server_thread = None
        self.server = None
        self.running = False
        self.shutdown_requested = False
        
    def create_icon_image(self, color='green'):
        """Create a simple icon for the system tray"""
        # Create a 64x64 image
        width = 64
        height = 64
        
        # Create image with transparent background
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a circle with the specified color
        if color == 'green':
            fill_color = (34, 197, 94, 255)  # Green
        elif color == 'red':
            fill_color = (239, 68, 68, 255)  # Red
        else:
            fill_color = (156, 163, 175, 255)  # Gray
            
        # Draw circle
        margin = 8
        draw.ellipse([margin, margin, width-margin, height-margin], 
                    fill=fill_color, outline=(255, 255, 255, 255), width=2)
        
        # Draw a small 'H' in the center
        draw.text((width//2 - 8, height//2 - 8), 'H', fill=(255, 255, 255, 255))
        
        return image

    def start_server(self):
        """Start the FastAPI server in a separate thread"""
        def run_server():
            try:
                print(f"Starting server on port {config.backend_port}...")
                self.server = uvicorn.Server(
                    uvicorn.Config(
                        app, 
                        host="0.0.0.0", 
                        port=config.backend_port,
                        log_level="info"
                    )
                )
                self.running = True
                self.update_icon('green')
                print("Server started successfully!")
                self.server.run()
            except Exception as e:
                print(f"Server error: {e}")
                import traceback
                traceback.print_exc()
                self.running = False
                self.update_icon('red')
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait a moment for server to start
        time.sleep(3)

    def request_shutdown(self):
        """Request shutdown from external source (like API endpoint)"""
        print("Shutdown requested via API endpoint")
        self.shutdown_requested = True
        self.stop_server()
    
    def stop_server(self):
        """Stop the FastAPI server"""
        print("Stopping backend server...")
        if self.server:
            self.server.should_exit = True
        self.running = False
        self.update_icon('red')
        
        # Give the server a moment to shut down gracefully
        import time
        time.sleep(1)
        
        # Force exit if needed
        import os
        os._exit(0)

    def update_icon(self, color):
        """Update the tray icon color"""
        if self.icon:
            self.icon.icon = self.create_icon_image(color)

    def on_quit(self, icon, item):
        """Handle quit action"""
        print("Quitting backend...")
        
        # Kill all frontend processes first
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
        
        # Save all data before shutting down
        print("Saving data to persistence...")
        try:
            # Save AI interactions
            if 'ai_interactions' in globals() and ai_interactions:
                persistence.save_ai_interactions(ai_interactions)
                print(f"Saved {len(ai_interactions)} AI interactions")
            
            # Save file operations
            if 'recent_ops' in globals() and recent_ops:
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
                print(f"Saved {len(file_ops_data)} file operations")
            
            # Save execution history
            if 'python_agent' in globals() and python_agent and hasattr(python_agent, 'get_execution_history'):
                execution_history = python_agent.get_execution_history()
                persistence.save_execution_history(execution_history)
                print(f"Saved {len(execution_history)} execution history entries")
                
        except Exception as e:
            print(f"Error saving data: {e}")
        
        self.stop_server()
        icon.stop()

    def on_show_status(self, icon, item):
        """Show status information"""
        status = "Running" if self.running else "Stopped"
        print(f"Backend Status: {status}")
        print(f"Port: {config.backend_port}")

    def on_restart(self, icon, item):
        """Restart the backend server"""
        print("Restarting backend...")
        self.stop_server()
        time.sleep(1)
        self.start_server()

    def run(self):
        """Run the tray application"""
        # Set global variable for shutdown endpoint access
        import sys
        sys.modules['__main__'].tray_app_instance = self
        
        # Create the menu
        menu = pystray.Menu(
            pystray.MenuItem("Backend Status", self.on_show_status),
            pystray.MenuItem("Restart Backend", self.on_restart),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.on_quit)
        )
        
        # Create the icon
        self.icon = pystray.Icon(
            "Hackyeah Backend",
            self.create_icon_image('gray'),
            "Hackyeah Automation Backend",
            menu
        )
        
        # Start the server
        self.start_server()
        
        # Run the tray icon
        print(f"Backend starting on port {config.backend_port}...")
        print("Backend tray icon created. Right-click to access menu.")
        print("The backend will continue running in the system tray.")
        
        try:
            self.icon.run()
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.on_quit(self.icon, None)

if __name__ == "__main__":
    tray_app = BackendTrayApp()
    tray_app.run()
