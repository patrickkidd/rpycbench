# RPyC Bench - RPyC vs HTTP/REST Benchmark Suite

A comprehensive Python benchmark suite for comparing RPyC (Remote Python Call) with HTTP/REST performance across multiple dimensions.

## Features

- **Comprehensive Metrics**
  - Connection establishment time
  - Request/response latency (mean, median, P95, P99)
  - Upload and download bandwidth
  - System resource usage (CPU, memory)

- **Multiple Server Modes**
  - RPyC: Threaded server, Forking server
  - HTTP: Flask-based threaded server

- **Concurrent Client Testing**
  - Test performance with multiple simultaneous clients
  - Measure connection pooling effectiveness

- **Flexible Usage**
  - **Autonomous Mode**: Run complete benchmark suite standalone
  - **Context Managers**: Integrate benchmarks into your application code
  - Compare baseline performance vs. application overhead

## Installation

```bash
# Clone repository
git clone <repository-url>
cd rpycbench

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .
```

## Quick Start

### Autonomous Mode

Run the complete benchmark suite:

```bash
# Run all benchmarks with default settings
rpycbench

# Customize parameters
rpycbench --num-connections 200 --num-requests 2000 --num-concurrent-clients 20

# Save results to JSON
rpycbench --output results.json

# Skip specific tests
rpycbench --skip-rpyc-forking --skip-http
```

### Using as Context Managers

Integrate benchmarks into your application:

```python
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection

# Start server
with RPyCServer(host='localhost', port=18812, mode='threaded'):

    # Create benchmark context
    with BenchmarkContext(
        name="My App",
        protocol="rpyc",
        measure_latency=True,
        measure_bandwidth=True,
    ) as bench:

        # Your application code
        conn = create_rpyc_connection('localhost', 18812)

        for i in range(100):
            with bench.measure_request():
                result = conn.root.ping()
                bench.record_request(success=True)

        conn.close()

    # Get results
    metrics = bench.get_results()
    stats = metrics.compute_statistics()
    print(f"Latency: {stats['latency']['mean']*1000:.2f}ms")
```

## Usage Examples

### Example 1: Autonomous Run

```python
from rpycbench.benchmarks.suite import BenchmarkSuite

suite = BenchmarkSuite()
results = suite.run_all(
    num_connections=100,
    num_requests=1000,
    num_concurrent_clients=10,
)
results.print_summary()
```

### Example 2: Baseline vs Application Overhead

Compare baseline performance with your app overhead:

```python
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection

class MyApp:
    def __init__(self, conn):
        self.conn = conn

    def process(self, data):
        # Your app logic (validation, transformation, etc.)
        return self.conn.root.echo(data)

with RPyCServer(host='localhost', port=18812, mode='threaded'):
    conn = create_rpyc_connection('localhost', 18812)

    # Baseline benchmark
    with BenchmarkContext("Baseline", "rpyc", measure_latency=True) as bench:
        for _ in range(100):
            with bench.measure_request():
                conn.root.ping()
                bench.record_request(success=True)
    baseline = bench.get_results()

    # App benchmark
    app = MyApp(conn)
    with BenchmarkContext("With App", "rpyc", measure_latency=True) as bench:
        for _ in range(100):
            with bench.measure_request():
                app.process(b'test')
                bench.record_request(success=True)
    app_metrics = bench.get_results()

    conn.close()

# Compare results
baseline_lat = baseline.compute_statistics()['latency']['mean']
app_lat = app_metrics.compute_statistics()['latency']['mean']
overhead = app_lat - baseline_lat
print(f"App overhead: {overhead*1000:.2f}ms")
```

### Example 3: Custom Benchmarks

Create custom benchmarks for specific scenarios:

```python
from rpycbench.core.benchmark import LatencyBenchmark
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection

with RPyCServer(host='localhost', port=18812, mode='threaded'):

    # Custom latency benchmark
    bench = LatencyBenchmark(
        name="Custom Test",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: create_rpyc_connection('localhost', 18812),
        request_func=lambda conn: conn.root.compute(1000),  # Custom method
        num_requests=500,
    )

    metrics = bench.execute()
    stats = metrics.compute_statistics()

    print(f"Mean latency: {stats['latency']['mean']*1000:.2f}ms")
    print(f"P95 latency: {stats['latency']['p95']*1000:.2f}ms")
```

## Command Line Options

