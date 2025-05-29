"""
Consistent Hashing Implementation

This module implements the consistent hashing algorithm with support for virtual nodes.
Consistent hashing provides a distribution mechanism that minimizes reorganization when
nodes are added or removed from the system.
"""

import bisect
from typing import Dict, List, Optional, Any, Callable


class ConsistentHash:
    """
    A consistent hashing implementation that supports virtual nodes.
    
    This class provides methods to add and remove nodes from the hash ring,
    as well as to find the appropriate node for a given key.
    """
    
    def __init__(self, hash_func: Callable[[str], int]):
        """
        Initialize a new ConsistentHash instance.
        
        Args:
            hash_func: A function that takes a string and returns an integer hash value.
        """
        self.hash_func = hash_func
        self.ring = {}  # Hash value -> Node mapping
        self.sorted_keys = []  # Sorted list of hash values for binary search
        self.nodes = {}  # Node name -> List of hash values
    
    def add_node(self, node_name: str, weight: int = 1) -> None:
        """
        Add a node to the hash ring.
        
        Args:
            node_name: A unique identifier for the node.
            weight: The weight of the node which determines the number of virtual nodes.
                   Higher weight means more virtual nodes and thus more responsibility.
        """
        if node_name in self.nodes:
            return  # Node already exists
        
        self.nodes[node_name] = []
        
        # Create virtual nodes based on weight
        for i in range(weight * 100):  # 100 virtual nodes per weight unit
            virtual_node_name = f"{node_name}:{i}"
            hash_value = self.hash_func(virtual_node_name)
            
            self.ring[hash_value] = node_name
            self.nodes[node_name].append(hash_value)
            bisect.insort(self.sorted_keys, hash_value)
    
    def remove_node(self, node_name: str) -> None:
        """
        Remove a node and all its virtual nodes from the hash ring.
        
        Args:
            node_name: The identifier of the node to remove.
        """
        if node_name not in self.nodes:
            return  # Node doesn't exist
        
        # Remove all virtual nodes
        for hash_value in self.nodes[node_name]:
            self.ring.pop(hash_value)
            self.sorted_keys.remove(hash_value)
        
        # Remove the node from nodes dict
        self.nodes.pop(node_name)
    
    def get_node(self, key: str) -> Optional[str]:
        """
        Find the node responsible for the given key.
        
        Args:
            key: The key to look up.
            
        Returns:
            The name of the node responsible for the key,
            or None if no nodes exist.
        """
        if not self.ring:
            return None
        
        hash_value = self.hash_func(key)
        
        # Find the first point in the ring >= hash_value
        idx = bisect.bisect_left(self.sorted_keys, hash_value) % len(self.sorted_keys)
        return self.ring[self.sorted_keys[idx]]
    
    def get_nodes(self, key: str, count: int) -> List[str]:
        """
        Find multiple nodes responsible for the given key.
        Useful for replication or when the preferred node is unavailable.
        
        Args:
            key: The key to look up.
            count: The number of nodes to return.
            
        Returns:
            A list of node names responsible for the key.
        """
        if not self.ring or count <= 0:
            return []
        
        if count > len(set(self.ring.values())):
            count = len(set(self.ring.values()))
        
        hash_value = self.hash_func(key)
        idx = bisect.bisect_left(self.sorted_keys, hash_value) % len(self.sorted_keys)
        
        unique_nodes = []
        visited = set()
        
        for i in range(len(self.sorted_keys)):
            node = self.ring[self.sorted_keys[(idx + i) % len(self.sorted_keys)]]
            if node not in visited:
                visited.add(node)
                unique_nodes.append(node)
                if len(unique_nodes) >= count:
                    break
        
        return unique_nodes