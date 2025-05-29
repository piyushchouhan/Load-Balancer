import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from unittest.mock import Mock, patch
from core.load_balancer import LoadBalancer, Server
from utils.hashing import get_hash_function


class TestLoadBalancer(unittest.TestCase):
    """Test cases for LoadBalancer."""
    def setUp(self):
        """Set up test fixtures."""
        hash_func = get_hash_function('sha1')
        self.load_balancer = LoadBalancer(hash_func)
        
        # Create test servers
        self.server1 = Server("server1", "localhost", 8001)
        self.server2 = Server("server2", "localhost", 8002)
        self.server3 = Server("server3", "localhost", 8003)
    
    def test_load_balancer_creation(self):
        """Test load balancer creation."""
        self.assertIsNotNone(self.load_balancer)
        self.assertEqual(len(self.load_balancer.servers), 0)
        
    def test_add_server(self):
        """Test adding servers to the load balancer."""
        self.load_balancer.add_server(self.server1)
        self.assertEqual(len(self.load_balancer.servers), 1)
        self.assertIn("server1", self.load_balancer.servers)
        
        # Add another server
        self.load_balancer.add_server(self.server2)
        self.assertEqual(len(self.load_balancer.servers), 2)
        
    def test_remove_server(self):
        """Test removing servers from the load balancer."""
        self.load_balancer.add_server(self.server1)
        self.load_balancer.add_server(self.server2)
        
        # Remove existing server
        result = self.load_balancer.remove_server("server1")
        self.assertTrue(result)
        self.assertEqual(len(self.load_balancer.servers), 1)
        self.assertNotIn("server1", self.load_balancer.servers)
        
        # Try to remove non-existent server
        result = self.load_balancer.remove_server("nonexistent")
        self.assertFalse(result)
        
    def test_get_server(self):
        """Test getting servers for keys."""
        self.load_balancer.add_server(self.server1)
        self.load_balancer.add_server(self.server2)
        
        # Test with a specific key
        server = self.load_balancer.get_server("test_key")
        self.assertIsNotNone(server)
        self.assertIn(server.name, ["server1", "server2"])
        
        # Same key should return same server (consistency)
        server2 = self.load_balancer.get_server("test_key")
        self.assertEqual(server.name, server2.name)
        
    def test_get_server_no_servers(self):
        """Test getting server when no servers are available."""
        server = self.load_balancer.get_server("test_key")
        self.assertIsNone(server)
        
    def test_get_server_no_healthy_servers(self):
        """Test getting server when no healthy servers are available."""
        self.load_balancer.add_server(self.server1)
        self.server1.healthy = False
        
        server = self.load_balancer.get_server("test_key")
        self.assertIsNone(server)
        
    def test_mark_server_status(self):
        """Test marking server health status."""
        self.load_balancer.add_server(self.server1)
        
        # Mark as unhealthy
        result = self.load_balancer.mark_server_status("server1", False)
        self.assertTrue(result)
        self.assertFalse(self.server1.healthy)
        
        # Mark as healthy
        result = self.load_balancer.mark_server_status("server1", True)
        self.assertTrue(result)
        self.assertTrue(self.server1.healthy)
        
        # Try with non-existent server
        result = self.load_balancer.mark_server_status("nonexistent", True)
        self.assertFalse(result)
        
    def test_get_all_servers(self):
        """Test getting all servers."""
        servers = self.load_balancer.get_all_servers()
        self.assertEqual(len(servers), 0)
        
        self.load_balancer.add_server(self.server1)
        self.load_balancer.add_server(self.server2)
        
        servers = self.load_balancer.get_all_servers()
        self.assertEqual(len(servers), 2)
        server_names = [s.name for s in servers]
        self.assertIn("server1", server_names)
        self.assertIn("server2", server_names)
        
    def test_get_stats(self):
        """Test getting load balancer statistics."""
        stats = self.load_balancer.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("total_servers", stats)
        self.assertIn("healthy_servers", stats)
        
        # Add some servers
        self.load_balancer.add_server(self.server1)
        self.load_balancer.add_server(self.server2)
        self.server2.healthy = False
        
        stats = self.load_balancer.get_stats()
        self.assertEqual(stats["total_servers"], 2)
        self.assertEqual(stats["healthy_servers"], 1)
        
    def test_consistent_hashing_distribution(self):
        """Test that consistent hashing distributes keys reasonably."""
        # Add multiple servers
        for i in range(5):
            server = Server(f"server{i}", "localhost", 8000 + i)
            self.load_balancer.add_server(server)
        
        # Test distribution of many keys
        distribution = {}
        for i in range(1000):
            key = f"key_{i}"
            server = self.load_balancer.get_server(key)
            if server:
                distribution[server.name] = distribution.get(server.name, 0) + 1
        
        # Each server should get some requests (rough distribution)
        self.assertEqual(len(distribution), 5)
        for count in distribution.values():
            self.assertGreater(count, 100)  # At least 100 requests per server
            
    def test_add_duplicate_server(self):
        """Test adding a server with duplicate name."""
        self.load_balancer.add_server(self.server1)
        self.assertEqual(len(self.load_balancer.servers), 1)
        
        # Add server with same name but different config
        duplicate_server = Server("server1", "localhost", 9001)
        self.load_balancer.add_server(duplicate_server)
        
        # Should still have only one server, but config should be updated
        self.assertEqual(len(self.load_balancer.servers), 1)
        server = self.load_balancer.servers["server1"]
        self.assertEqual(server.port, 9001)  # Should be updated