```
rpycbench [options]

Server Configuration:
  --rpyc-host HOST          RPyC server host (default: localhost)
  --rpyc-port PORT          RPyC server port (default: 18812)
  --http-host HOST          HTTP server host (default: localhost)
  --http-port PORT          HTTP server port (default: 5000)

Test Selection:
  --skip-rpyc-threaded      Skip RPyC threaded server tests
  --skip-rpyc-forking       Skip RPyC forking server tests
  --skip-http               Skip HTTP server tests

Benchmark Parameters:
  --num-connections N       Number of connections (default: 100)
  --num-requests N          Number of requests (default: 1000)
  --num-concurrent-clients N Number of concurrent clients (default: 10)
  --requests-per-client N   Requests per client (default: 100)

Output Options:
  --output FILE, -o FILE    Save JSON results to file
  --quiet, -q               Suppress summary output
```

## Architecture

```
rpycbench/
├── core/
│   ├── benchmark.py      # Core benchmark classes and context managers
│   └── metrics.py        # Metrics collection and statistics
├── servers/
│   ├── rpyc_servers.py   # RPyC server implementations
│   └── http_servers.py   # HTTP/REST server implementations
├── benchmarks/
│   └── suite.py          # Complete benchmark suite
├── runners/
│   └── autonomous.py     # Autonomous runner (CLI)
└── utils/
    └── ...               # Utility functions
```

## Benchmark Types

### 1. Connection Benchmark
Measures time to establish a connection to the server.

### 2. Latency Benchmark
Measures request/response round-trip time with statistics:
- Mean, median, min, max
- Standard deviation
- 95th and 99th percentiles

### 3. Bandwidth Benchmark
Measures data transfer rates for various payload sizes (1KB - 1MB):
- Upload bandwidth
- Download bandwidth

### 4. Concurrent Benchmark
Measures performance with multiple simultaneous clients:
- Connection establishment under load
- Request throughput
- Success rate
- Resource usage

## Output Format

### Console Summary

```
================================================================================
BENCHMARK RESULTS SUMMARY
================================================================================

RPYC_THREADED
----------------------------------------
  Connection Time: 1.23ms (±0.45ms)
  Latency Mean: 2.34ms (±0.67ms)
  Latency Median: 2.10ms
  Latency P95: 3.56ms
  Latency P99: 4.23ms
  Upload Bandwidth: 45.67 MB/s
  Download Bandwidth: 67.89 MB/s
  Concurrent Connections: 10
  Total Requests: 1000
  Success Rate: 100.00%
  CPU Usage: 15.3% (max: 45.2%)
  Memory Usage: 12.1% (max: 18.7%)

HTTP_THREADED
----------------------------------------
  Connection Time: 2.45ms (±0.78ms)
  Latency Mean: 3.21ms (±0.89ms)
  ...
```

### JSON Output

```json
{
  "rpyc_threaded": {
    "name": "RPyC Latency (threaded)",
    "protocol": "rpyc",
    "server_mode": "threaded",
    "connection_time": {
      "mean": 0.00123,
      "median": 0.00120,
      "min": 0.00089,
      "max": 0.00245,
      "stdev": 0.00045,
      "count": 100
    },
    "latency": {
      "mean": 0.00234,
      "median": 0.00210,
      "p95": 0.00356,
      "p99": 0.00423,
      ...
    }
  }
}
```

## Extending the Suite

### Custom Server Implementation

```python
from rpycbench.core.benchmark import BenchmarkBase

class MyCustomBenchmark(BenchmarkBase):
    def setup(self):
        # Setup resources
        pass

    def run(self):
        # Run benchmark
        for _ in range(self.num_iterations):
            start = time.time()
            # Your benchmark code
            duration = time.time() - start
            self.metrics.add_latency(duration)

    def teardown(self):
        # Cleanup
        pass

metrics = MyCustomBenchmark(...).execute()
```

### Custom Metrics

```python
from rpycbench.core.metrics import BenchmarkMetrics

metrics = BenchmarkMetrics(name="Custom", protocol="rpyc")
metrics.add_connection_time(0.001)
metrics.add_latency(0.002)
metrics.record_system_metrics()

stats = metrics.compute_statistics()
```

## Requirements

- Python >= 3.8
- rpyc >= 5.3.0
- requests >= 2.31.0
- flask >= 3.0.0
- numpy >= 1.24.0
- pandas >= 2.0.0
- matplotlib >= 3.7.0
- psutil >= 5.9.0

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

See LICENSE file for details.

## Examples

See the `examples/` directory for more usage examples:
- `autonomous_run.py` - Running benchmarks autonomously
- `context_manager_basic.py` - Basic context manager usage
- `context_manager_app_integration.py` - Integration with application code
