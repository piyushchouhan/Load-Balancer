"""
Unit tests for ConsistentHash implementation.
"""

import unittest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.consistent_hash import ConsistentHash
from utils.hashing import fnv1a_hash, djb2_hash


class TestConsistentHash(unittest.TestCase):
    """Test cases for ConsistentHash class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.hash_func = fnv1a_hash
        self.consistent_hash = ConsistentHash(self.hash_func)
    
    def test_empty_ring(self):
        """Test behavior with empty ring."""
        self.assertIsNone(self.consistent_hash.get_node("test_key"))        
        self.assertEqual(self.consistent_hash.get_nodes("test_key", 3), [])
        
    def test_add_single_node(self):
        """Test adding a single node to the ring."""
        self.consistent_hash.add_node("node1")
        
        # Ring should not be empty
        self.assertGreater(len(self.consistent_hash.ring), 0)
        self.assertIn("node1", self.consistent_hash.nodes)
        
        # Should return the only node for any key
        self.assertEqual(self.consistent_hash.get_node("test_key"), "node1")
        self.assertEqual(self.consistent_hash.get_nodes("test_key", 1), ["node1"])
        
    def test_add_multiple_nodes(self):
        """Test adding multiple nodes to the ring."""
        nodes = ["node1", "node2", "node3"]
        for node in nodes:
            self.consistent_hash.add_node(node)
        
        # All nodes should be in the ring
        for node in nodes:
            self.assertIn(node, self.consistent_hash.nodes)
        
        # Should return valid nodes for keys
        for key in ["key1", "key2", "key3"]:
            node = self.consistent_hash.get_node(key)
            self.assertIn(node, nodes)

    def test_node_weights(self):
        """Test that node weights affect virtual node count."""
        self.consistent_hash.add_node("light_node", weight=1)
        self.consistent_hash.add_node("heavy_node", weight=3)
        
        light_virtual_nodes = len(self.consistent_hash.nodes["light_node"])
        heavy_virtual_nodes = len(self.consistent_hash.nodes["heavy_node"])
        
        # Heavy node should have more virtual nodes
        self.assertGreater(heavy_virtual_nodes, light_virtual_nodes)
        self.assertEqual(heavy_virtual_nodes, light_virtual_nodes * 3)

    def test_remove_node(self):
        """Test removing a node from the ring."""
        # Add nodes
        self.consistent_hash.add_node("node1")
        self.consistent_hash.add_node("node2")
        
        # Remove one node
        self.consistent_hash.remove_node("node1")
        
        # Node should be removed
        self.assertNotIn("node1", self.consistent_hash.nodes)
        self.assertIn("node2", self.consistent_hash.nodes)
        
        # Keys should now map to remaining node
        self.assertEqual(self.consistent_hash.get_node("test_key"), "node2")

    def test_remove_nonexistent_node(self):
        """Test removing a node that doesn't exist."""
        self.consistent_hash.add_node("node1")
        
        # Should not raise an error
        self.consistent_hash.remove_node("nonexistent")
        
        # Original node should still be there
        self.assertIn("node1", self.consistent_hash.nodes)

    def test_get_multiple_nodes(self):
        """Test getting multiple nodes for replication."""
        nodes = ["node1", "node2", "node3", "node4"]
        for node in nodes:
            self.consistent_hash.add_node(node)
        
        # Test getting multiple nodes
        result_nodes = self.consistent_hash.get_nodes("test_key", 3)
        
        self.assertEqual(len(result_nodes), 3)
        self.assertEqual(len(set(result_nodes)), 3)  # All unique
        
        # All returned nodes should be valid
        for node in result_nodes:
            self.assertIn(node, nodes)

    def test_consistent_mapping(self):
        """Test that the same key always maps to the same node."""
        nodes = ["node1", "node2", "node3"]
        for node in nodes:
            self.consistent_hash.add_node(node)
        
        key = "consistent_key"
        first_result = self.consistent_hash.get_node(key)
        
        # Multiple calls should return the same result
        for _ in range(10):
            self.assertEqual(self.consistent_hash.get_node(key), first_result)
    
    def test_distribution_after_node_addition(self):
        """Test that adding a node doesn't drastically change key distribution."""
        # Start with two nodes
        self.consistent_hash.add_node("node1")
        self.consistent_hash.add_node("node2")
        
        # Record where keys map initially
        keys = [f"key_{i}" for i in range(100)]
        initial_mapping = {key: self.consistent_hash.get_node(key) for key in keys}
        
        # Add a third node
        self.consistent_hash.add_node("node3")
        
        # Check how many keys changed
        changed_keys = 0
        for key in keys:
            if self.consistent_hash.get_node(key) != initial_mapping[key]:
                changed_keys += 1
          # Should be roughly 1/3 of keys (not too many changed)
        self.assertLess(changed_keys, len(keys) * 0.5)  # Less than 50% changed
    
    def test_different_hash_functions(self):
        """Test that different hash functions work."""
        hash1 = ConsistentHash(fnv1a_hash)
        hash2 = ConsistentHash(djb2_hash)
        
        # Add same nodes to both
        for hash_ring in [hash1, hash2]:
            hash_ring.add_node("node1")
            hash_ring.add_node("node2")
          # Both should work (may give different results due to different hash functions)
        key = "test_key"
        result1 = hash1.get_node(key)
        result2 = hash2.get_node(key)
        
        self.assertIn(result1, ["node1", "node2"])
        self.assertIn(result2, ["node1", "node2"])

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test with empty key
        self.consistent_hash.add_node("node1")
        self.assertEqual(self.consistent_hash.get_node(""), "node1")
        
        # Test with unicode key
        self.assertEqual(self.consistent_hash.get_node("测试"), "node1")
        
        # Test get_nodes with zero count
        self.assertEqual(self.consistent_hash.get_nodes("key", 0), [])
        
        # Test get_nodes with count larger than available nodes
        result = self.consistent_hash.get_nodes("key", 10)
        self.assertEqual(len(result), 1)  # Only one node available


if __name__ == "__main__":
    unittest.main()