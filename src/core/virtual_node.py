"""
Virtual Node Implementation

This module provides the virtual node functionality for the consistent hashing algorithm.
Virtual nodes are used to improve the distribution of keys across the nodes in the system.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class VirtualNode:
    """
    Represents a virtual node in the consistent hashing ring.
    
    A single physical node can have multiple virtual nodes associated with it,
    which helps in achieving a more balanced distribution of keys.
    """
    
    # The name/ID of the physical node this virtual node represents
    physical_node: str
    
    # A unique identifier for this virtual node
    id: int
    
    # The computed hash value of this virtual node in the hash ring
    hash_value: int
    
    # Optional weight for this virtual node (can be used for weighted distribution)
    weight: int = 1
    
    # Optional metadata that can be associated with the node
    metadata: Optional[dict] = None
    
    def __str__(self) -> str:
        """String representation of a virtual node."""
        return f"VirtualNode(physical={self.physical_node}, id={self.id}, hash={self.hash_value})"
    
    def __eq__(self, other: Any) -> bool:
        """
        Equality check for virtual nodes.
        
        Two virtual nodes are considered equal if they represent the same physical node
        and have the same virtual node ID.
        """
        if not isinstance(other, VirtualNode):
            return False
        return (self.physical_node == other.physical_node and 
                self.id == other.id)
    
    def __hash__(self) -> int:
        """Hash function for the virtual node."""
        return hash((self.physical_node, self.id))


class VirtualNodeManager:
    """
    Manages the virtual nodes for physical nodes in the system.
    
    This class is responsible for creating, tracking, and removing virtual nodes
    associated with physical nodes.
    """
    
    def __init__(self, hash_func):
        """
        Initialize a new VirtualNodeManager.
        
        Args:
            hash_func: A function that takes a string and returns an integer hash value.
        """
        self.hash_func = hash_func
        self.physical_to_virtual = {}  # Maps physical node name to list of virtual nodes
        self.virtual_nodes = {}  # Maps hash value to VirtualNode object
    
    def create_virtual_nodes(self, physical_node: str, count: int = 100, weight: int = 1) -> list:
        """
        Create virtual nodes for a physical node.
        
        Args:
            physical_node: The name/ID of the physical node.
            count: The number of virtual nodes to create.
            weight: The weight to assign to each virtual node.
            
        Returns:
            List of created VirtualNode objects.
        """
        virtual_nodes = []
        
        # Initialize the list if this is a new physical node
        if physical_node not in self.physical_to_virtual:
            self.physical_to_virtual[physical_node] = []
        
        # Create the specified number of virtual nodes
        for i in range(count):
            # Create a unique string for this virtual node
            virtual_node_str = f"{physical_node}:{i}"
            
            # Compute the hash value for this virtual node
            hash_value = self.hash_func(virtual_node_str)
            
            # Create the virtual node object
            v_node = VirtualNode(
                physical_node=physical_node,
                id=i,
                hash_value=hash_value,
                weight=weight
            )
            
            # Store the virtual node
            self.virtual_nodes[hash_value] = v_node
            self.physical_to_virtual[physical_node].append(v_node)
            virtual_nodes.append(v_node)
        
        return virtual_nodes
    
    def remove_virtual_nodes(self, physical_node: str) -> None:
        """
        Remove all virtual nodes associated with a physical node.
        
        Args:
            physical_node: The name/ID of the physical node.
        """
        if physical_node not in self.physical_to_virtual:
            return
        
        # Remove each virtual node from the virtual_nodes dict
        for v_node in self.physical_to_virtual[physical_node]:
            if v_node.hash_value in self.virtual_nodes:
                del self.virtual_nodes[v_node.hash_value]
        
        # Remove the physical node from the tracking dict
        del self.physical_to_virtual[physical_node]
    
    def get_virtual_nodes(self, physical_node: str) -> list:
        """
        Get all virtual nodes associated with a physical node.
        
        Args:
            physical_node: The name/ID of the physical node.
            
        Returns:
            List of VirtualNode objects associated with the physical node,
            or an empty list if the physical node doesn't exist.
        """
        return self.physical_to_virtual.get(physical_node, [])