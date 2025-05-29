"""
Load Balancer Implementation

This module provides a load balancer implementation that uses consistent hashing
to distribute requests across multiple servers.
"""

from typing import Dict, List, Optional, Callable, Any
import time
import threading
import logging

from .consistent_hash import ConsistentHash


logger = logging.getLogger(__name__)


class Server:
    """
    Represents a server in the load balancing pool.
    
    Stores information about a server such as its address, health status,
    and various metrics.
    """
    
    def __init__(self, name: str, address: str, port: int, weight: int = 1):
        """
        Initialize a new Server instance.
        
        Args:
            name: A unique identifier for the server.
            address: The server's IP address or hostname.
            port: The port the server is listening on.
            weight: The weight of the server in the load balancing scheme.
        """
        self.name = name
        self.address = address
        self.port = port
        self.weight = weight
        self.healthy = True
        self.last_health_check = time.time()
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        
    def __str__(self) -> str:
        """String representation of a server."""
        status = "healthy" if self.healthy else "unhealthy"
        return f"Server({self.name}, {self.address}:{self.port}, {status})"
    
    def get_url(self) -> str:
        """Get the full URL for this server."""
        return f"http://{self.address}:{self.port}"
    
    def get_average_response_time(self) -> float:
        """Calculate the average response time for this server."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def record_request(self, response_time: Optional[float] = None):
        """
        Record that a request was processed by this server.
        
        Args:
            response_time: The time (in seconds) it took to process the request.
        """
        self.request_count += 1
        if response_time is not None:
            self.response_times.append(response_time)
            # Keep only the most recent 100 response times
            if len(self.response_times) > 100:
                self.response_times.pop(0)
    
    def record_error(self):
        """Record that an error occurred when processing a request."""
        self.error_count += 1


class LoadBalancer:
    """
    A load balancer that uses consistent hashing to distribute requests across servers.
    
    Features:
    - Consistent hashing for request distribution
    - Virtual nodes for better distribution
    - Health monitoring of servers
    - Server addition/removal with minimal impact
    """
    
    def __init__(self, hash_func: Callable[[str], int]):
        """
        Initialize a new LoadBalancer instance.
        
        Args:
            hash_func: A function that takes a string and returns an integer hash value.
        """
        self.consistent_hash = ConsistentHash(hash_func)
        self.servers: Dict[str, Server] = {}
        self.lock = threading.RLock()  # For thread safety
        self.health_check_interval = 10.0  # seconds
        self.health_checker_running = False
    
    def add_server(self, server: Server) -> None:
        """
        Add a server to the load balancer.
        
        Args:
            server: The server to add.
        """
        with self.lock:
            if server.name in self.servers:
                logger.warning(f"Server {server.name} already exists, updating configuration")
            
            self.servers[server.name] = server
            self.consistent_hash.add_node(server.name, server.weight)
            logger.info(f"Added server {server}")
            
            # Start health checker if not already running
            if not self.health_checker_running:
                self._start_health_checker()
    
    def remove_server(self, server_name: str) -> bool:
        """
        Remove a server from the load balancer.
        
        Args:
            server_name: The name of the server to remove.
            
        Returns:
            True if the server was removed, False otherwise.
        """
        with self.lock:
            if server_name not in self.servers:
                logger.warning(f"Server {server_name} not found")
                return False
            
            server = self.servers.pop(server_name)
            self.consistent_hash.remove_node(server_name)
            logger.info(f"Removed server {server}")
            return True
    
    def get_server(self, key: str) -> Optional[Server]:
        """
        Get the server that should handle the given key.
        
        Args:
            key: The key to look up (e.g., client IP, request path).
            
        Returns:
            The server that should handle the request, or None if no servers are available.
        """
        with self.lock:
            server_name = self.consistent_hash.get_node(key)
            if not server_name or server_name not in self.servers:
                return None
            
            server = self.servers[server_name]
            
            # Don't return unhealthy servers
            if not server.healthy:
                # Try to find the next healthy server
                for name in self.consistent_hash.get_nodes(key, len(self.servers)):
                    if name in self.servers and self.servers[name].healthy:
                        return self.servers[name]
                # If no healthy servers found, return None
                return None
            
            return server
    
    def mark_server_status(self, server_name: str, healthy: bool) -> bool:
        """
        Mark a server as healthy or unhealthy.
        
        Args:
            server_name: The name of the server.
            healthy: The new health status.
            
        Returns:
            True if the server status was updated, False otherwise.
        """
        with self.lock:
            if server_name not in self.servers:
                logger.warning(f"Server {server_name} not found")
                return False
            
            server = self.servers[server_name]
            if server.healthy != healthy:
                server.healthy = healthy
                status = "healthy" if healthy else "unhealthy"
                logger.info(f"Server {server_name} is now {status}")
            
            server.last_health_check = time.time()
            return True
    
    def _start_health_checker(self) -> None:
        """Start the health checking thread."""
        if self.health_checker_running:
            return
        
        self.health_checker_running = True
        thread = threading.Thread(target=self._health_check_loop, daemon=True)
        thread.start()
    
    def _health_check_loop(self) -> None:
        """Periodically check the health of all servers."""
        try:
            while True:
                time.sleep(self.health_check_interval)
                self._check_all_servers()
        except Exception as e:
            logger.error(f"Health checker failed: {e}")
        finally:
            self.health_checker_running = False
    
    def _check_all_servers(self) -> None:
        """Check the health of all servers."""
        for server_name, server in list(self.servers.items()):
            try:
                # In a real implementation, we would make a health check request to the server
                # For this example, we just assume the server is healthy
                # self._check_server_health(server)
                pass
            except Exception as e:
                logger.error(f"Health check failed for {server_name}: {e}")
                self.mark_server_status(server_name, False)
    
    def _check_server_health(self, server: Server) -> bool:
        """
        Check if a server is healthy.
        
        This should be implemented with actual health check logic,
        such as making an HTTP request to a health endpoint.
        
        Args:
            server: The server to check.
            
        Returns:
            True if the server is healthy, False otherwise.
        """
        # This would typically make an HTTP request to the server's health endpoint
        # For now, we just set it to True
        return True
    
    def get_all_servers(self) -> List[Server]:
        """
        Get all servers in the load balancer.
        
        Returns:
            A list of all servers.
        """
        with self.lock:
            return list(self.servers.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the load balancer.
        
        Returns:
            A dictionary with statistics.
        """
        with self.lock:
            total_requests = sum(s.request_count for s in self.servers.values())
            total_errors = sum(s.error_count for s in self.servers.values())
            healthy_count = sum(1 for s in self.servers.values() if s.healthy)
            
            return {
                "total_servers": len(self.servers),
                "healthy_servers": healthy_count,
                "unhealthy_servers": len(self.servers) - healthy_count,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": total_errors / total_requests if total_requests > 0 else 0
            }