"""
Tests for the VirtualNode class.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from unittest.mock import Mock
from core.virtual_node import VirtualNode
from core.load_balancer import Server


class TestVirtualNode(unittest.TestCase):
    """Test cases for VirtualNode."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = Server("test-server", "localhost", 8080)
        self.virtual_node = VirtualNode("test-server", 0, 12345)
    
    def test_virtual_node_creation(self):
        """Test virtual node creation."""
        self.assertEqual(self.virtual_node.physical_node, "test-server")
        self.assertEqual(self.virtual_node.id, 0)
        self.assertEqual(self.virtual_node.hash_value, 12345)
        
    def test_virtual_node_equality(self):
        """Test virtual node equality."""
        other_virtual_node = VirtualNode("test-server", 0, 12345)
        self.assertEqual(self.virtual_node, other_virtual_node)
        
        different_virtual_node = VirtualNode("test-server", 1, 12346)
        self.assertNotEqual(self.virtual_node, different_virtual_node)
        
    def test_virtual_node_hash(self):
        """Test virtual node hashing."""
        hash1 = hash(self.virtual_node)
        hash2 = hash(VirtualNode("test-server", 0, 12345))
        self.assertEqual(hash1, hash2)
        
    def test_virtual_node_string_representation(self):
        """Test virtual node string representation."""
        expected_str = "VirtualNode(physical=test-server, id=0, hash=12345)"
        self.assertEqual(str(self.virtual_node), expected_str)
        
    def test_virtual_node_with_different_servers(self):
        """Test virtual nodes with different servers."""
        vnode1 = VirtualNode("server1", 0, 12345)
        vnode2 = VirtualNode("server2", 0, 12345)
        
        self.assertNotEqual(vnode1, vnode2)
        
    def test_virtual_node_with_same_server_different_id(self):
        """Test virtual nodes with same server but different virtual IDs."""
        vnode1 = VirtualNode("test-server", 0, 12345)
        vnode2 = VirtualNode("test-server", 1, 12346)
        
        self.assertNotEqual(vnode1, vnode2)
        
    def test_virtual_node_weight(self):
        """Test virtual node weight functionality."""
        weighted_node = VirtualNode("test-server", 0, 12345, weight=3)
        self.assertEqual(weighted_node.weight, 3)
        
        # Default weight should be 1
        self.assertEqual(self.virtual_node.weight, 1)


if __name__ == '__main__':
    unittest.main()
