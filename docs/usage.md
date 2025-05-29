# Load Balancer Usage Guide

This document provides comprehensive instructions on how to use the Load Balancer system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [Running the System](#running-the-system)
4. [API Reference](#api-reference)
5. [Testing](#testing)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Python 3.7 or higher
- Required packages (install with: `pip install -r requirements.txt`)

### Basic Setup

1. **Clone or extract the project:**
   ```bash
   cd f:\Loadbalancer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start test backend servers:**
   ```bash
   python test_servers.py
   ```
   This starts 3 test servers on ports 8001, 8002, and 8003.

4. **Start the load balancer:**
   ```bash
   python src/main.py
   ```
   The load balancer will start on port 8080 by default.

5. **Test the system:**
   ```bash
   curl http://localhost:8080/
   ```

## Configuration

The load balancer is configured via `config.json`:

```json
{
    "load_balancer": {
        "port": 8080,
        "host": "localhost",
        "algorithm": "consistent_hash"
    },
    "servers": [
        {"host": "localhost", "port": 8001, "weight": 1},
        {"host": "localhost", "port": 8002, "weight": 1},
        {"host": "localhost", "port": 8003, "weight": 2}
    ],
    "health_check": {
        "enabled": true,
        "interval": 30,
        "timeout": 5,
        "retries": 3
    },
    "consistent_hash": {
        "virtual_nodes": 150,
        "hash_function": "fnv1a"
    }
}
```

### Configuration Options

#### Load Balancer Settings
- `port`: Port for the load balancer (default: 8080)
- `host`: Host address (default: "localhost")
- `algorithm`: Load balancing algorithm ("consistent_hash", "round_robin", etc.)

#### Server Settings
- `host`: Backend server hostname/IP
- `port`: Backend server port
- `weight`: Server weight for load distribution (higher = more traffic)

#### Health Check Settings
- `enabled`: Enable/disable health monitoring
- `interval`: Health check interval in seconds
- `timeout`: Request timeout for health checks
- `retries`: Number of retries before marking server as unhealthy

#### Consistent Hash Settings
- `virtual_nodes`: Number of virtual nodes per server (affects distribution granularity)
- `hash_function`: Hash function to use ("fnv1a", "djb2", "md5", "sha1")

## Running the System

### Using the Main Application

```bash
python src/main.py
```

### Using the Start Script

```bash
python start.py
```

### Using PowerShell Demo Script

```powershell
.\demo.ps1
```

This script:
1. Starts test backend servers
2. Starts the load balancer
3. Runs sample requests
4. Shows system statistics

### Environment Variables

You can override configuration using environment variables:

```bash
export LB_PORT=9000
export LB_HOST=0.0.0.0
python src/main.py
```

## API Reference

### Load Balancing Endpoint

**GET /** or **GET /path/to/resource**
- Forwards requests to backend servers using consistent hashing
- Returns response from the selected backend server
- Headers and query parameters are preserved

### Management Endpoints

#### Get System Statistics
```http
GET /api/stats
```

**Response:**
```json
{
    "total_requests": 150,
    "successful_requests": 148,
    "failed_requests": 2,
    "error_rate": 1.33,
    "servers": {
        "localhost:8001": {
            "requests": 45,
            "errors": 0,
            "status": "healthy"
        },
        "localhost:8002": {
            "requests": 52,
            "errors": 1,
            "status": "healthy"
        },
        "localhost:8003": {
            "requests": 51,
            "errors": 1,
            "status": "healthy"
        }
    }
}
```

#### Get Server Status
```http
GET /api/servers
```

**Response:**
```json
{
    "servers": [
        {
            "host": "localhost",
            "port": 8001,
            "weight": 1,
            "status": "healthy",
            "requests": 45,
            "errors": 0
        },
        {
            "host": "localhost",
            "port": 8002,
            "weight": 1,
            "status": "healthy",
            "requests": 52,
            "errors": 1
        }
    ]
}
```

#### Get Health Status
```http
GET /api/health
```

**Response:**
```json
{
    "status": "healthy",
    "uptime": 3600,
    "version": "1.0.0"
}
```

### Adding/Removing Servers Dynamically

#### Add Server
```http
POST /api/servers
Content-Type: application/json

{
    "host": "localhost",
    "port": 8004,
    "weight": 1
}
```

#### Remove Server
```http
DELETE /api/servers/localhost:8004
```

## Testing

### Unit Tests

Run all unit tests:
```bash
python -m unittest discover tests -v
```

Run specific test file:
```bash
python -m unittest tests.test_consistent_hash -v
```

### Integration Tests

Run the simple integration test:
```bash
python simple_test.py
```

### Load Testing

Use the included example script:
```bash
python example.py
```

This script demonstrates:
- Consistent hashing behavior
- Load distribution
- Error handling
- Statistics collection

### Manual Testing

1. **Start the system:**
   ```bash
   python test_servers.py &
   python src/main.py &
   ```

2. **Send test requests:**
   ```bash
   for i in {1..10}; do
       curl http://localhost:8080/test$i
   done
   ```

3. **Check statistics:**
   ```bash
   curl http://localhost:8080/api/stats
   ```

## Advanced Usage

### Custom Hash Functions

You can implement custom hash functions by extending the `utils/hashing.py` module:

```python
def custom_hash(data: str) -> int:
    """Custom hash function implementation."""
    # Your implementation here
    return hash_value

# Update config.json:
{
    "consistent_hash": {
        "hash_function": "custom"
    }
}
```

### Custom Load Balancing Algorithms

Extend the `core/load_balancer.py` to implement new algorithms:

```python
class CustomLoadBalancer(LoadBalancer):
    def select_server(self, key: str) -> Optional[Server]:
        """Custom server selection logic."""
        # Your implementation here
        return selected_server
```

### Monitoring Integration

The system provides hooks for monitoring integration:

```python
from src.core.load_balancer import LoadBalancer

def on_request(server, success, response_time):
    """Custom monitoring callback."""
    # Send metrics to your monitoring system
    pass

# Configure callback
load_balancer.set_monitoring_callback(on_request)
```

### SSL/TLS Support

To enable HTTPS:

1. **Generate certificates:**
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

2. **Update configuration:**
   ```json
   {
       "load_balancer": {
           "ssl": {
               "enabled": true,
               "cert_file": "cert.pem",
               "key_file": "key.pem"
           }
       }
   }
   ```

### High Availability Setup

For production deployment:

1. **Multiple Load Balancer Instances:**
   ```bash
   # Instance 1
   LB_PORT=8080 python src/main.py &
   
   # Instance 2
   LB_PORT=8081 python src/main.py &
   ```

2. **Use a reverse proxy (nginx):**
   ```nginx
   upstream load_balancers {
       server localhost:8080;
       server localhost:8081;
   }
   
   server {
       listen 80;
       location / {
           proxy_pass http://load_balancers;
       }
   }
   ```

## Troubleshooting

### Common Issues

#### 1. Import Errors
**Problem:** `ModuleNotFoundError: No module named 'core'`

**Solution:**
```bash
# Ensure you're in the correct directory
cd f:\Loadbalancer

# Run with Python module syntax
python -m src.main

# Or add to PYTHONPATH
set PYTHONPATH=f:\Loadbalancer\src;%PYTHONPATH%
```

#### 2. Port Already in Use
**Problem:** `OSError: [WinError 10048] Only one usage of each socket address`

**Solution:**
```bash
# Find and kill process using the port
netstat -ano | findstr :8080
taskkill /PID <process_id> /F

# Or use a different port
LB_PORT=9000 python src/main.py
```

#### 3. Backend Servers Not Responding
**Problem:** Health checks failing, servers marked as unhealthy

**Solution:**
1. Check if backend servers are running:
   ```bash
   curl http://localhost:8001/health
   ```

2. Verify configuration:
   ```json
   {
       "servers": [
           {"host": "localhost", "port": 8001}
       ]
   }
   ```

3. Check firewall settings

#### 4. Uneven Load Distribution
**Problem:** Some servers getting more traffic than others

**Solution:**
1. Adjust server weights in configuration
2. Increase virtual nodes count for better distribution:
   ```json
   {
       "consistent_hash": {
           "virtual_nodes": 300
       }
   }
   ```

#### 5. High Error Rate
**Problem:** Many requests failing

**Solution:**
1. Check server logs
2. Increase health check timeout:
   ```json
   {
       "health_check": {
           "timeout": 10,
           "retries": 5
       }
   }
   ```

### Logging and Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:
```bash
set LOG_LEVEL=DEBUG
python src/main.py
```

### Performance Tuning

1. **Optimize Virtual Nodes:**
   - More virtual nodes = better distribution but more memory
   - Recommended: 100-500 virtual nodes per server

2. **Adjust Health Check Frequency:**
   - More frequent checks = faster failure detection but more overhead
   - Recommended: 30-60 seconds for most applications

3. **Connection Pooling:**
   - Use connection pooling for backend connections
   - Configure appropriate timeouts

### Getting Help

1. **Check the logs** for error messages
2. **Verify configuration** syntax and values
3. **Test components individually** (hash function, health checks, etc.)
4. **Use the API endpoints** to monitor system state
5. **Run unit tests** to verify core functionality

For additional support, refer to the architecture documentation in `docs/architecture.md`.