#!/usr/bin/env python3
"""
Hackyeah Automation Backend - FastAPI Server
Entry point for the backend API server.
"""

import sys
import uvicorn
from src.main import app, config

if __name__ == "__main__":
    # Check if tray mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--tray":
        try:
            from tray_backend import BackendTrayApp
            app_instance = BackendTrayApp()
            app_instance.run()
        except ImportError as e:
            print(f"Tray mode not available: {e}")
            print("Please install required packages: pip install pystray pillow")
            print("Falling back to normal mode...")
            uvicorn.run(app, host="0.0.0.0", port=config.backend_port)
    else:
        uvicorn.run(app, host="0.0.0.0", port=config.backend_port)
