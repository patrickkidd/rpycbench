# RPyC Bench - RPyC vs HTTP/REST Benchmark Suite

A comprehensive Python benchmark suite for comparing RPyC (Remote Python Call) with HTTP/REST performance across multiple dimensions.

## Table of Contents

- [Features & Architecture](#features--architecture)
- [Quick Install](#quick-install)
- [Installation Options](#installation-options)
- [Command-Line Usage](#command-line-usage) - Testing RPyC vs HTTP/Flask generically
  - [Quick Start Examples](#quick-start-examples)
  - [Cookbook: Common Scenarios](#cookbook-common-scenarios)
  - [Command Reference](#command-reference)
- [Python API for Existing Apps](#python-api-for-existing-apps) - Integrating benchmarks into your application
  - [Basic Integration](#basic-integration)
  - [Synthetic App Example](#synthetic-app-example)
  - [Measuring Application Overhead](#measuring-application-overhead)
  - [Context Manager Patterns](#context-manager-patterns)
  - [RPyC Profiling & Telemetry](#rpyc-profiling--telemetry)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Contributing](#contributing)

## Features & Architecture

rpycbench measures RPyC vs HTTP/REST performance across five dimensions:

1. **Connection Time**: Initial handshake and connection establishment
2. **Latency**: Round-trip time for request/response pairs (mean, median, P95, P99)
3. **Bandwidth**: Data transfer rates for various payload sizes
4. **Binary File Transfer**: Large file transfers with configurable sizes and chunk sizes
5. **Concurrency**: Performance under load with multiple simultaneous connections

**What's Being Measured**:
- RPyC uses binary protocol over raw sockets with Python object serialization
- HTTP uses JSON over REST with request/response overhead
- Tests measure both baseline protocol performance and real-world usage patterns
- Profiler identifies bottlenecks like excessive round trips and netref overhead

**Key Capabilities**:
- Comprehensive metrics: connection time, latency (P95/P99), bandwidth, system resources
- Multiple server modes: RPyC threaded/forking, HTTP threaded
- High concurrency testing: 128+ parallel connections with per-connection tracking
- Two usage modes: CLI for generic testing, Python API for application integration
- Built-in profiling: track RPyC round trips, netrefs, and call patterns

## Quick Install

Always get the latest version with a single command:

```bash
# Using Python (works everywhere)
curl -sSL https://raw.githubusercontent.com/patrickkidd/rpycbench/main/install-latest.py | python3

# Or using bash (Linux/Mac)
curl -sSL https://raw.githubusercontent.com/patrickkidd/rpycbench/main/install-latest.sh | bash
```

This automatically fetches and installs the latest wheel from GitHub releases - no version string needed!

## Installation Options

### Manual Installation from GitHub Releases

```bash
# Install specific version
pip install https://github.com/patrickkidd/rpycbench/releases/download/v0.1.0-build.123/rpycbench-0.1.0-py3-none-any.whl

# Upgrade to a specific version
pip install --upgrade --force-reinstall https://github.com/patrickkidd/rpycbench/releases/download/v0.1.0-build.123/rpycbench-0.1.0-py3-none-any.whl
```

Browse all releases: https://github.com/patrickkidd/rpycbench/releases

### From Source

```bash
git clone https://github.com/patrickkidd/rpycbench.git
cd rpycbench
pip install -r requirements.txt
pip install -e .
```

---

# Command-Line Usage

**Purpose**: Test RPyC vs HTTP/Flask performance generically without writing code.

The command-line tool runs benchmarks comparing RPyC and HTTP servers across different scenarios. Use this to understand baseline performance characteristics before integrating into your application.

## Quick Start Examples

### Basic Comparison

```bash
# Run all benchmarks with default settings
rpycbench

# Quick baseline (skip forking server for speed)
rpycbench --skip-rpyc-forking

# Save results to JSON
rpycbench --output results.json
```

### Focused Testing

```bash
# Test only latency
rpycbench --num-serial-connections 10 --num-requests 5000

# Test only concurrency
rpycbench --num-parallel-clients 50 --requests-per-client 200

# Test only binary transfers
rpycbench --test-binary-transfer --binary-file-sizes 1048576 10485760
```

## Cookbook: Common Scenarios

### Scenario 1: Quick Health Check

**Goal**: Verify RPyC and HTTP are working correctly

```bash
rpycbench \
  --skip-rpyc-forking \
  --num-serial-connections 10 \
  --num-requests 100 \
  --num-parallel-clients 5
```

**What it tests**: Basic connectivity, latency, and light concurrency
**Time**: ~10 seconds

---

### Scenario 2: Detailed Latency Analysis

**Goal**: Understand request/response latency characteristics

```bash
rpycbench \
  --num-requests 10000 \
  --num-serial-connections 1 \
  --num-parallel-clients 1
```

**What it tests**: P50, P95, P99 latency with large sample size
**Time**: ~30 seconds
**Output**: Detailed percentile breakdown

---

### Scenario 3: High Concurrency Load Test

**Goal**: Test performance under heavy concurrent load

```bash
rpycbench \
  --num-parallel-clients 128 \
  --requests-per-client 500 \
  --skip-rpyc-forking
```

**What it tests**: 128 parallel connections making 500 requests each
**Time**: ~1-2 minutes
**Watch for**: Success rate, connection failures, resource usage

---

### Scenario 4: Bandwidth Characterization

**Goal**: Understand data transfer rates for different payload sizes

```bash
rpycbench \
  --num-serial-connections 10 \
  --num-requests 100 \
  --num-parallel-clients 1
```

**What it tests**: Upload/download bandwidth for 1KB - 1MB payloads
**Time**: ~20 seconds
**Focus**: Bandwidth benchmark results

---

### Scenario 5: Large File Transfers

**Goal**: Test large file transfer performance

```bash
# Test with default 64KB chunks
rpycbench --test-binary-transfer

# Compare different chunk sizes
rpycbench --test-binary-transfer --binary-chunk-size 8192
rpycbench --test-binary-transfer --binary-chunk-size 524288

# Custom file sizes
rpycbench --test-binary-transfer \
  --binary-file-sizes 5242880 52428800 \
  --binary-chunk-size 65536 \
  --binary-iterations 5
```

**What it tests**: Multi-MB file transfers with different chunking strategies
**Time**: Varies by file size (can be 5-10 minutes for 500MB)
**Insight**: Shows impact of chunk size on throughput

---

### Scenario 6: Server Mode Comparison

**Goal**: Compare threaded vs forking server performance

```bash
rpycbench \
  --num-parallel-clients 32 \
  --requests-per-client 100
```

**What it tests**: Both threaded and forking RPyC servers under load
**Time**: ~1 minute
**Compare**: Threaded vs forking results for your workload

---

### Scenario 7: Production Simulation

**Goal**: Simulate production-like mixed workload

```bash
rpycbench \
  --num-serial-connections 50 \
  --num-requests 2000 \
  --num-parallel-clients 20 \
  --requests-per-client 200 \
  --test-binary-transfer \
  --binary-file-sizes 1048576 \
  --binary-chunk-size 65536 \
  --output production-sim.json
```

**What it tests**: Connection establishment, latency, bandwidth, concurrency, file transfers
**Time**: ~3-5 minutes
**Use**: Baseline for production planning

---

### Scenario 8: RPyC Forking Only

**Goal**: Test only forking server (may be needed for CPU-bound work)

```bash
rpycbench \
  --skip-rpyc-threaded \
  --skip-http \
  --num-parallel-clients 10
```

**What it tests**: RPyC forking server isolation
**Time**: ~30 seconds
**Use**: When GIL contention is a concern

---

### Scenario 9: HTTP Only Baseline

**Goal**: Establish HTTP/REST baseline for comparison

```bash
rpycbench \
  --skip-rpyc-threaded \
  --skip-rpyc-forking \
  --num-requests 5000 \
  --output http-baseline.json
```

**What it tests**: Pure HTTP/Flask performance
**Time**: ~20 seconds
**Use**: Compare against existing HTTP services

---

### Scenario 10: Minimal Overhead Test

**Goal**: Find absolute minimum latency/overhead

```bash
rpycbench \
  --skip-rpyc-forking \
  --num-serial-connections 1 \
  --num-requests 10000 \
  --num-parallel-clients 1
```

**What it tests**: Single connection, sequential requests
**Time**: ~30 seconds
**Result**: Best-case latency numbers (no concurrency overhead)

---

### Scenario 11: Remote Server Benchmarking

**Goal**: Run benchmarks with server on a remote host via SSH

```bash
# Benchmark against remote server (automatic deployment)
rpycbench --remote-host user@hostname

# Benchmark with custom host/port configuration
rpycbench --remote-host user@192.168.1.100 \
  --rpyc-host 0.0.0.0 \
  --http-host 0.0.0.0

# Skip HTTP and test only RPyC on remote host
rpycbench --remote-host deploy@production-server \
  --skip-http \
  --num-parallel-clients 32
```

**What it does**:
- Automatically deploys rpycbench to remote host via SSH
- Caches deployment (only redeploys when code changes)
- Starts server processes on remote host
- Runs benchmarks from local machine against remote server
- Cleans up remote processes when done

**Requirements**:
- SSH access to remote host with public key authentication
- `uv` installed on remote host
- Firewall allows connections on specified ports

**Time**: Initial deployment ~30s, cached deployments ~5s overhead
**Use**: Test performance across network, production-like infrastructure testing

---

## Command Reference

```
rpycbench [options]
```

### Server Configuration

```
--remote-host USER@HOST   Remote host for server deployment via SSH (format: user@hostname)
                          Enables automatic deployment and server management on remote host
--rpyc-host HOST          RPyC server host (default: localhost)
--rpyc-port PORT          RPyC server port (default: 18812)
--http-host HOST          HTTP server host (default: localhost)
--http-port PORT          HTTP server port (default: 5000)
```

### Test Selection

```
--skip-rpyc-threaded      Skip RPyC threaded server tests
--skip-rpyc-forking       Skip RPyC forking server tests
--skip-http               Skip HTTP server tests
```

### Benchmark Parameters

```
--num-serial-connections N    Sample size: number of serial connections created one-at-a-time
                              to measure average connection establishment time (default: 100)
--num-requests N              Sample size: number of requests for latency benchmark (default: 1000)
--num-parallel-clients N      Number of parallel clients (simultaneous connections to
                              measure performance under load) (default: 10)
--requests-per-client N       Requests per parallel client (default: 100)
```

### Binary Transfer Benchmark

```
--test-binary-transfer    Enable binary file transfer benchmarks
--binary-file-sizes SIZE [SIZE ...]
                          File sizes in bytes (default: 1572864 134217728 524288000)
--binary-chunk-size SIZE  Chunk size in bytes (default: 65536)
                          Run multiple times with different values to compare
--binary-iterations N     Number of iterations per test (default: 3)
```

### Output Options

```
--output FILE, -o FILE    Save JSON results to file
--quiet, -q               Suppress summary output
```

### Example Combinations

```bash
# Comprehensive test with all options
rpycbench \
  --rpyc-host localhost \
  --rpyc-port 18812 \
  --http-host localhost \
  --http-port 5000 \
  --num-serial-connections 200 \
  --num-requests 5000 \
  --num-parallel-clients 50 \
  --requests-per-client 100 \
  --test-binary-transfer \
  --binary-file-sizes 1048576 10485760 52428800 \
  --binary-chunk-size 65536 \
  --binary-iterations 5 \
  --output comprehensive-results.json

# Minimal fast test
rpycbench \
  --skip-rpyc-forking \
  --skip-http \
  --num-serial-connections 5 \
  --num-requests 50 \
  --num-parallel-clients 2 \
  --quiet
```

---

# Python API for Existing Apps

**Purpose**: Integrate benchmarks into your existing application to measure real-world performance.

Use the Python API to:
- Measure your application's actual RPyC/HTTP performance
- Compare baseline protocol performance vs your application overhead
- Track performance over time in your codebase
- Profile specific operations in your application

## Basic Integration

### Measuring a Simple Operation

```python
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection

# Start server
with RPyCServer(host='localhost', port=18812, mode='threaded'):
    # Create benchmark context
    with BenchmarkContext(
        name="My Operation",
        protocol="rpyc",
        measure_latency=True,
    ) as bench:
        conn = create_rpyc_connection('localhost', 18812)

        # Measure your operations
        for i in range(100):
            with bench.measure_request():
                result = conn.root.ping()
                bench.record_request(success=True)

        conn.close()

    # Get results
    metrics = bench.get_results()
    stats = metrics.compute_statistics()
    print(f"Average latency: {stats['latency']['mean']*1000:.2f}ms")
    print(f"P95 latency: {stats['latency']['p95']*1000:.2f}ms")
```

## Synthetic App Example

Here's a complete example of a synthetic application with remote function calls being benchmarked:

```python
"""
Synthetic Application Example: Remote Data Processing Service

This demonstrates a realistic application with:
- Data validation
- Remote computation
- Error handling
- Performance measurement
"""

import rpyc
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection


# Define your RPyC service (your application logic)
class DataProcessingService(rpyc.Service):
    """Example remote data processing service"""

    def exposed_validate_data(self, data):
        """Validate input data"""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if 'values' not in data:
            raise ValueError("Data must contain 'values' key")
        return True

    def exposed_compute_statistics(self, data):
        """Compute statistics on data"""
        values = data['values']
        return {
            'mean': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'count': len(values),
        }

    def exposed_process_batch(self, batch):
        """Process a batch of data items"""
        results = []
        for item in batch:
            # Simulate processing
            processed = {
                'id': item['id'],
                'result': item['value'] * 2,
                'status': 'processed'
            }
            results.append(processed)
        return results

    def exposed_store_results(self, results):
        """Store processing results"""
        # Simulate storage
        return {'stored': len(results), 'status': 'success'}


# Your application client
class DataProcessingClient:
    """Client for data processing service"""

    def __init__(self, connection):
        self.conn = connection

    def validate(self, data):
        """Validate data before processing"""
        return self.conn.root.validate_data(data)

    def compute(self, data):
        """Compute statistics"""
        return self.conn.root.compute_statistics(data)

    def process_batch(self, batch):
        """Process a batch of items"""
        return self.conn.root.process_batch(batch)

    def store(self, results):
        """Store results"""
        return self.conn.root.store_results(results)

    def full_pipeline(self, data, batch):
        """Full processing pipeline"""
        # Validation
        self.validate(data)

        # Computation
        stats = self.compute(data)

        # Batch processing
        results = self.process_batch(batch)

        # Storage
        store_result = self.store(results)

        return {
            'stats': stats,
            'batch_results': results,
            'storage': store_result
        }


# Benchmark your application
def benchmark_application():
    """Benchmark the data processing application"""

    # Start server with your service
    with RPyCServer(host='localhost', port=18812, mode='threaded'):
        # Connect to server
        conn = create_rpyc_connection('localhost', 18812)

        # Create client
        client = DataProcessingClient(conn)

        # Prepare test data
        test_data = {
            'values': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        }

        test_batch = [
            {'id': i, 'value': i * 10}
            for i in range(20)
        ]

        # Benchmark individual operations
        print("=" * 80)
        print("BENCHMARKING INDIVIDUAL OPERATIONS")
        print("=" * 80)

        # 1. Validation performance
        with BenchmarkContext("Validation", "rpyc", measure_latency=True) as bench:
            for _ in range(1000):
                with bench.measure_request():
                    client.validate(test_data)
                    bench.record_request(success=True)

        stats = bench.get_results().compute_statistics()
        print(f"\nValidation:")
        print(f"  Mean: {stats['latency']['mean']*1000:.2f}ms")
        print(f"  P95:  {stats['latency']['p95']*1000:.2f}ms")

        # 2. Computation performance
        with BenchmarkContext("Computation", "rpyc", measure_latency=True) as bench:
            for _ in range(1000):
                with bench.measure_request():
                    client.compute(test_data)
                    bench.record_request(success=True)

        stats = bench.get_results().compute_statistics()
        print(f"\nComputation:")
        print(f"  Mean: {stats['latency']['mean']*1000:.2f}ms")
        print(f"  P95:  {stats['latency']['p95']*1000:.2f}ms")

        # 3. Batch processing performance with bandwidth tracking
        with BenchmarkContext("Batch Processing", "rpyc",
                              measure_latency=True,
                              measure_bandwidth=True) as bench:
            for _ in range(100):
                with bench.measure_request(bytes_sent=len(str(test_batch))):
                    results = client.process_batch(test_batch)
                    bench.record_request(success=True)

        stats = bench.get_results().compute_statistics()
        print(f"\nBatch Processing:")
        print(f"  Mean latency: {stats['latency']['mean']*1000:.2f}ms")
        print(f"  P95 latency:  {stats['latency']['p95']*1000:.2f}ms")
        print(f"  Throughput:   {stats['upload_bandwidth']['mean']/(1024*1024):.2f} MB/s")

        # 4. Full pipeline performance
        print("\n" + "=" * 80)
        print("BENCHMARKING FULL PIPELINE")
        print("=" * 80)

        with BenchmarkContext("Full Pipeline", "rpyc", measure_latency=True) as bench:
            for _ in range(100):
                with bench.measure_request():
                    try:
                        result = client.full_pipeline(test_data, test_batch)
                        bench.record_request(success=True)
                    except Exception as e:
                        bench.record_request(success=False)

        stats = bench.get_results().compute_statistics()
        metrics = bench.get_results()
        success_rate = (metrics.total_requests - metrics.failed_requests) / metrics.total_requests * 100

        print(f"\nFull Pipeline:")
        print(f"  Mean latency:  {stats['latency']['mean']*1000:.2f}ms")
        print(f"  P95 latency:   {stats['latency']['p95']*1000:.2f}ms")
        print(f"  P99 latency:   {stats['latency']['p99']*1000:.2f}ms")
        print(f"  Success rate:  {success_rate:.1f}%")
        print(f"  Total requests: {metrics.total_requests}")
        print(f"  Failed:        {metrics.failed_requests}")

        conn.close()


if __name__ == '__main__':
    benchmark_application()
```

**Save this as `my_app_benchmark.py` and run**:
```bash
python my_app_benchmark.py
```

## Measuring Application Overhead

Compare your application's performance against baseline protocol performance:

```python
from rpycbench.core.benchmark import BenchmarkContext, LatencyBenchmark
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection


def compare_baseline_vs_application():
    """Compare baseline RPyC performance vs application performance"""

    with RPyCServer(host='localhost', port=18812, mode='threaded'):
        # 1. Baseline benchmark (direct ping)
        baseline_bench = LatencyBenchmark(
            name="Baseline",
            protocol="rpyc",
            server_mode="threaded",
            connection_factory=lambda: create_rpyc_connection('localhost', 18812),
            request_func=lambda conn: conn.root.ping(),
            num_requests=1000,
        )
        baseline_metrics = baseline_bench.execute()
        baseline_stats = baseline_metrics.compute_statistics()

        # 2. Application benchmark
        conn = create_rpyc_connection('localhost', 18812)

        # Your application class with business logic
        class MyApp:
            def __init__(self, connection):
                self.conn = connection
                self.cache = {}

            def process_request(self, data):
                # Your application logic (validation, caching, etc.)
                if data in self.cache:
                    return self.cache[data]

                # Make remote call
                result = self.conn.root.echo(data)

                # Post-processing
                self.cache[data] = result
                return result

        app = MyApp(conn)

        with BenchmarkContext("Application", "rpyc", measure_latency=True) as bench:
            for i in range(1000):
                with bench.measure_request():
                    app.process_request(f"data_{i}")
                    bench.record_request(success=True)

        app_metrics = bench.get_results()
        app_stats = app_metrics.compute_statistics()

        conn.close()

        # Compare results
        print("=" * 80)
        print("BASELINE VS APPLICATION COMPARISON")
        print("=" * 80)

        baseline_mean = baseline_stats['latency']['mean'] * 1000
        app_mean = app_stats['latency']['mean'] * 1000
        overhead = app_mean - baseline_mean
        overhead_pct = (overhead / baseline_mean) * 100

        print(f"\nBaseline (direct RPyC call):")
        print(f"  Mean: {baseline_mean:.2f}ms")
        print(f"  P95:  {baseline_stats['latency']['p95']*1000:.2f}ms")

        print(f"\nApplication (with business logic):")
        print(f"  Mean: {app_mean:.2f}ms")
        print(f"  P95:  {app_stats['latency']['p95']*1000:.2f}ms")

        print(f"\nOverhead:")
        print(f"  Absolute: {overhead:.2f}ms")
        print(f"  Relative: {overhead_pct:.1f}%")

        if overhead_pct > 50:
            print(f"\n⚠️  Application overhead is {overhead_pct:.1f}% - consider optimization")
        else:
            print(f"\n✓ Application overhead is reasonable at {overhead_pct:.1f}%")


if __name__ == '__main__':
    compare_baseline_vs_application()
```

## Context Manager Patterns

### Pattern 1: Simple Request Measurement

```python
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection

with RPyCServer(host='localhost', port=18812, mode='threaded'):
    with BenchmarkContext("My Service", "rpyc", measure_latency=True) as ctx:
        conn = create_rpyc_connection('localhost', 18812)

        for i in range(100):
            with ctx.measure_request():
                conn.root.my_method(i)
                ctx.record_request(success=True)

        conn.close()

    stats = ctx.get_results().compute_statistics()
    print(f"Mean: {stats['latency']['mean']*1000:.2f}ms")
```

### Pattern 2: Bandwidth Measurement

```python
with BenchmarkContext("File Upload", "rpyc", measure_bandwidth=True) as ctx:
    conn = create_rpyc_connection('localhost', 18812)

    for file_data in my_files:
        with ctx.measure_request(bytes_sent=len(file_data)):
            conn.root.upload(file_data)
            ctx.record_request(success=True)

    conn.close()

stats = ctx.get_results().compute_statistics()
print(f"Upload speed: {stats['upload_bandwidth']['mean']/(1024*1024):.2f} MB/s")
```

### Pattern 3: Connection Time Measurement

```python
with BenchmarkContext("Connections", "rpyc", measure_connection=True) as ctx:
    for i in range(50):
        with ctx.measure_connection_time():
            conn = create_rpyc_connection('localhost', 18812)

        # Use connection
        conn.root.ping()
        conn.close()

stats = ctx.get_results().compute_statistics()
print(f"Avg connection time: {stats['connection_time']['mean']*1000:.2f}ms")
```

### Pattern 4: Error Handling

```python
with BenchmarkContext("API Calls", "rpyc", measure_latency=True) as ctx:
    conn = create_rpyc_connection('localhost', 18812)

    for request in requests:
        with ctx.measure_request():
            try:
                result = conn.root.process(request)
                ctx.record_request(success=True)
            except Exception as e:
                ctx.record_request(success=False)
                # Handle error

    conn.close()

metrics = ctx.get_results()
success_rate = (metrics.total_requests - metrics.failed_requests) / metrics.total_requests
print(f"Success rate: {success_rate*100:.1f}%")
```

### Pattern 5: Programmatic Binary Transfer

```python
from rpycbench.core.benchmark import BinaryTransferBenchmark
from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection

with RPyCServer(host='localhost', port=18812, mode='threaded'):
    bench = BinaryTransferBenchmark(
        name="My File Transfer",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: create_rpyc_connection('localhost', 18812),
        upload_func=lambda conn, data: conn.root.upload_file(data),
        download_func=lambda conn, size: conn.root.download_file(size),
        upload_chunked_func=lambda conn, chunks: conn.root.upload_file_chunked(chunks),
        download_chunked_func=lambda conn, size, chunk_size: conn.root.download_file_chunked(size, chunk_size),
        file_sizes=[1_048_576, 10_485_760],  # 1MB, 10MB
        chunk_size=65_536,  # 64KB
        iterations=5,
    )

    metrics = bench.execute()

    for result in metrics.metadata['transfer_results']:
        print(f"{result['type']}: {result['throughput_mbps']:.2f} Mbps")
```

## RPyC Profiling & Telemetry

Profile and diagnose performance issues in your RPyC applications by tracking network round trips, netref usage, and call patterns.

### Quick Profiling Example

```python
from rpycbench.utils.profiler import create_profiled_connection
from rpycbench.utils.telemetry import RPyCTelemetry
from rpycbench.servers.rpyc_servers import RPyCServer

with RPyCServer(host='localhost', port=18812, mode='threaded'):
    telemetry = RPyCTelemetry(
        enabled=True,
        track_netrefs=True,
        slow_call_threshold=0.1,
        deep_stack_threshold=5,
    )

    conn = create_profiled_connection(
        host='localhost',
        port=18812,
        telemetry_inst=telemetry,
    )

    # Your remote calls are automatically tracked
    for i in range(10):
        conn.root.ping()

    conn.close()

    # Print comprehensive report
    telemetry.print_summary()
```

### What Gets Tracked

1. **Network Round Trips**: Count every remote call
2. **NetRef Operations**: Track netref creation, access, lifecycle
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
```

For more profiling examples, see the `examples/profiling_*.py` files in the repository.

## Remote Server Execution (Python API)

Run benchmarks against a remote server using SSH deployment:

```python
from rpycbench.benchmarks.suite import BenchmarkSuite

suite = BenchmarkSuite(
    rpyc_host='0.0.0.0',
    rpyc_port=18812,
    http_host='0.0.0.0',
    http_port=5000,
    remote_host='user@remote-server.com',
)

results = suite.run_all(
    test_rpyc_threaded=True,
    test_rpyc_forking=True,
    test_http=True,
)

results.print_summary()
```

**What happens**:
1. Connects to remote host via SSH
2. Deploys rpycbench code (cached if unchanged)
3. Sets up Python environment on remote host
4. Starts server processes remotely
5. Runs benchmarks from local machine
6. Stops servers and cleans up

**Using Remote Servers with BenchmarkContext**:

```python
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.remote.servers import RemoteRPyCServer
from rpycbench.servers.rpyc_servers import create_rpyc_connection

with RemoteRPyCServer(
    remote_host='user@hostname',
    host='0.0.0.0',
    port=18812,
    mode='threaded'
):
    with BenchmarkContext("My Remote Test", "rpyc", measure_latency=True) as bench:
        conn = create_rpyc_connection('hostname', 18812)

        for i in range(100):
            with bench.measure_request():
                result = conn.root.ping()
                bench.record_request(success=True)

        conn.close()

    stats = bench.get_results().compute_statistics()
    print(f"Remote latency: {stats['latency']['mean']*1000:.2f}ms")
```

---

# How It Works

## Threading Model & Isolation

**Important**: All benchmark servers run in **separate processes** from the benchmark client code. This provides true isolation without GIL interference.

1. **Server Lifecycle**:
   - Server spawned in separate process before each test
   - Server lifecycle automatically managed by parent process
   - Tests run against the server
   - Server cleanly terminated after test completes
   - Each server type tested sequentially (one at a time)

2. **Process Isolation** (✅ No GIL Interference):
   - **Server Process**: Runs independently from client
   - **Client Process**: Runs 128+ concurrent threads without GIL from server
   - **Benefits**: True parallelism, accurate metrics, production-like environment

3. **Server Threading Models**:
   - **RPyC ThreadedServer**: New thread per client connection (in server process)
   - **RPyC ForkingServer**: Fork new process per client (from server process)
   - **HTTP ThreadedServer**: Flask handles requests in threads (in server process)

4. **Client Concurrency**:
   - Default: **128 concurrent connections** from single client process
   - Each connection runs in own thread within client process
   - Configurable: Test with any number of concurrent clients
   - Per-connection metrics tracking available

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

### 4. Binary File Transfer Benchmark
Measures large file transfer performance:
- Default file sizes: 1.5MB, 128MB, 500MB
- Single chunk size per run (default: 64KB)
- Tests both chunked and non-chunked transfers
- Run multiple times with different chunk sizes to compare

### 5. Concurrent Benchmark
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
  Success Rate: 100.00%
```

### JSON Output

```json
{
  "rpyc_threaded": {
    "name": "RPyC Latency (threaded)",
    "protocol": "rpyc",
    "server_mode": "threaded",
    "latency": {
      "mean": 0.00234,
      "median": 0.00210,
      "p95": 0.00356,
      "p99": 0.00423
    }
  }
}
```

---

# Architecture

```
rpycbench/
├── core/
│   ├── benchmark.py      # Benchmark classes and context managers
│   └── metrics.py        # Metrics collection and statistics
├── servers/
│   ├── rpyc_servers.py   # RPyC server implementations
│   └── http_servers.py   # HTTP/REST server implementations
├── benchmarks/
│   └── suite.py          # Complete benchmark suite
├── runners/
│   └── autonomous.py     # CLI entry point
└── utils/
    ├── telemetry.py      # RPyC telemetry tracking
    ├── profiler.py       # Connection profiling
    └── visualizer.py     # Telemetry visualization
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

### Running Tests

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest rpycbench/tests/

# Run with coverage
pytest rpycbench/tests/ --cov=rpycbench --cov-report=html
```

Contributions are welcome! Please feel free to submit pull requests.

## License

See LICENSE file for details.
