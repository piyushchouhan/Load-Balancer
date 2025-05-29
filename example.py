#!/usr/bin/env python3
"""
Simple Example Script

This script demonstrates how to use the load balancer with some example servers.
"""

import sys
import os
import time
import threading
import http.server
import socketserver

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.load_balancer import LoadBalancer, Server
from utils.hashing import get_hash_function


class SimpleHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Simple HTTP handler that returns server info."""
    
    def __init__(self, server_name, *args, **kwargs):
        self.server_name = server_name
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "server": self.server_name,
            "path": self.path,
            "timestamp": time.time(),
            "message": f"Hello from {self.server_name}!"
        }
        
        import json
        self.wfile.write(json.dumps(response, indent=2).encode())


def create_test_server(name: str, port: int):
    """Create a simple test HTTP server."""
    def handler_factory(*args, **kwargs):
        return SimpleHTTPHandler(name, *args, **kwargs)
    
    httpd = socketserver.TCPServer(("", port), handler_factory)
    httpd.server_name = name
    return httpd


def start_test_servers():
    """Start multiple test servers in background threads."""
    servers = []
    ports = [8001, 8002, 8003]
    
    for i, port in enumerate(ports, 1):
        server_name = f"TestServer{i}"
        httpd = create_test_server(server_name, port)
        
        # Start server in a background thread
        thread = threading.Thread(
            target=httpd.serve_forever,
            daemon=True,
            name=f"Server-{port}"
        )
        thread.start()
        
        servers.append((httpd, thread))
        print(f"Started {server_name} on port {port}")
    
    return servers


def demo_load_balancer():
    """Demonstrate the load balancer functionality."""
    print("=== Load Balancer Demo ===\n")
    
    # Create load balancer with FNV1a hash function
    hash_func = get_hash_function("fnv1a")
    lb = LoadBalancer(hash_func)
    
    # Add servers
    servers = [
        Server("server1", "127.0.0.1", 8001, weight=1),
        Server("server2", "127.0.0.1", 8002, weight=1), 
        Server("server3", "127.0.0.1", 8003, weight=2),  # Higher weight
    ]
    
    for server in servers:
        lb.add_server(server)
        print(f"Added {server}")
    
    print(f"\nLoad balancer stats: {lb.get_stats()}")
    
    # Test key distribution
    print("\n=== Testing Key Distribution ===")
    test_keys = [
        "user123", "user456", "user789",
        "192.168.1.10", "192.168.1.20", "192.168.1.30",
        "/api/data", "/api/users", "/api/orders"
    ]
    
    distribution = {}
    for key in test_keys:
        server = lb.get_server(key)
        if server:
            distribution[server.name] = distribution.get(server.name, 0) + 1
            print(f"Key '{key}' -> {server.name}")
        else:
            print(f"Key '{key}' -> No server available")
    
    print(f"\nDistribution: {distribution}")
    
    # Test server removal
    print("\n=== Testing Server Removal ===")
    print("Removing server2...")
    lb.remove_server("server2")
    
    print("Key distribution after removal:")
    distribution_after = {}
    for key in test_keys:
        server = lb.get_server(key)
        if server:
            distribution_after[server.name] = distribution_after.get(server.name, 0) + 1
            print(f"Key '{key}' -> {server.name}")
    
    print(f"New distribution: {distribution_after}")
    
    # Test server addition back
    print("\n=== Testing Server Re-addition ===")
    lb.add_server(Server("server2", "127.0.0.1", 8002, weight=1))
    print("Re-added server2")
    
    print("Final key distribution:")
    final_distribution = {}
    for key in test_keys:
        server = lb.get_server(key)
        if server:
            final_distribution[server.name] = final_distribution.get(server.name, 0) + 1
            print(f"Key '{key}' -> {server.name}")
    
    print(f"Final distribution: {final_distribution}")
    print(f"\nFinal stats: {lb.get_stats()}")


def demo_hash_functions():
    """Demonstrate different hash functions."""
    print("\n=== Hash Function Comparison ===")
    
    hash_functions = ["simple", "djb2", "fnv1a", "crc32", "md5"]
    test_key = "test_user_123"
    
    for func_name in hash_functions:
        try:
            hash_func = get_hash_function(func_name)
            hash_value = hash_func(test_key)
            print(f"{func_name.upper():8}: {hash_value:>12} (0x{hash_value:08x})")
        except ValueError:
            print(f"{func_name.upper():8}: Not available")


def main():
    """Main demo function."""
    try:
        # Start test servers
        print("Starting test HTTP servers...")
        test_servers = start_test_servers()
        
        # Give servers time to start
        time.sleep(1)
        
        # Run demos
        demo_hash_functions()
        demo_load_balancer()
        
        print("\n=== Demo Complete ===")
        print("Test servers are running. You can test them directly:")
        print("  curl http://localhost:8001/")
        print("  curl http://localhost:8002/")
        print("  curl http://localhost:8003/")
        print("\nPress Ctrl+C to stop all servers.")
        
        # Keep servers running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down servers...")
            for httpd, thread in test_servers:
                httpd.shutdown()
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
