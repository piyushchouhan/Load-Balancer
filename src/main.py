#!/usr/bin/env python3
"""
Load Balancer Main Entry Point

This is the main entry point for the load balancer application.
It sets up the load balancer, adds servers, and starts the API server.
"""

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

from .core.load_balancer import LoadBalancer, Server
from .core.consistent_hash import ConsistentHash
from .utils.hashing import get_hash_function
from .utils.health_check import HealthChecker
from .api.server import APIServer


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file.
        
    Returns:
        The configuration dictionary.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        sys.exit(1)


def create_default_config(config_path: str):
    """
    Create a default configuration file.
    
    Args:
        config_path: Path where to create the configuration file.
    """
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
                "weight": 1
            }
        ]
    }
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    logger.info(f"Created default configuration file: {config_path}")


def setup_load_balancer(config: dict) -> LoadBalancer:
    """
    Set up the load balancer with the given configuration.
    
    Args:
        config: The configuration dictionary.
        
    Returns:
        The configured LoadBalancer instance.
    """
    # Get the hash function
    hash_func_name = config.get("hash_function", "fnv1a")
    try:
        hash_func = get_hash_function(hash_func_name)
    except ValueError as e:
        logger.error(f"Invalid hash function: {e}")
        sys.exit(1)
    
    # Create the load balancer
    load_balancer = LoadBalancer(hash_func)
    
    # Add servers from configuration
    servers_config = config.get("servers", [])
    for server_config in servers_config:
        server = Server(
            name=server_config["name"],
            address=server_config["address"],
            port=server_config["port"],
            weight=server_config.get("weight", 1)
        )
        load_balancer.add_server(server)
        logger.info(f"Added server: {server}")
    
    return load_balancer


def setup_health_checker(config: dict, load_balancer: LoadBalancer) -> HealthChecker:
    """
    Set up the health checker with the given configuration.
    
    Args:
        config: The configuration dictionary.
        load_balancer: The LoadBalancer instance.
        
    Returns:
        The configured HealthChecker instance.
    """
    health_config = config.get("health_check", {})
    
    health_checker = HealthChecker(
        check_interval=health_config.get("interval", 10.0),
        timeout=health_config.get("timeout", 2.0),
        healthy_threshold=health_config.get("healthy_threshold", 2),
        unhealthy_threshold=health_config.get("unhealthy_threshold", 3)
    )
    
    # Add all servers to the health checker
    for server in load_balancer.get_all_servers():
        health_checker.add_server(
            server_id=server.name,
            server_info={
                "address": server.address,
                "port": server.port
            },
            check_type="tcp"  # Use TCP check by default
        )
    
    return health_checker


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main entry point for the load balancer application."""
    parser = argparse.ArgumentParser(description="Load Balancer with Consistent Hashing")
    parser.add_argument(
        "--config",
        "-c",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default configuration file and exit"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Override API host from configuration"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override API port from configuration"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    # Create default config if requested
    if args.create_config:
        create_default_config(args.config)
        return
    
    # Load configuration
    config = load_config(args.config)
    
    # Override configuration with command line arguments
    if args.host:
        config.setdefault("api", {})["host"] = args.host
    if args.port:
        config.setdefault("api", {})["port"] = args.port
    if args.debug:
        config.setdefault("api", {})["debug"] = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Set up load balancer
        logger.info("Setting up load balancer...")
        load_balancer = setup_load_balancer(config)
        
        # Set up health checker
        logger.info("Setting up health checker...")
        health_checker = setup_health_checker(config, load_balancer)
        health_checker.start()
        
        # Set up API server
        logger.info("Setting up API server...")
        api_config = config.get("api", {})
        api_server = APIServer(
            load_balancer=load_balancer,
            health_checker=health_checker,
            host=api_config.get("host", "0.0.0.0"),
            port=api_config.get("port", 8080),
            debug=api_config.get("debug", False)
        )
        
        # Start the API server
        logger.info("Starting load balancer...")
        logger.info(f"API server will be available at http://{api_config.get('host', '0.0.0.0')}:{api_config.get('port', 8080)}")
        
        # Show current server status
        stats = load_balancer.get_stats()
        logger.info(f"Load balancer statistics: {stats}")
        
        # Start the server (this will block)
        api_server.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            health_checker.stop()
        except:
            pass
        logger.info("Load balancer stopped.")


if __name__ == "__main__":
    main()