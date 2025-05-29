"""
API Server for Load Balancer

This module provides a Flask-based API server for the load balancer.
It exposes endpoints for load balancing, server management, and monitoring.
"""

import logging
import time
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, redirect, Response
import requests
from werkzeug.exceptions import NotFound, BadRequest, InternalServerError

from ..core.load_balancer import LoadBalancer
from ..utils.health_check import HealthChecker
from .routes import create_api_routes, create_management_routes


logger = logging.getLogger(__name__)


class APIServer:
    """
    Flask-based API server for the load balancer.
    
    Provides endpoints for:
    - Load balancing requests
    - Server management
    - Health monitoring
    - Statistics
    """
    
    def __init__(
        self,
        load_balancer: LoadBalancer,
        health_checker: HealthChecker,
        host: str = "0.0.0.0",
        port: int = 8080,
        debug: bool = False
    ):
        """
        Initialize the API server.
        
        Args:
            load_balancer: The LoadBalancer instance.
            health_checker: The HealthChecker instance.
            host: The host to bind to.
            port: The port to bind to.
            debug: Whether to enable debug mode.        
        """
        self.load_balancer = load_balancer
        self.health_checker = health_checker
        self.host = host
        self.port = port
        self.debug = debug
        
        # Create Flask app
        self.app = Flask(__name__)
        self.app.config['DEBUG'] = debug
        
        # Set up routes
        self._setup_routes()
        
        # Set up error handlers
        self._setup_error_handlers()        
    def _setup_routes(self):
        """Set up API routes."""
        
        # Register API routes blueprint
        api_routes = create_api_routes(self.load_balancer, self.health_checker)
        self.app.register_blueprint(api_routes)
        
        # Register management routes blueprint
        mgmt_routes = create_management_routes(self.load_balancer, self.health_checker)
        self.app.register_blueprint(mgmt_routes)
        
        # Load balancing endpoint (catch-all for proxying)
        @self.app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        @self.app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        def proxy_request(path):
            """Proxy requests to backend servers."""
            # Skip API and management routes
            if path.startswith('api/') or path.startswith('manage/'):
                return jsonify({"error": "Route not found"}), 404
            return self._handle_proxy_request(path)
    
    def _setup_error_handlers(self):
        """Set up error handlers."""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({"error": "Not found"}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({"error": "Internal server error"}), 500
        
        @self.app.errorhandler(BadRequest)
        def bad_request(error):
            return jsonify({"error": "Bad request", "message": str(error)}), 400
    
    def _handle_proxy_request(self, path: str) -> Response:
        """
        Handle proxying a request to a backend server.
        
        Args:
            path: The request path.
            
        Returns:
            A Flask Response object.
        """
        try:
            # Determine the key for consistent hashing
            # Use client IP + path as the key
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            key = f"{client_ip}:{path}"
            
            # Get the server for this key
            server = self.load_balancer.get_server(key)
            if not server:
                return jsonify({"error": "No healthy servers available"}), 503
            
            # Build the target URL
            target_url = f"{server.get_url()}/{path}"
            if request.query_string:
                target_url += f"?{request.query_string.decode('utf-8')}"
            
            # Record request start time
            start_time = time.time()
            
            try:
                # Forward the request
                response = requests.request(
                    method=request.method,
                    url=target_url,
                    headers={key: value for key, value in request.headers if key != 'Host'},
                    data=request.get_data(),
                    params=request.args,
                    allow_redirects=False,
                    timeout=30
                )
                
                # Record successful request
                response_time = time.time() - start_time
                server.record_request(response_time)
                
                # Create Flask response
                flask_response = Response(
                    response.content,
                    status=response.status_code,
                    headers=dict(response.headers)
                )
                # Add load balancer headers
                flask_response.headers['X-Load-Balancer-Server'] = server.name
                flask_response.headers['X-Load-Balancer-Response-Time'] = f"{response_time:.3f}"
                
                return flask_response
                
            except requests.exceptions.RequestException as e:
                # Record failed request
                response_time = time.time() - start_time
                server.record_error()
                
                logger.error(f"Error forwarding request to {server.name}: {e}")
                return jsonify({
                    "error": "Backend server error",
                    "server": server.name,
                    "message": str(e)
                }), 502
                
        except Exception as e:
            logger.error(f"Error handling proxy request: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    def run(self):
        """Start the API server."""
        logger.info(f"Starting API server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=self.debug)