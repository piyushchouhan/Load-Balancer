"""
Hashing Utilities

This module provides various hashing functions that can be used with the consistent hashing algorithm.
Different hashing strategies have different properties in terms of distribution and performance.
"""

import hashlib
import zlib
import struct
try:
    import mmh3  # MurmurHash implementation
except ImportError:
    # Make mmh3 optional since it requires installation
    mmh3 = None


def simple_hash(key: str) -> int:
    """
    A simple hash function that sums character ordinals and does modulo.
    
    Not recommended for production use due to poor distribution, but included for educational purposes.
    
    Args:
        key: The string to hash.
        
    Returns:
        A non-negative integer hash value.
    """
    hash_val = 0
    for char in key:
        hash_val += ord(char)
    return hash_val


def djb2_hash(key: str) -> int:
    """
    DJB2 hash function, known for its simplicity and good distribution.
    
    Args:
        key: The string to hash.
        
    Returns:
        A non-negative integer hash value.
    """
    hash_val = 5381
    for char in key:
        hash_val = ((hash_val << 5) + hash_val) + ord(char)  # hash * 33 + c
    return hash_val & 0xFFFFFFFF  # Ensure it's a 32-bit unsigned int


def fnv1a_hash(key: str) -> int:
    """
    FNV-1a hash function, which has good distribution and performance.
    
    Args:
        key: The string to hash.
        
    Returns:
        A non-negative integer hash value.
    """
    FNV_PRIME = 16777619
    FNV_OFFSET_BASIS = 2166136261
    
    hash_val = FNV_OFFSET_BASIS
    for char in key:
        hash_val = hash_val ^ ord(char)
        hash_val = (hash_val * FNV_PRIME) & 0xFFFFFFFF
    
    return hash_val


def md5_hash(key: str) -> int:
    """
    MD5-based hash function, which provides good distribution but is slower.
    
    Args:
        key: The string to hash.
        
    Returns:
        A non-negative integer hash value based on the first 4 bytes of the MD5 hash.
    """
    md5 = hashlib.md5()
    md5.update(key.encode('utf-8'))
    # Take first 4 bytes and convert to int
    return struct.unpack("I", md5.digest()[:4])[0]


def sha1_hash(key: str) -> int:
    """
    SHA1-based hash function, which provides good distribution but is slower than MD5.
    
    Args:
        key: The string to hash.
        
    Returns:
        A non-negative integer hash value based on the first 4 bytes of the SHA1 hash.
    """
    sha1 = hashlib.sha1()
    sha1.update(key.encode('utf-8'))
    # Take first 4 bytes and convert to int
    return struct.unpack("I", sha1.digest()[:4])[0]


def crc32_hash(key: str) -> int:
    """
    CRC32-based hash function, which is faster than cryptographic hashes.
    
    Args:
        key: The string to hash.
        
    Returns:
        A non-negative integer hash value.
    """
    return zlib.crc32(key.encode('utf-8')) & 0xFFFFFFFF


def murmur3_hash(key: str) -> int:
    """
    MurmurHash3 hash function, which has excellent distribution and performance.
    Recommended for production use.
    
    Args:
        key: The string to hash.
        
    Returns:
        A non-negative integer hash value.
    """
    if mmh3 is None:
        raise ImportError("mmh3 module not found. Install with 'pip install mmh3'")
    # Use seed=0 for consistency
    return mmh3.hash(key, seed=0) & 0xFFFFFFFF


def jump_hash(key: str, bucket_count: int) -> int:
    """
    Jump Consistent Hash, a fast, minimal memory, consistent hashing algorithm.
    Developed by Google, it maps keys to buckets directly without a ring structure.
    
    Note: This differs from other hash functions as it directly outputs a bucket number
    rather than a hash value that needs to be mapped to a bucket.
    
    Args:
        key: The string to hash.
        bucket_count: The number of buckets.
        
    Returns:
        A bucket number in the range [0, bucket_count-1].
    """
    if bucket_count <= 0:
        raise ValueError("Bucket count must be positive")
    
    # Convert string to a 64-bit integer using another hash function
    key_hash = fnv1a_hash(key)
    
    # Jump hash algorithm
    b = -1
    j = 0
    while j < bucket_count:
        b = j
        key_hash = ((key_hash * 2862933555777941757) + 1) & 0xFFFFFFFFFFFFFFFF
        j = int(float(b + 1) * (float(1 << 31) / float((key_hash >> 33) + 1)))
    
    return b


def get_hash_function(name: str):
    """
    Get a hash function by name.
    
    Args:
        name: The name of the hash function to get.
        
    Returns:
        A function that takes a string and returns an integer hash value.
        
    Raises:
        ValueError: If the hash function is not found.
    """
    hash_functions = {
        'simple': simple_hash,
        'djb2': djb2_hash,
        'fnv1a': fnv1a_hash,
        'md5': md5_hash,
        'sha1': sha1_hash,
        'crc32': crc32_hash,
    }
    
    # Add murmur3 if available
    if mmh3 is not None:
        hash_functions['murmur3'] = murmur3_hash
    
    if name not in hash_functions:
        raise ValueError(f"Hash function '{name}' not found. Available functions: {list(hash_functions.keys())}")
    
    return hash_functions[name]