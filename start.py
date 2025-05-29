#!/usr/bin/env python3
"""
Quick Start Script

This script helps you quickly start the load balancer with default settings.
"""

import os
import sys
import subprocess
import json

def check_python_version():
    """Check if Python version is adequate."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)

def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("Error: Failed to install dependencies")
        sys.exit(1)

def create_default_config():
    """Create default configuration if it doesn't exist."""
    config_path = "config.json"
    if not os.path.exists(config_path):
        print("Creating default configuration...")
        default_config = {
            "hash_function": "fnv1a",
            "api": {
                "host": "0.0.0.0",
                "port": 8080,
                "debug": False
            },
            "health_check": {
                "interval": 10.0,
                "timeout": 2.0,
                "healthy_threshold": 2,
                "unhealthy_threshold": 3
            },
            "servers": [
                {
                    "name": "server1",
                    "address": "127.0.0.1",
                    "port": 8001,
                    "weight": 1
                },
                {
                    "name": "server2",
                    "address": "127.0.0.1", 
                    "port": 8002,
                    "weight": 1
                },
                {
                    "name": "server3",
                    "address": "127.0.0.1",
                    "port": 8003,
                    "weight": 2
                }
            ]
        }
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created {config_path}")

def start_load_balancer():
    """Start the load balancer."""
    print("Starting load balancer...")
    try:
        # Change to src directory and run main.py
        src_path = os.path.join(os.path.dirname(__file__), "src")
        main_script = os.path.join(src_path, "main.py")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = src_path
        
        subprocess.run([sys.executable, main_script], cwd=os.path.dirname(__file__), env=env)
    except KeyboardInterrupt:
        print("\nShutting down load balancer...")
    except Exception as e:
        print(f"Error starting load balancer: {e}")
        sys.exit(1)

def main():
    """Main function."""
    print("=== Load Balancer Quick Start ===\n")
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    if "--skip-install" not in sys.argv:
        install_dependencies()
    
    # Create default config
    create_default_config()
    
    # Start load balancer
    start_load_balancer()

if __name__ == "__main__":
    main()
