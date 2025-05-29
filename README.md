# Load Balancer with Consistent Hashing

A high-performance load balancer implementation using consistent hashing algorithm to distribute requests across multiple servers. This implementation provides efficient load distribution, automatic failover, and health monitoring capabilities.

## Features

- **Consistent Hashing**: Minimizes reorganization when servers are added or removed
- **Virtual Nodes**: Improves load distribution by creating multiple virtual nodes per server
- **Health Monitoring**: Automatic health checks with configurable intervals
- **Weighted Load Balancing**: Support for different server weights
- **RESTful API**: HTTP API for management and monitoring
- **Real-time Metrics**: Request count, error rates, and response time tracking
- **Automatic Failover**: Unhealthy servers are automatically removed from rotation

## Architecture

The load balancer consists of several key components:

- **Load Balancer Core**: Main orchestration logic
- **Consistent Hash Ring**: Distributes requests using consistent hashing
- **Virtual Nodes**: Improves distribution uniformity
- **Health Check System**: Monitors server availability
- **API Server**: RESTful interface for management

For detailed architecture information, see [docs/architecture.md](docs/architecture.md).

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Loadbalancer
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

1. **Configure the load balancer** by editing `config.json`:
```json
{
  "servers": [
    {"name": "server1", "address": "192.168.1.10", "port": 8080, "weight": 1},
    {"name": "server2", "address": "192.168.1.11", "port": 8080, "weight": 2}
  ],
  "health_check": {
    "interval": 30,
    "timeout": 5,
    "path": "/health"
  },
  "api": {
    "host": "localhost",
    "port": 9090
  }
}
```

2. **Start the load balancer**:
```bash
python src/main.py
```

3. **Test the load balancer** by sending requests to the configured endpoint.

## Configuration

The load balancer is configured via the `config.json` file:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `servers` | List of backend servers | Required |
| `health_check.interval` | Health check interval (seconds) | 30 |
| `health_check.timeout` | Health check timeout (seconds) | 5 |
| `health_check.path` | Health check endpoint path | `/health` |
| `api.host` | API server host | `localhost` |
| `api.port` | API server port | 9090 |

## API Reference

### Server Management

- `GET /api/servers` - List all servers
- `POST /api/servers` - Add a new server
- `DELETE /api/servers/{name}` - Remove a server
- `PUT /api/servers/{name}/weight` - Update server weight

### Health and Monitoring

- `GET /api/health` - Load balancer health status
- `GET /api/metrics` - Performance metrics
- `GET /api/ring` - Hash ring visualization

### Load Balancing

- `POST /api/route` - Route a request through the load balancer

For detailed API documentation, see [docs/usage.md](docs/usage.md).

## Usage Examples

### Adding a Server
```bash
curl -X POST http://localhost:9090/api/servers \
  -H "Content-Type: application/json" \
  -d '{"name": "server3", "address": "192.168.1.12", "port": 8080, "weight": 1}'
```

### Routing a Request
```bash
curl -X POST http://localhost:9090/api/route \
  -H "Content-Type: application/json" \
  -d '{"key": "user123", "path": "/api/data"}'
```

### Checking Metrics
```bash
curl http://localhost:9090/api/metrics
```

## Development

### Project Structure

```
Loadbalancer/
├── src/
│   ├── main.py                 # Application entry point
│   ├── api/                    # REST API implementation
│   │   ├── server.py          # API server
│   │   └── routes.py          # API routes
│   ├── core/                   # Core load balancing logic
│   │   ├── load_balancer.py   # Main load balancer class
│   │   ├── consistent_hash.py # Consistent hashing implementation
│   │   └── virtual_node.py    # Virtual node management
│   └── utils/                  # Utility functions
│       ├── hashing.py         # Hash functions
│       └── health_check.py    # Health monitoring
├── tests/                      # Unit tests
├── docs/                       # Documentation
├── config.json                 # Configuration file
└── requirements.txt           # Python dependencies
```

### Running Tests

Execute the test suite:
```bash
python -m unittest discover tests/ -v
```

Run individual test modules:
```bash
python -m unittest tests.test_consistent_hash -v
python -m unittest tests.test_load_balancer -v
python -m unittest tests.test_virtual_node -v
```

### Code Style

This project follows PEP 8 style guidelines. Format code using:
```bash
black src/ tests/
```

Lint code using:
```bash
flake8 src/ tests/
```

## Algorithm Details

### Consistent Hashing

The load balancer uses consistent hashing to distribute requests. Key benefits:

- **Minimal Reorganization**: Only K/n keys are reassigned when adding/removing servers (K = total keys, n = number of servers)
- **Load Distribution**: Virtual nodes ensure more uniform distribution
- **Scalability**: Easy to add or remove servers without major disruption

### Virtual Nodes

Each physical server is represented by multiple virtual nodes on the hash ring:
- Default: 100 virtual nodes per weight unit
- Higher weight servers get more virtual nodes
- Improves load distribution uniformity

## Performance

Typical performance characteristics:
- **Lookup Time**: O(log n) where n is the number of virtual nodes
- **Memory Usage**: O(v) where v is the total number of virtual nodes
- **Throughput**: 10,000+ requests per second (depends on backend servers)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Ensure all tests pass: `python -m unittest discover tests/ -v`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support:
- Create an issue in the GitHub repository
- Check the [documentation](docs/) for detailed information
- Review the [usage examples](docs/usage.md)

## Roadmap

- [ ] WebSocket support for real-time monitoring
- [ ] Redis integration for distributed state
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests
- [ ] Advanced load balancing algorithms (least connections, response time)
- [ ] SSL/TLS termination
- [ ] Rate limiting
- [ ] Circuit breaker pattern