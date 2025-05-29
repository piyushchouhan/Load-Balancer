"""
API Routes for Load Balancer

This module defines the API routes and request handlers for the load balancer.
It provides a more organized way to handle different API endpoints.
"""

from flask import Blueprint, request, jsonify, Response
import logging
import time
from typing import Dict, Any

from ..core.load_balancer import LoadBalancer, Server
from ..utils.health_check import HealthChecker


logger = logging.getLogger(__name__)


def create_api_routes(load_balancer: LoadBalancer, health_checker: HealthChecker) -> Blueprint:
    """
    Create API routes blueprint.
    
    Args:
        load_balancer: The LoadBalancer instance.
        health_checker: The HealthChecker instance.
        
    Returns:
        A Flask Blueprint with all API routes.
    """
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    @api_bp.route('/servers', methods=['GET'])
    def get_servers():
        """Get all servers and their status."""
        try:
            servers = []
            for server in load_balancer.get_all_servers():
                server_info = {
                    "name": server.name,
                    "address": server.address,
                    "port": server.port,
                    "weight": server.weight,
                    "healthy": server.healthy,
                    "last_health_check": server.last_health_check,
                    "request_count": server.request_count,
                    "error_count": server.error_count,
                    "average_response_time": server.get_average_response_time(),
                    "url": server.get_url(),
                    "error_rate": (
                        server.error_count / server.request_count 
                        if server.request_count > 0 else 0
                    )
                }
                
                # Add health check details if available
                health_status = health_checker.get_status(server.name)
                if "error" not in health_status:
                    server_info["health_check"] = {
                        "last_check": health_status.get("last_check"),
                        "response_time": health_status.get("response_time"),
                        "healthy_count": health_status.get("healthy_count"),
                        "unhealthy_count": health_status.get("unhealthy_count")
                    }
                
                servers.append(server_info)
            
            return jsonify({
                "servers": servers,
                "total_count": len(servers),
                "healthy_count": sum(1 for s in servers if s["healthy"]),
                "timestamp": time.time()
            })
            
        except Exception as e:
            logger.error(f"Error getting servers: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/servers', methods=['POST'])
    def add_server():
        """Add a new server to the load balancer."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            # Validate required fields
            required_fields = ["name", "address", "port"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400
            
            # Validate data types
            try:
                port = int(data["port"])
                weight = int(data.get("weight", 1))
            except ValueError:
                return jsonify({"error": "Port and weight must be integers"}), 400
            
            if port <= 0 or port > 65535:
                return jsonify({"error": "Port must be between 1 and 65535"}), 400
            
            if weight <= 0:
                return jsonify({"error": "Weight must be positive"}), 400
            
            # Check if server already exists
            existing_servers = load_balancer.get_all_servers()
            if any(s.name == data["name"] for s in existing_servers):
                return jsonify({"error": f"Server with name '{data['name']}' already exists"}), 409
            
            # Create server
            server = Server(
                name=data["name"],
                address=data["address"],
                port=port,
                weight=weight
            )
            
            # Add to load balancer
            load_balancer.add_server(server)
            
            # Add to health checker
            health_checker.add_server(
                server_id=server.name,
                server_info={
                    "address": server.address,
                    "port": server.port
                },
                check_type=data.get("health_check_type", "tcp"),
                check_endpoint=data.get("health_check_endpoint", "/health"),
                expected_status=data.get("expected_status", 200)
            )
            
            logger.info(f"Added server {server.name} ({server.address}:{server.port})")
            
            return jsonify({
                "message": f"Server {server.name} added successfully",
                "server": {
                    "name": server.name,
                    "address": server.address,
                    "port": server.port,
                    "weight": server.weight,
                    "url": server.get_url()
                }
            }), 201
            
        except Exception as e:
            logger.error(f"Error adding server: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/servers/<server_name>', methods=['GET'])
    def get_server(server_name: str):
        """Get information about a specific server."""
        try:
            servers = load_balancer.get_all_servers()
            server = next((s for s in servers if s.name == server_name), None)
            
            if not server:
                return jsonify({"error": f"Server {server_name} not found"}), 404
            
            server_info = {
                "name": server.name,
                "address": server.address,
                "port": server.port,
                "weight": server.weight,
                "healthy": server.healthy,
                "last_health_check": server.last_health_check,
                "request_count": server.request_count,
                "error_count": server.error_count,
                "average_response_time": server.get_average_response_time(),
                "url": server.get_url(),
                "error_rate": (
                    server.error_count / server.request_count 
                    if server.request_count > 0 else 0
                )
            }
            
            # Add health check details
            health_status = health_checker.get_status(server_name)
            if "error" not in health_status:
                server_info["health_check"] = health_status
            
            return jsonify(server_info)
            
        except Exception as e:
            logger.error(f"Error getting server {server_name}: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/servers/<server_name>', methods=['PUT'])
    def update_server(server_name: str):
        """Update server configuration."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            servers = load_balancer.get_all_servers()
            server = next((s for s in servers if s.name == server_name), None)
            
            if not server:
                return jsonify({"error": f"Server {server_name} not found"}), 404
            
            # Update allowed fields
            updated_fields = []
            
            if "weight" in data:
                try:
                    new_weight = int(data["weight"])
                    if new_weight <= 0:
                        return jsonify({"error": "Weight must be positive"}), 400
                    
                    # Remove and re-add server with new weight
                    load_balancer.remove_server(server_name)
                    server.weight = new_weight
                    load_balancer.add_server(server)
                    updated_fields.append("weight")
                    
                except ValueError:
                    return jsonify({"error": "Weight must be an integer"}), 400
            
            return jsonify({
                "message": f"Server {server_name} updated successfully",
                "updated_fields": updated_fields
            })
            
        except Exception as e:
            logger.error(f"Error updating server {server_name}: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/servers/<server_name>', methods=['DELETE'])
    def remove_server(server_name: str):
        """Remove a server from the load balancer."""
        try:
            # Remove from load balancer
            success = load_balancer.remove_server(server_name)
            if not success:
                return jsonify({"error": f"Server {server_name} not found"}), 404
            
            # Remove from health checker
            health_checker.remove_server(server_name)
            
            logger.info(f"Removed server {server_name}")
            
            return jsonify({"message": f"Server {server_name} removed successfully"})
            
        except Exception as e:
            logger.error(f"Error removing server {server_name}: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/servers/<server_name>/health', methods=['PUT'])
    def set_server_health(server_name: str):
        """Manually set server health status."""
        try:
            data = request.get_json()
            if not data or "healthy" not in data:
                return jsonify({"error": "Missing 'healthy' field in JSON data"}), 400
            
            healthy = bool(data["healthy"])
            success = load_balancer.mark_server_status(server_name, healthy)
            
            if not success:
                return jsonify({"error": f"Server {server_name} not found"}), 404
            
            status = "healthy" if healthy else "unhealthy"
            logger.info(f"Manually set server {server_name} as {status}")
            
            return jsonify({"message": f"Server {server_name} marked as {status}"})
            
        except Exception as e:
            logger.error(f"Error setting server health: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/stats', methods=['GET'])
    def get_stats():
        """Get comprehensive load balancer statistics."""
        try:
            # Get basic stats
            stats = load_balancer.get_stats()
            
            # Add detailed server stats
            servers = load_balancer.get_all_servers()
            server_stats = []
            
            for server in servers:
                server_stat = {
                    "name": server.name,
                    "healthy": server.healthy,
                    "request_count": server.request_count,
                    "error_count": server.error_count,
                    "average_response_time": server.get_average_response_time()
                }
                server_stats.append(server_stat)
            
            stats["servers"] = server_stats
            stats["timestamp"] = time.time()
            
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for the load balancer itself."""
        try:
            stats = load_balancer.get_stats()
            healthy_servers = stats.get("healthy_servers", 0)
            total_servers = stats.get("total_servers", 0)
            
            if healthy_servers > 0:
                return jsonify({
                    "status": "healthy",
                    "healthy_servers": healthy_servers,
                    "total_servers": total_servers,
                    "timestamp": time.time()
                })
            else:
                return jsonify({
                    "status": "unhealthy",
                    "healthy_servers": healthy_servers,
                    "total_servers": total_servers,
                    "message": "No healthy backend servers available",
                    "timestamp": time.time()
                }), 503
                
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }), 500
    
    @api_bp.route('/debug/lookup/<key>', methods=['GET'])
    def debug_lookup(key: str):
        """Debug endpoint to see which server a key maps to."""
        try:
            server = load_balancer.get_server(key)
            
            # Also get multiple servers for comparison
            multiple_servers = load_balancer.consistent_hash.get_nodes(key, 3)
            
            result = {
                "key": key,
                "hash_value": load_balancer.consistent_hash.hash_func(key),
                "selected_server": None,
                "candidate_servers": multiple_servers
            }
            
            if server:
                result["selected_server"] = {
                    "name": server.name,
                    "address": server.address,
                    "port": server.port,
                    "healthy": server.healthy,
                    "url": server.get_url()
                }
            else:
                result["message"] = "No healthy servers available"
            
            return jsonify(result)
                
        except Exception as e:
            logger.error(f"Error in debug lookup: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @api_bp.route('/debug/ring', methods=['GET'])
    def debug_ring():
        """Debug endpoint to view the hash ring state."""
        try:
            ring_info = {
                "total_nodes": len(load_balancer.consistent_hash.ring),
                "physical_servers": list(load_balancer.consistent_hash.nodes.keys()),
                "virtual_nodes_per_server": {
                    name: len(nodes) 
                    for name, nodes in load_balancer.consistent_hash.nodes.items()
                }
            }
            
            # Add ring visualization (limited to avoid huge responses)
            if request.args.get('include_ring') == 'true':
                ring_items = []
                for hash_val in sorted(load_balancer.consistent_hash.sorted_keys[:100]):  # Limit to first 100
                    ring_items.append({
                        "hash": hash_val,
                        "server": load_balancer.consistent_hash.ring[hash_val]
                    })
                ring_info["ring_sample"] = ring_items
                ring_info["note"] = "Only showing first 100 virtual nodes"
            
            return jsonify(ring_info)
            
        except Exception as e:
            logger.error(f"Error getting ring debug info: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    return api_bp


def create_management_routes(load_balancer: LoadBalancer, health_checker: HealthChecker) -> Blueprint:
    """
    Create management routes blueprint for administrative tasks.
    
    Args:
        load_balancer: The LoadBalancer instance.
        health_checker: The HealthChecker instance.
        
    Returns:
        A Flask Blueprint with management routes.
    """
    mgmt_bp = Blueprint('management', __name__, url_prefix='/manage')
    
    @mgmt_bp.route('/reset', methods=['POST'])
    def reset_stats():
        """Reset all server statistics."""
        try:
            for server in load_balancer.get_all_servers():
                server.request_count = 0
                server.error_count = 0
                server.response_times = []
            
            return jsonify({"message": "Statistics reset successfully"})
            
        except Exception as e:
            logger.error(f"Error resetting stats: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @mgmt_bp.route('/drain/<server_name>', methods=['POST'])
    def drain_server(server_name: str):
        """Drain a server (mark as unhealthy to stop new requests)."""
        try:
            success = load_balancer.mark_server_status(server_name, False)
            if not success:
                return jsonify({"error": f"Server {server_name} not found"}), 404
            
            return jsonify({"message": f"Server {server_name} is now draining (marked unhealthy)"})
            
        except Exception as e:
            logger.error(f"Error draining server: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @mgmt_bp.route('/enable/<server_name>', methods=['POST'])
    def enable_server(server_name: str):
        """Enable a server (mark as healthy)."""
        try:
            success = load_balancer.mark_server_status(server_name, True)
            if not success:
                return jsonify({"error": f"Server {server_name} not found"}), 404
            
            return jsonify({"message": f"Server {server_name} is now enabled (marked healthy)"})
            
        except Exception as e:
            logger.error(f"Error enabling server: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    return mgmt_bp