class TestServer(unittest.TestCase):
    """Test cases for Server."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = Server("test-server", "localhost", 8080, weight=2)
    
    def test_server_creation(self):
        """Test server creation."""
        self.assertEqual(self.server.name, "test-server")
        self.assertEqual(self.server.address, "localhost")
        self.assertEqual(self.server.port, 8080)
        self.assertEqual(self.server.weight, 2)
        self.assertTrue(self.server.healthy)
        self.assertEqual(self.server.request_count, 0)
        self.assertEqual(self.server.error_count, 0)
        
    def test_server_url(self):
        """Test server URL generation."""
        expected_url = "http://localhost:8080"
        self.assertEqual(self.server.get_url(), expected_url)
        
    def test_record_request(self):
        """Test recording requests."""
        self.server.record_request(0.1)
        self.assertEqual(self.server.request_count, 1)
        self.assertEqual(len(self.server.response_times), 1)
        self.assertEqual(self.server.response_times[0], 0.1)
        
        # Record request without response time
        self.server.record_request()
        self.assertEqual(self.server.request_count, 2)
        self.assertEqual(len(self.server.response_times), 1)
        
    def test_record_error(self):
        """Test recording errors."""
        self.server.record_error()
        self.assertEqual(self.server.error_count, 1)
        
    def test_average_response_time(self):
        """Test average response time calculation."""
        # No response times recorded
        self.assertEqual(self.server.get_average_response_time(), 0.0)
          # Record some response times
        self.server.record_request(0.1)
        self.server.record_request(0.2)
        self.server.record_request(0.3)
        
        expected_avg = (0.1 + 0.2 + 0.3) / 3
        self.assertAlmostEqual(self.server.get_average_response_time(), expected_avg, places=5)
        
    def test_response_times_limit(self):
        """Test that response times list is limited."""
        # Record more than 100 response times
        for i in range(150):
            self.server.record_request(0.1)
        
        # Should only keep the most recent 100
        self.assertEqual(len(self.server.response_times), 100)
        
    def test_server_string_representation(self):
        """Test server string representation."""
        expected_str = "Server(test-server, localhost:8080, healthy)"
        self.assertEqual(str(self.server), expected_str)
        
        self.server.healthy = False
        expected_str = "Server(test-server, localhost:8080, unhealthy)"
        self.assertEqual(str(self.server), expected_str)


if __name__ == '__main__':
    unittest.main()