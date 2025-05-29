"""
Load Balancer Package

A high-performance load balancer implementation using consistent hashing.
"""

__version__ = "1.0.0"
__author__ = "Load Balancer Team"

# Import main components for easier access
from .core.load_balancer import LoadBalancer, Server
from .core.consistent_hash import ConsistentHash
from .utils.hashing import get_hash_function
from .utils.health_check import HealthChecker

__all__ = [
    'LoadBalancer',
    'Server', 
    'ConsistentHash',
    'get_hash_function',
    'HealthChecker'
]