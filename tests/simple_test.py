#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.consistent_hash import ConsistentHash
from utils.hashing import fnv1a_hash

def test_basic_functionality():
    print("Testing ConsistentHash basic functionality...")
    
    # Create hash ring
    ch = ConsistentHash(fnv1a_hash)
    
    # Add nodes
    ch.add_node('node1')
    ch.add_node('node2')
    ch.add_node('node3')
    
    # Test node selection
    node1 = ch.get_node('key1')
    node2 = ch.get_node('key2')
    node3 = ch.get_node('key3')
    
    print(f"Key1 -> {node1}")
    print(f"Key2 -> {node2}")
    print(f"Key3 -> {node3}")
    
    # Test consistency
    assert ch.get_node('key1') == node1, "Consistency check failed"
    
    # Test multiple nodes
    nodes = ch.get_nodes('key1', 2)
    print(f"Multiple nodes for key1: {nodes}")
    
    print("Basic functionality tests passed!")
    
def test_load_balancer():
    print("\nTesting LoadBalancer...")
    
    from core.load_balancer import LoadBalancer, Server
    from utils.hashing import get_hash_function
      # Create load balancer
    hash_func = get_hash_function('md5')
    lb = LoadBalancer(hash_func)
    
    # Add servers
    server1 = Server("server1", "localhost", 8001)
    server2 = Server("server2", "localhost", 8002)
    server3 = Server("server3", "localhost", 8003)
    
    lb.add_server(server1)
    lb.add_server(server2) 
    lb.add_server(server3)
    
    # Test server selection
    selected = lb.get_server("test_key")
    print(f"Selected server: {selected}")
    
    # Test stats
    stats = lb.get_stats()
    print(f"Stats: {stats}")
    
    print("LoadBalancer tests passed!")

if __name__ == "__main__":
    test_basic_functionality()
    test_load_balancer()
    print("\nAll tests completed successfully!")
