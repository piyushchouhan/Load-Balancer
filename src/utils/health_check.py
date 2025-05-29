"""
Health Check Utilities

This module provides functions to check the health of servers in the load balancing pool.
"""

import time
import logging
import socket
import threading
from typing import Dict, List, Optional, Callable, Any
import http.client
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger(__name__)


class HealthCheckResult:
    """
    Represents the result of a health check.
    """
    
    def __init__(
        self,
        is_healthy: bool,
        response_time: float = 0.0,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        Initialize a new HealthCheckResult instance.
        
        Args:
            is_healthy: Whether the server is healthy.
            response_time: The time (in seconds) it took to respond.
            status_code: The HTTP status code (for HTTP health checks).
            error_message: An error message if the check failed.
        """
        self.is_healthy = is_healthy
        self.response_time = response_time
        self.status_code = status_code
        self.error_message = error_message
        self.timestamp = time.time()
    
    def __str__(self):
        """String representation of a health check result."""
        status = "healthy" if self.is_healthy else "unhealthy"
        details = []
        if self.response_time > 0:
            details.append(f"response_time={self.response_time:.3f}s")
        if self.status_code is not None:
            details.append(f"status={self.status_code}")
        if self.error_message:
            details.append(f"error='{self.error_message}'")
        
        return f"HealthCheckResult({status}, {', '.join(details)})"


class HealthChecker:
    """
    A health checker for monitoring the health of servers.
    """
    
    def __init__(
        self,
        check_interval: float = 10.0,
        timeout: float = 2.0,
        healthy_threshold: int = 2,
        unhealthy_threshold: int = 3,
    ):
        """
        Initialize a new HealthChecker instance.
        
        Args:
            check_interval: The interval (in seconds) between health checks.
            timeout: The timeout (in seconds) for health checks.
            healthy_threshold: The number of consecutive successful checks required to mark a server as healthy.
            unhealthy_threshold: The number of consecutive failed checks required to mark a server as unhealthy.
        """
        self.check_interval = check_interval
        self.timeout = timeout
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        
        self._servers = {}  # server_id -> server_info
        self._check_counters = {}  # server_id -> (healthy_count, unhealthy_count)
        self._last_results = {}  # server_id -> HealthCheckResult
        self._check_thread = None
        self._stop_event = threading.Event()
    
    def add_server(
        self,
        server_id: str,
        server_info: Dict[str, Any],
        check_endpoint: str = "/health",
        check_type: str = "http",
        expected_status: int = 200,
    ):
        """
        Add a server to be monitored.
        
        Args:
            server_id: A unique identifier for the server.
            server_info: Server information (must include 'address' and 'port').
            check_endpoint: The endpoint to check for HTTP/HTTPS checks.
            check_type: The type of check to perform ('http', 'tcp', or 'custom').
            expected_status: The expected HTTP status code for HTTP checks.
        """
        self._servers[server_id] = {
            "info": server_info,
            "check_endpoint": check_endpoint,
            "check_type": check_type,
            "expected_status": expected_status,
        }
        self._check_counters[server_id] = (0, 0)  # (healthy_count, unhealthy_count)
    
    def remove_server(self, server_id: str):
        """
        Remove a server from monitoring.
        
        Args:
            server_id: The unique identifier for the server.
        """
        if server_id in self._servers:
            self._servers.pop(server_id)
            self._check_counters.pop(server_id, None)
            self._last_results.pop(server_id, None)
    
    def start(self):
        """Start the health checking thread."""
        if self._check_thread and self._check_thread.is_alive():
            # Already running
            return
        
        self._stop_event.clear()
        self._check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self._check_thread.start()
        logger.info("Health checker started.")
    
    def stop(self):
        """Stop the health checking thread."""
        if self._check_thread and self._check_thread.is_alive():
            self._stop_event.set()
            self._check_thread.join(timeout=5.0)
            logger.info("Health checker stopped.")
    
    def _check_loop(self):
        """Main health checking loop."""
        while not self._stop_event.is_set():
            for server_id, server_config in list(self._servers.items()):
                try:
                    result = self._check_server(server_id, server_config)
                    self._last_results[server_id] = result
                    
                    # Update counters
                    healthy_count, unhealthy_count = self._check_counters[server_id]
                    if result.is_healthy:
                        healthy_count += 1
                        unhealthy_count = 0
                    else:
                        unhealthy_count += 1
                        healthy_count = 0
                    
                    self._check_counters[server_id] = (healthy_count, unhealthy_count)
                    
                    # Notify listeners if state has changed
                    if healthy_count >= self.healthy_threshold:
                        self._on_server_healthy(server_id)
                    elif unhealthy_count >= self.unhealthy_threshold:
                        self._on_server_unhealthy(server_id)
                
                except Exception as e:
                    logger.error(f"Error checking server {server_id}: {e}")
            
            # Wait for next check interval
            self._stop_event.wait(self.check_interval)
    
    def _check_server(self, server_id: str, server_config: Dict[str, Any]) -> HealthCheckResult:
        """
        Check the health of a server.
        
        Args:
            server_id: The server's unique identifier.
            server_config: The server's configuration.
            
        Returns:
            A HealthCheckResult object.
        """
        check_type = server_config["check_type"]
        server_info = server_config["info"]
        
        if check_type == "http" or check_type == "https":
            return self._http_check(
                server_id,
                server_info["address"],
                server_info["port"],
                server_config["check_endpoint"],
                check_type == "https",
                server_config["expected_status"],
            )
        elif check_type == "tcp":
            return self._tcp_check(server_id, server_info["address"], server_info["port"])
        else:
            return HealthCheckResult(False, error_message=f"Unknown check type: {check_type}")
    
    def _http_check(
        self,
        server_id: str,
        address: str,
        port: int,
        endpoint: str,
        use_ssl: bool,
        expected_status: int,
    ) -> HealthCheckResult:
        """
        Perform an HTTP health check.
        
        Args:
            server_id: The server's unique identifier.
            address: The server's address.
            port: The server's port.
            endpoint: The endpoint to check.
            use_ssl: Whether to use HTTPS.
            expected_status: The expected HTTP status code.
            
        Returns:
            A HealthCheckResult object.
        """
        start_time = time.time()
        
        try:
            if use_ssl:
                conn = http.client.HTTPSConnection(address, port, timeout=self.timeout)
            else:
                conn = http.client.HTTPConnection(address, port, timeout=self.timeout)
            
            conn.request("GET", endpoint)
            response = conn.getresponse()
            response_time = time.time() - start_time
            
            status_code = response.status
            is_healthy = status_code == expected_status
            
            if is_healthy:
                return HealthCheckResult(True, response_time, status_code)
            else:
                return HealthCheckResult(
                    False,
                    response_time,
                    status_code,
                    f"Unexpected status code: got {status_code}, expected {expected_status}"
                )
        
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(False, response_time, error_message=str(e))
        
        finally:
            conn.close()
    
    def _tcp_check(self, server_id: str, address: str, port: int) -> HealthCheckResult:
        """
        Perform a TCP health check.
        
        Args:
            server_id: The server's unique identifier.
            address: The server's address.
            port: The server's port.
            
        Returns:
            A HealthCheckResult object.
        """
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((address, port))
            response_time = time.time() - start_time
            return HealthCheckResult(True, response_time)
        
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(False, response_time, error_message=str(e))
        
        finally:
            sock.close()
    
    def _on_server_healthy(self, server_id: str):
        """
        Called when a server becomes healthy.
        
        Args:
            server_id: The server's unique identifier.
        """
        # This is a placeholder that can be overridden by subclasses
        # or replaced with a callback mechanism
        logger.info(f"Server {server_id} is now healthy")
    
    def _on_server_unhealthy(self, server_id: str):
        """
        Called when a server becomes unhealthy.
        
        Args:
            server_id: The server's unique identifier.
        """
        # This is a placeholder that can be overridden by subclasses
        # or replaced with a callback mechanism
        logger.warning(f"Server {server_id} is now unhealthy")
    
    def get_status(self, server_id: str = None) -> Dict[str, Any]:
        """
        Get the current health status of servers.
        
        Args:
            server_id: If provided, get status for a specific server. Otherwise, get status for all servers.
            
        Returns:
            A dictionary with server status information.
        """
        if server_id:
            if server_id not in self._servers:
                return {"error": f"Server {server_id} not found"}
            
            result = self._last_results.get(server_id)
            healthy_count, unhealthy_count = self._check_counters.get(server_id, (0, 0))
            
            return {
                "server_id": server_id,
                "info": self._servers[server_id]["info"],
                "is_healthy": result.is_healthy if result else None,
                "last_check": result.timestamp if result else None,
                "response_time": result.response_time if result else None,
                "healthy_count": healthy_count,
                "unhealthy_count": unhealthy_count,
            }
        else:
            # Return status for all servers
            return {
                server_id: self.get_status(server_id)
                for server_id in self._servers
            }


# Simple function to ping a server to check if it's up
def ping_server(address: str, port: int, timeout: float = 1.0) -> bool:
    """
    Simple TCP ping to check if a server is reachable.
    
    Args:
        address: The server's address.
        port: The server's port.
        timeout: The timeout (in seconds) for the connection attempt.
        
    Returns:
        True if the server is reachable, False otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((address, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


# HTTP health check function
def http_health_check(
    url: str,
    timeout: float = 2.0,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    expected_status: int = 200,
) -> HealthCheckResult:
    """
    Perform an HTTP health check on a server.
    
    Args:
        url: The URL to check.
        timeout: The timeout (in seconds) for the request.
        method: The HTTP method to use.
        headers: Additional headers to send with the request.
        expected_status: The expected HTTP status code.
        
    Returns:
        A HealthCheckResult object.
    """
    start_time = time.time()
    
    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme == "https":
            conn = http.client.HTTPSConnection(parsed_url.netloc, timeout=timeout)
        else:
            conn = http.client.HTTPConnection(parsed_url.netloc, timeout=timeout)
        
        path = parsed_url.path or "/"
        if parsed_url.query:
            path += "?" + parsed_url.query
        
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        response_time = time.time() - start_time
        
        status_code = response.status
        is_healthy = status_code == expected_status
        
        if is_healthy:
            return HealthCheckResult(True, response_time, status_code)
        else:
            return HealthCheckResult(
                False,
                response_time,
                status_code,
                f"Unexpected status code: {status_code}"
            )
    
    except Exception as e:
        response_time = time.time() - start_time
        return HealthCheckResult(False, response_time, error_message=str(e))
    
    finally:
        conn.close()