#!/usr/bin/env python3
"""
Test Backend Servers

This script creates simple HTTP servers that can be used to test the load balancer.
Each server returns a JSON response identifying itself.
"""

import sys
import json
import time
import threading
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class TestServerHandler(BaseHTTPRequestHandler):
    """HTTP handler for test servers."""
    
    def __init__(self, server_name, server_port, *args, **kwargs):
        self.server_name = server_name
        self.server_port = server_port
        self.request_count = 0
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        self.request_count += 1
        
        # Parse URL
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Create response
        response_data = {
            "server_name": self.server_name,
            "server_port": self.server_port,
            "path": parsed_url.path,
            "query": dict(query_params),
            "method": "GET",
            "request_count": self.request_count,
            "timestamp": time.time(),
            "headers": dict(self.headers)
        }
        
        # Special health check endpoint
        if parsed_url.path == "/health":
            response_data["status"] = "healthy"
            response_data["uptime"] = time.time() - getattr(self, 'start_time', time.time())
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Server', f'{self.server_name}')
        self.end_headers()
        
        response_json = json.dumps(response_data, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
    
    def do_POST(self):
        """Handle POST requests."""
        self.request_count += 1
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Parse URL
        parsed_url = urlparse(self.path)
        
        # Create response
        response_data = {
            "server_name": self.server_name,
            "server_port": self.server_port,
            "path": parsed_url.path,
            "method": "POST",
            "request_count": self.request_count,
            "timestamp": time.time(),
            "post_data": post_data.decode('utf-8', errors='ignore'),
            "content_length": content_length
        }
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Server', f'{self.server_name}')
        self.end_headers()
        
        response_json = json.dumps(response_data, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to provide custom logging."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.server_name}: {format % args}")


def create_server_handler(server_name, server_port):
    """Create a handler class for a specific server."""
    class ServerHandler(TestServerHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(server_name, server_port, *args, **kwargs)
            self.start_time = time.time()
    
    return ServerHandler


def start_test_server(name, port, delay=0):
    """Start a test server on the specified port."""
    if delay > 0:
        print(f"Waiting {delay} seconds before starting {name}...")
        time.sleep(delay)
    
    try:
        handler_class = create_server_handler(name, port)
        httpd = HTTPServer(('', port), handler_class)
        
        print(f"Starting {name} on port {port}")
        print(f"  Health check: http://localhost:{port}/health")
        print(f"  Test endpoint: http://localhost:{port}/test")
        
        httpd.serve_forever()
        
    except OSError as e:
        if e.errno == 10048:  # Address already in use on Windows
            print(f"Error: Port {port} is already in use")
        else:
            print(f"Error starting server {name} on port {port}: {e}")
    except KeyboardInterrupt:
        print(f"\nShutting down {name}...")
    except Exception as e:
        print(f"Error in server {name}: {e}")


def main():
    """Main function to start test servers."""
    parser = argparse.ArgumentParser(description="Start test backend servers for load balancer testing")
    parser.add_argument(
        '--ports',
        nargs='+',
        type=int,
        default=[8001, 8002, 8003],
        help='Ports to start servers on (default: 8001 8002 8003)'
    )
    parser.add_argument(
        '--names',
        nargs='+',
        default=None,
        help='Names for the servers (default: server1, server2, ...)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0,
        help='Delay between starting servers (seconds)'
    )
    parser.add_argument(
        '--single',
        type=int,
        help='Start only a single server on specified port'
    )
    
    args = parser.parse_args()
    
    if args.single:
        # Start single server
        server_name = f"TestServer-{args.single}"
        print(f"Starting single test server: {server_name}")
        start_test_server(server_name, args.single)
        return
    
    # Generate server names if not provided
    if args.names:
        if len(args.names) != len(args.ports):
            print("Error: Number of names must match number of ports")
            sys.exit(1)
        server_names = args.names
    else:
        server_names = [f"TestServer{i+1}" for i in range(len(args.ports))]
    
    print("Starting test backend servers...")
    print("These servers will respond with JSON indicating which server handled the request.")
    print("Press Ctrl+C to stop all servers.\n")
    
    # Start servers in separate threads
    threads = []
    for i, (name, port) in enumerate(zip(server_names, args.ports)):
        delay = i * args.delay if args.delay > 0 else 0
        thread = threading.Thread(
            target=start_test_server,
            args=(name, port, delay),
            daemon=True,
            name=f"Server-{port}"
        )
        thread.start()
        threads.append(thread)
    
    try:
        # Wait for all servers to start
        time.sleep(1)
        
        print("\n=== Test Servers Started ===")
        for name, port in zip(server_names, args.ports):
            print(f"  {name}: http://localhost:{port}/")
        
        print("\nYou can now start the load balancer and test it!")
        print("Example commands:")
        print("  curl http://localhost:8080/test")
        print("  curl -X POST -d 'test data' http://localhost:8080/api/test")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down all test servers...")
        # Threads are daemon threads, they'll terminate when main thread exits


if __name__ == "__main__":
    main()
