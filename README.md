# RPyC Bench - RPyC vs HTTP/REST Benchmark Suite

A comprehensive Python benchmark suite for comparing RPyC (Remote Python Call) with HTTP/REST performance across multiple dimensions.

## Table of Contents

- [Features & Architecture](#features--architecture)
- [Quick Install](#quick-install)
- [Installation Options](#installation-options)
- [Quick Start](#quick-start)
  - [Autonomous Mode](#autonomous-mode)
  - [Baseline Comparison](#baseline-comparison-rpyc-vs-http)
  - [Using as Context Managers](#using-as-context-managers)
- [Usage Examples](#usage-examples)
- [Command Line Options](#command-line-options)
- [RPyC Profiling & Telemetry](#rpyc-profiling--telemetry)
- [How It Works: Threading Model & Isolation](#how-it-works-threading-model--isolation)
- [Benchmark Types](#benchmark-types)
- [Output Format](#output-format)
- [Architecture (Directory Structure)](#architecture)
- [Extending the Suite](#extending-the-suite)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [License](#license)
- [Examples](#examples)

## Features & Architecture

rpycbench measures RPyC vs HTTP/REST performance across four dimensions:

1. **Connection Time**: Initial handshake and connection establishment
2. **Latency**: Round-trip time for request/response pairs (with percentile analysis)
3. **Bandwidth**: Data transfer rates for various payload sizes
4. **Concurrency**: Performance under load with multiple simultaneous connections

**What's Being Measured**:
- RPyC uses binary protocol over raw sockets with Python object serialization
- HTTP uses JSON over REST with request/response overhead
- Tests measure both baseline protocol performance and real-world usage patterns
- Profiler identifies bottlenecks like excessive round trips and netref overhead

**Key Capabilities**:

- **Comprehensive Metrics**
  - Connection establishment time
  - Request/response latency (mean, median, P95, P99)
  - Upload and download bandwidth
  - System resource usage (CPU, memory)

- **Multiple Server Modes**
  - RPyC: Threaded server, Forking server
  - HTTP: Flask-based threaded server

- **High Concurrency Testing**
  - Default: 128 parallel connections from single client
  - Server runs in separate process (no GIL interference)
  - Per-connection metrics tracking
  - Compare server modes under load

- **Flexible Usage**
  - **Autonomous Mode**: Run complete benchmark suite standalone
  - **Context Managers**: Integrate benchmarks into your application code
  - Compare baseline performance vs. application overhead

- **RPyC Profiling & Telemetry**
  - Track network round trips in real-time
  - Monitor netref creation and lifecycle
  - Visualize call stacks and nesting depth
  - Detect slow calls automatically
  - ASCII call tree and timeline visualization
  - Diagnose performance bottlenecks in your RPyC applications

**Design Principles**:
- **Separate Processes**: Servers run in isolated processes to eliminate GIL interference
- **Multiple Server Modes**: RPyC threaded/forking vs HTTP threaded
- **High Concurrency**: Default 128 parallel client connections from single process
- **Context Managers**: Embed benchmarks directly into application code
- **Profiling**: Track RPyC network round trips, netref usage, and call patterns

## Quick Install

Always get the latest version with a single command:

```bash
# Using Python (works everywhere)
curl -sSL https://raw.githubusercontent.com/patrickkidd/rpycbench/main/install-latest.py | python3

# Or using bash (Linux/Mac)
curl -sSL https://raw.githubusercontent.com/patrickkidd/rpycbench/main/install-latest.sh | bash
```

This automatically fetches and installs the latest wheel from GitHub releases - no version string needed!

**How it works**: The script queries the GitHub API for the latest release, extracts the wheel URL, and runs `pip install --upgrade --force-reinstall` on it. This ensures you always get the most recent build without manually tracking version numbers.

## Installation Options

The quick install above is recommended, but here are other options:

### Manual Installation from GitHub Releases

Every push to master automatically builds a wheel. Install a specific version:

```bash
# Install specific version
pip install https://github.com/patrickkidd/rpycbench/releases/download/v0.1.0-build.123/rpycbench-0.1.0-py3-none-any.whl

# Upgrade to a specific version
pip install --upgrade --force-reinstall https://github.com/patrickkidd/rpycbench/releases/download/v0.1.0-build.123/rpycbench-0.1.0-py3-none-any.whl
```

Browse all releases: https://github.com/patrickkidd/rpycbench/releases

### Direct Install from Master Branch

Install directly from the latest wheel built from master (bypasses releases):

```bash
pip install --upgrade https://github.com/patrickkidd/rpycbench/raw/master/dist/rpycbench-0.1.0-py3-none-any.whl
```

Note: This requires the wheel to be committed to the repository. Use the release-based install above for automatic updates.

### From Source

```bash
# Clone repository
git clone https://github.com/patrickkidd/rpycbench.git
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

### Baseline Comparison (RPyC vs HTTP)

Compare baseline performance in a single run with comparable metrics:

```bash
# Run baseline comparison
python examples/baseline_comparison.py

# Quick baseline (faster, less accurate)
python examples/baseline_comparison.py --quick
```

Or use the CLI:
```bash
# Compare RPyC threaded vs HTTP (skip forking for faster baseline)
rpycbench --skip-rpyc-forking --output baseline.json
```

**Output Format**: All metrics are in the same format for easy comparison:

```
================================================================================
BENCHMARK RESULTS SUMMARY
================================================================================

RPYC_THREADED
----------------------------------------
  Connection Time: 1.23ms (±0.45ms)
  Latency Mean: 2.34ms (±0.67ms)
  Latency P95: 3.56ms
  Upload Bandwidth: 45.67 MB/s
  Download Bandwidth: 67.89 MB/s

HTTP_THREADED
----------------------------------------
  Connection Time: 2.45ms (±0.78ms)
  Latency Mean: 3.21ms (±0.89ms)
  Latency P95: 4.12ms
  Upload Bandwidth: 38.45 MB/s
  Download Bandwidth: 52.31 MB/s
```

**JSON Export** for programmatic comparison:
```python
import json
data = json.load(open('baseline.json'))

# Compare latencies
rpyc_lat = data['rpyc_threaded']['latency']['mean']
http_lat = data['http_threaded']['latency']['mean']
speedup = http_lat / rpyc_lat
print(f"RPyC is {speedup:.2f}x faster")

# Compare bandwidth
rpyc_bw = data['rpyc_threaded']['download_bandwidth']['mean']
http_bw = data['http_threaded']['download_bandwidth']['mean']
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

### Example 3: Baseline Comparison

Run a quick baseline comparison:

```python
from rpycbench.benchmarks.suite import BenchmarkSuite

suite = BenchmarkSuite()

# Compare RPyC vs HTTP
results = suite.run_all(
    test_rpyc_threaded=True,
    test_rpyc_forking=False,  # Skip for faster baseline
    test_http=True,
    num_connections=100,
    num_requests=1000,
)

# Print formatted comparison
results.print_summary()

# Export for analysis
data = results.to_dict()
print(f"RPyC latency: {data['rpyc_threaded']['latency']['mean']*1000:.2f}ms")
print(f"HTTP latency: {data['http_threaded']['latency']['mean']*1000:.2f}ms")
```

### Example 4: Custom Benchmarks

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

## RPyC Profiling & Telemetry

Profile and diagnose performance issues in your RPyC applications by tracking network round trips, netref usage, and call patterns.

### Quick Profiling Example

```python
from rpycbench.utils.profiler import create_profiled_connection
from rpycbench.utils.telemetry import RPyCTelemetry
from rpycbench.servers.rpyc_servers import RPyCServer

# Start server
with RPyCServer(host='localhost', port=18812, mode='threaded'):

    # Create telemetry instance
    telemetry = RPyCTelemetry(
        enabled=True,
        track_netrefs=True,
        slow_call_threshold=0.1,  # 100ms
        deep_stack_threshold=5,    # Warn on 5+ nested calls
    )

    # Create profiled connection
    conn = create_profiled_connection(
        host='localhost',
        port=18812,
        telemetry_inst=telemetry,
    )

    # Make remote calls - they're automatically tracked!
    for i in range(10):
        conn.root.ping()

    conn.close()

    # Print comprehensive telemetry report
    telemetry.print_summary()
```

### What Gets Tracked

1. **Network Round Trips**: Count every remote call
2. **NetRef Operations**: Track netref creation, access, and lifecycle
3. **Call Stacks**: Monitor nesting depth and call chains
4. **Slow Calls**: Automatically detect calls exceeding threshold
5. **Performance**: Latency per call, total duration, resource usage

### Profiling Output

```
================================================================================
RPYC TELEMETRY SUMMARY
================================================================================
Total Calls:              45
Network Round Trips:      45
NetRefs Created:          3
Active NetRefs:           1
Current Stack Depth:      0
Max Stack Depth:          3
Slow Calls (>0.1s):       2
Avg Call Duration:        12.34ms

--------------------------------------------------------------------------------
SLOW CALLS:
--------------------------------------------------------------------------------
  process_large_batch              150.23ms  depth=0
  nested_computation                120.45ms  depth=2

--------------------------------------------------------------------------------
DEEP CALL STACKS (>5 levels):
--------------------------------------------------------------------------------
  Depth: 6
    → get_object (method)
    → access_property (getattr)
    → call_method (method)
    → another_call (method)
    ...
```

### Visualization Tools

```python
from rpycbench.utils.visualizer import (
    format_call_tree,
    format_timeline,
    format_netref_report,
    format_slow_calls_report,
)

# Call tree shows nesting and hierarchy
print(format_call_tree(telemetry))

# Timeline shows when calls happened
print(format_timeline(telemetry, width=80))

# NetRef report shows object usage
print(format_netref_report(telemetry))

# Slow calls report with details
print(format_slow_calls_report(telemetry, top_n=20))
```

### Using with Context Manager

```python
from rpycbench.utils.profiler import profile_rpyc_calls

conn = rpyc.connect('localhost', 18812)

with profile_rpyc_calls(conn, slow_call_threshold=0.05) as profiled:
    # Use profiled connection
    profiled.root.some_method()

# Telemetry summary automatically printed on exit
```

### Diagnosing Performance Issues

Common issues the profiler helps identify:

1. **Excessive Round Trips**
   ```python
   # BAD: N round trips
   for item in items:
       conn.root.process(item)  # Each call = 1 round trip

   # Profiler shows: 100 round trips for 100 items
   ```

2. **NetRef Overhead**
   ```python
   # Each netref access is a network call
   obj = conn.root.get_object()  # Creates netref
   obj.property  # Network call!
   obj.method()  # Network call!

   # Profiler shows: NetRef created with 10 accesses
   ```

3. **Deep Call Stacks**
   ```python
   # Nested remote calls create latency
   conn.root.a()  # Which calls b()
     # Which calls c()
       # Which calls d()

   # Profiler shows: Stack depth of 4, total latency accumulates
   ```

### Integration with Benchmarks

Combine profiling with benchmarking to understand both baseline and actual performance:

```python
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.utils.profiler import create_profiled_connection

conn = create_profiled_connection('localhost', 18812)

# Benchmark with profiling
with BenchmarkContext("My App", "rpyc", measure_latency=True) as bench:
    for _ in range(100):
        with bench.measure_request():
            conn.root.my_method()
            bench.record_request(success=True)

# Get both benchmark metrics AND telemetry
metrics = bench.get_results()
telemetry = conn.telemetry

print(f"Latency: {metrics.compute_statistics()['latency']['mean']*1000:.2f}ms")
print(f"Round trips: {telemetry.total_network_roundtrips}")
```

### Examples

See the `examples/` directory for complete profiling examples:
- `profiling_basic.py` - Basic profiling usage
- `profiling_advanced.py` - Advanced features and visualization
- `profiling_diagnose_slow_calls.py` - Real-world performance diagnosis

## How It Works: Threading Model & Isolation

### Server Execution Model

**Important**: All benchmark servers run in **separate processes** from the benchmark client code. This provides true isolation without GIL interference:

1. **Server Lifecycle**:
   - Server is spawned in a separate process before each test
   - Server lifecycle is automatically managed by the parent process
   - Tests run against the server
   - Server is cleanly terminated after the test completes
   - Each server type is tested **sequentially** (one at a time)

2. **Process Isolation** (✅ No GIL Interference):
   - **Server Process**: Runs completely independently from client
   - **Client Process**: Runs 128+ concurrent client threads without GIL from server
   - **Benefits**: True parallelism, accurate performance metrics, production-like environment

3. **Server Threading Models**:
   - **RPyC ThreadedServer**: Creates NEW THREAD per client connection (in server process)
   - **RPyC ForkingServer**: FORKS NEW PROCESS per client connection (from server process)
   - **HTTP ThreadedServer**: Flask handles requests in threads (in server process)

4. **Client Concurrency**:
   - Default: **128 concurrent connections** from single client process
   - Each connection runs in its own thread within the client process
   - Configurable: Can test with any number of concurrent clients
   - Per-connection metrics tracking available

5. **Why This Design?**:
   - ✅ **No GIL interference** between server and client
   - ✅ **Easy to use** - single script, automatic lifecycle management
   - ✅ **Production-like** - tests real server modes (threaded, forking)
   - ✅ **High concurrency** - test with 128+ parallel connections
   - ✅ **Accurate metrics** - server runs unencumbered by client GIL

### Port Usage

- RPyC servers use port 18812 by default (configurable)
- HTTP servers use port 5000 by default (configurable)
- Ports are reused between tests (servers are stopped between runs)

### Code Execution Flow

```
1. Start RPyC Threaded Server (background thread)
   └─> Run Connection Benchmark
   └─> Run Latency Benchmark
   └─> Run Bandwidth Benchmark
   └─> Run Concurrent Benchmark
2. Stop RPyC Threaded Server

3. Start RPyC Forking Server (background thread)
   └─> Run all benchmarks...
4. Stop RPyC Forking Server

5. Start HTTP Server (background thread)
   └─> Run all benchmarks...
6. Stop HTTP Server

7. Compare results
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
    ├── telemetry.py      # RPyC telemetry tracking
    ├── profiler.py       # Connection profiling
    └── visualizer.py     # Telemetry visualization
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

See the `examples/` directory for complete examples:

**Benchmarking:**
- `baseline_comparison.py` - Quick baseline comparison of RPyC vs HTTP
- `high_concurrency_128.py` - 128 parallel connections with per-connection metrics
- `autonomous_run.py` - Running full benchmark suite autonomously
- `context_manager_basic.py` - Basic context manager usage
- `context_manager_app_integration.py` - Integration with application code
- `quick_test.py` - Quick verification test

**Profiling:**
- `profiling_basic.py` - Basic RPyC profiling
- `profiling_advanced.py` - Advanced profiling with visualization
- `profiling_diagnose_slow_calls.py` - Real-world performance diagnosis

**High Concurrency:**

Test 128 parallel connections and compare server modes:
```bash
# Test RPyC with 128 concurrent connections
python examples/high_concurrency_128.py --rpyc

# Test HTTP with 128 concurrent connections
python examples/high_concurrency_128.py --http

# Compare threaded vs forking server modes
python examples/high_concurrency_128.py --compare

# Run all tests
python examples/high_concurrency_128.py
```
