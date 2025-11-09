# RPyCBench Python API Cookbook

## Table of Contents

- [Diagnosis and Profiling](#diagnosis-and-profiling)
  - [Diagnostic Flowchart: "My RPyC Performance is Bad"](#diagnostic-flowchart-my-rpyc-performance-is-bad)
  - [Identify Why a Specific Method is Slow](#identify-why-a-specific-method-is-slow)
  - [Find Excessive Network Round Trips](#find-excessive-network-round-trips)
  - [Detect NetRef Overhead](#detect-netref-overhead)
  - [Monitor Deep Call Stack Issues](#monitor-deep-call-stack-issues)
  - [Compare Before and After Optimization](#compare-before-and-after-optimization)
- [Benchmarking Patterns](#benchmarking-patterns)
  - [Measure Connection Overhead](#measure-connection-overhead)
  - [Measure Request Latency Distribution](#measure-request-latency-distribution)
  - [Test Bandwidth for Different Payload Sizes](#test-bandwidth-for-different-payload-sizes)
  - [Benchmark Concurrent Client Performance](#benchmark-concurrent-client-performance)
  - [Test Large File Transfer Performance](#test-large-file-transfer-performance)
- [Application Integration](#application-integration)
  - [Add Lightweight Profiling to Production Code](#add-lightweight-profiling-to-production-code)
  - [Track Specific Operations with Context Manager](#track-specific-operations-with-context-manager)
  - [Implement Performance Monitoring Dashboard](#implement-performance-monitoring-dashboard)
  - [Alert on Performance Degradation](#alert-on-performance-degradation)
- [Optimization Techniques](#optimization-techniques)
  - [Reduce Round Trips by Batching](#reduce-round-trips-by-batching)
  - [Eliminate NetRef Overhead](#eliminate-netref-overhead)
  - [Flatten Deep Call Stacks](#flatten-deep-call-stacks)
  - [Optimize Chunk Sizes for Large Transfers](#optimize-chunk-sizes-for-large-transfers)
  - [Diagnose CPU-bound vs I/O-bound Bottlenecks](#diagnose-cpu-bound-vs-io-bound-bottlenecks)
  - [Detect Server vs Client Bottlenecks](#detect-server-vs-client-bottlenecks)
  - [Choose the Right Server Mode](#choose-the-right-server-mode)
- [Testing and Validation](#testing-and-validation)
  - [Regression Test Performance](#regression-test-performance)
  - [Compare RPyC vs HTTP for Your Use Case](#compare-rpyc-vs-http-for-your-use-case)
  - [Test Remote Server Performance](#test-remote-server-performance)
  - [Validate Optimization Impact](#validate-optimization-impact)

---

## Diagnosis and Profiling

### Diagnostic Flowchart: "My RPyC Performance is Bad"

Use this decision tree to systematically diagnose performance issues:

```
START: Poor RPyC Performance
│
├─► Check Success Rate (metrics.failed_requests / metrics.total_requests)
│   │
│   ├─► < 95% success rate?
│   │   └─► SERVER EXHAUSTION
│   │       Actions:
│   │       - Check server logs for connection errors
│   │       - Increase ulimits: ulimit -n 65536
│   │       - Reduce num_clients
│   │       - Implement connection pooling
│   │
│   └─► ≥ 95% success rate → Continue
│
├─► Measure Concurrent Performance (use ConcurrentBenchmark)
│   │
│   ├─► Calculate P99/P50 ratio
│   │   │
│   │   ├─► Ratio > 10?
│   │   │   └─► SEVERE RESOURCE CONTENTION
│   │   │       Check CPU usage → If high: GIL contention
│   │   │       Check CPU usage → If low: I/O bottleneck
│   │   │
│   │   └─► Ratio < 5 → Consistent performance, check absolute latency
│   │
│   └─► Check CPU Usage (stats['cpu_usage']['mean'])
│       │
│       ├─► CPU > 80%?
│       │   └─► HIGH CPU USAGE
│       │       │
│       │       ├─► P99/P50 > 5?
│       │       │   └─► GIL CONTENTION (threaded mode)
│       │       │       Actions:
│       │       │       - Switch to server_mode='forking'
│       │       │       - Verify CPU-bound workload (hashing, computation)
│       │       │       - Expected: Multi-core CPU usage in forking mode
│       │       │
│       │       └─► P99/P50 < 3
│       │           └─► SERVER AT CAPACITY (but stable)
│       │               Actions:
│       │               - Scale horizontally (more servers)
│       │               - Optimize hot code paths
│       │               - Profile CPU-intensive operations
│       │
│       └─► CPU < 30%?
│           └─► LOW CPU USAGE
│               │
│               ├─► P99 > 100ms?
│               │   └─► I/O BOTTLENECK
│               │       Actions:
│               │       - Profile database queries (add indexes, optimize)
│               │       - Check network latency to backend services
│               │       - Implement connection pooling
│               │       - Consider async I/O
│               │       - Threaded mode is fine (GIL released during I/O)
│               │
│               └─► P99 < 100ms
│                   └─► NETWORK LATENCY
│                       - Check geographic distance client ↔ server
│                       - Measure baseline latency (LatencyBenchmark)
│                       - Reduce round trips (batch operations)
│
└─► Profile Individual Calls (use profile_rpyc_calls)
    │
    ├─► stats['total_calls'] > 100?
    │   └─► EXCESSIVE ROUND TRIPS
    │       Actions:
    │       - Batch multiple calls into one
    │       - Return all needed data in single call
    │       - See "Reduce Round Trips by Batching" pattern
    │
    ├─► stats['netrefs_created'] > 20?
    │   └─► NETREF OVERHEAD
    │       Actions:
    │       - Return dicts instead of objects
    │       - Use rpyc.utils.classic.obtain() to copy objects
    │       - See "Eliminate NetRef Overhead" pattern
    │
    └─► stats['max_stack_depth'] > 3?
        └─► DEEP CALL NESTING
            Actions:
            - Flatten remote call structure
            - Move nested logic server-side
            - See "Flatten Deep Call Stacks" pattern
```

**Quick Reference Table**:

| Symptom | Root Cause | Action |
|---------|-----------|--------|
| Success rate < 95% | Server exhaustion | Increase ulimits, reduce load |
| CPU > 80% + P99/P50 > 5 | GIL contention | Switch to forking mode |
| CPU < 30% + P99 > 100ms | I/O bottleneck | Optimize I/O, connection pooling |
| P99/P50 > 10 | Resource contention | Check CPU, try forking, scale |
| total_calls > 100 | Excessive round trips | Batch calls, return all data at once |
| netrefs_created > 20 | NetRef overhead | Return primitives, use obtain() |
| max_stack_depth > 3 | Deep call nesting | Flatten structure, server-side logic |

### Identify Why a Specific Method is Slow

**Problem**: A specific RPyC method takes several seconds but you don't know why.

**Solution**:

```python
import rpyc
from rpycbench.utils.profiler import profile_rpyc_calls, RPyCTelemetry
from rpycbench.utils.visualizer import (
    format_call_tree,
    format_slow_calls_report,
    format_netref_report
)

# Custom telemetry to catch moderately slow calls
telemetry = RPyCTelemetry(
    slow_call_threshold=0.05,  # Flag calls > 50ms
    deep_stack_threshold=3,    # Flag stacks > 3 deep
    track_netrefs=True,
    track_stacks=True
)

conn = rpyc.connect('localhost', 18812)

with profile_rpyc_calls(conn, telemetry_inst=telemetry) as profiled:
    result = profiled.root.process_large_dataset(dataset_id)

# Print comprehensive diagnosis
print("\n=== SLOW CALLS ===")
print(format_slow_calls_report(telemetry, top_n=20))

print("\n=== CALL TREE ===")
print(format_call_tree(telemetry, show_netrefs=True))

print("\n=== NETREF REPORT ===")
print(format_netref_report(telemetry))

# Get statistics
stats = telemetry.get_statistics()
print(f"\nDiagnosis Summary:")
print(f"  Total calls: {stats['total_calls']}")
print(f"  Network round trips: {stats['total_calls']}")
print(f"  Slow calls: {stats['slow_calls']}")
print(f"  NetRefs created: {stats['netrefs_created']}")
print(f"  Max stack depth: {stats['max_stack_depth']}")

# Identify the problem
if stats['total_calls'] > 100:
    print("\n  PROBLEM: Excessive round trips - consider batching calls")
if stats['netrefs_created'] > 20:
    print("  PROBLEM: NetRef overhead - return primitives instead of objects")
if stats['max_stack_depth'] > 3:
    print("  PROBLEM: Deep call nesting - flatten structure or move logic server-side")
```

**Expected output**:
```
=== SLOW CALLS ===
Top 20 Slow Calls (threshold: 50.0ms)
  1. fetch_record: 234.5ms (called 156 times, 36.6s total)
  2. validate_data: 87.3ms (called 156 times, 13.6s total)
  3. calculate_metrics: 45.2ms (called 1 time, 45.2ms total)

PROBLEM: Excessive round trips - consider batching calls
```

### Find Excessive Network Round Trips

**Problem**: Your operation is making hundreds of network calls when it should make one or two.

**Solution**:

```python
import rpyc
from rpycbench.utils.profiler import profile_rpyc_calls

conn = rpyc.connect('localhost', 18812)

with profile_rpyc_calls(conn) as profiled:
    # Your operation
    users = profiled.root.get_users()
    for user in users:
        # ANTI-PATTERN: Each iteration makes a network call
        email = user.email  # Network call
        name = user.name    # Network call
        status = user.status  # Network call

stats = profiled.telemetry.get_statistics()
print(f"Total round trips: {stats['total_calls']}")

# If you see 300+ calls for 100 users, you have the problem
# Fix: Return primitive data instead
```

**Fix**:

```python
# Server-side: Return dict instead of objects
class MyService(rpyc.Service):
    def exposed_get_users(self):
        users = fetch_users_from_db()
        # Return primitive data, not objects
        return [
            {'email': u.email, 'name': u.name, 'status': u.status}
            for u in users
        ]

# Client-side: Now this is just 1 network call
conn = rpyc.connect('localhost', 18812)
users = conn.root.get_users()  # Single call returns all data
for user in users:
    email = user['email']  # Local dict access, no network
    name = user['name']    # Local dict access, no network
    status = user['status']  # Local dict access, no network
```

### Detect NetRef Overhead

**Problem**: You're not sure if NetRefs are causing performance issues.

**Solution**:

```python
import rpyc
from rpycbench.utils.profiler import profile_rpyc_calls
from rpycbench.utils.visualizer import format_netref_report

telemetry = RPyCTelemetry(track_netrefs=True)
conn = rpyc.connect('localhost', 18812)

with profile_rpyc_calls(conn, telemetry_inst=telemetry) as profiled:
    result = profiled.root.your_operation()

print(format_netref_report(telemetry))

stats = telemetry.get_statistics()
if stats['netrefs_created'] > 0:
    print(f"\nWARNING: {stats['netrefs_created']} NetRefs created")
    print("Each NetRef access causes a network round trip")
    print("Consider using rpyc.utils.classic.obtain() to copy objects locally")
```

**Fix options**:

```python
import rpyc
from rpyc.utils.classic import obtain

conn = rpyc.connect('localhost', 18812)

# Option 1: Use obtain() to copy the entire object tree locally
user = obtain(conn.root.get_user(123))
# Now user is a local object, all attribute access is local
email = user.email  # No network call
name = user.name    # No network call

# Option 2: Return primitive data from server (preferred)
user_dict = conn.root.get_user_dict(123)  # Server returns dict
email = user_dict['email']  # Local access
name = user_dict['name']    # Local access
```

### Monitor Deep Call Stack Issues

**Problem**: Remote methods are calling other remote methods, creating latency multiplication.

**Solution**:

```python
import rpyc
from rpycbench.utils.profiler import profile_rpyc_calls
from rpycbench.utils.visualizer import format_call_tree

telemetry = RPyCTelemetry(
    track_stacks=True,
    deep_stack_threshold=3  # Warn when depth > 3
)

conn = rpyc.connect('localhost', 18812)

with profile_rpyc_calls(conn, telemetry_inst=telemetry) as profiled:
    result = profiled.root.complex_operation()

# Visualize call nesting
print(format_call_tree(telemetry, max_depth=None))

stats = telemetry.get_statistics()
if stats['max_stack_depth'] > 3:
    print(f"\nWARNING: Max call depth of {stats['max_stack_depth']}")
    print("Each level adds network latency - consider flattening")
```

**Fix**:

```python
# BEFORE: Nested remote calls (4x network latency)
class MyService(rpyc.Service):
    def exposed_method_a(self):
        return self.exposed_method_b()  # Remote call

    def exposed_method_b(self):
        return self.exposed_method_c()  # Remote call

    def exposed_method_c(self):
        return self.exposed_method_d()  # Remote call

    def exposed_method_d(self):
        return "result"

# AFTER: Flat call (1x network latency)
class MyService(rpyc.Service):
    def exposed_method_a(self):
        # Do all the work in one method
        result_b = self._internal_method_b()  # Local call
        result_c = self._internal_method_c(result_b)  # Local call
        result_d = self._internal_method_d(result_c)  # Local call
        return result_d

    def _internal_method_b(self):
        return "step_b"

    def _internal_method_c(self, input_b):
        return "step_c"

    def _internal_method_d(self, input_c):
        return "result"
```

### Compare Before and After Optimization

**Problem**: You made changes but want to verify they actually improved performance.

**Solution**:

```python
from rpycbench.core.benchmark import LatencyBenchmark
from rpycbench.core.metrics import BenchmarkResults
import rpyc

def test_old_implementation(conn):
    return conn.root.old_method()

def test_new_implementation(conn):
    return conn.root.new_method()

# Benchmark old implementation
old_bench = LatencyBenchmark(
    name="old_implementation",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=test_old_implementation,
    num_requests=1000
)

# Benchmark new implementation
new_bench = LatencyBenchmark(
    name="new_implementation",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=test_new_implementation,
    num_requests=1000
)

old_metrics = old_bench.run()
new_metrics = new_bench.run()

# Compare results
results = BenchmarkResults()
results.add_result(old_metrics)
results.add_result(new_metrics)
results.print_summary()

# Calculate improvement
old_stats = old_metrics.compute_statistics()
new_stats = new_metrics.compute_statistics()

improvement = ((old_stats['latency']['mean'] - new_stats['latency']['mean'])
               / old_stats['latency']['mean'] * 100)

print(f"\nPerformance improvement: {improvement:.1f}%")
print(f"Old P99: {old_stats['latency']['p99']*1000:.2f}ms")
print(f"New P99: {new_stats['latency']['p99']*1000:.2f}ms")
```

---

## Benchmarking Patterns

### Measure Connection Overhead

**Problem**: Need to know how long it takes to establish RPyC connections.

**Solution**:

```python
from rpycbench.core.benchmark import ConnectionBenchmark
import rpyc

bench = ConnectionBenchmark(
    name="connection_time",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812, config={
        'allow_public_attrs': True,
        'sync_request_timeout': 30
    }),
    num_connections=100
)

metrics = bench.run()
stats = metrics.compute_statistics()

print(f"Connection time statistics:")
print(f"  Mean: {stats['connection_time']['mean']*1000:.2f}ms")
print(f"  Median: {stats['connection_time']['median']*1000:.2f}ms")
print(f"  P95: {stats['connection_time']['p95']*1000:.2f}ms")
print(f"  P99: {stats['connection_time']['p99']*1000:.2f}ms")
print(f"  Min: {stats['connection_time']['min']*1000:.2f}ms")
print(f"  Max: {stats['connection_time']['max']*1000:.2f}ms")

# If P99 > 100ms, consider connection pooling
if stats['connection_time']['p99'] > 0.1:
    print("\nRECOMMENDATION: Connection time is high, use connection pooling")
```

### Measure Request Latency Distribution

**Problem**: Need to understand the latency distribution of your RPyC calls, especially tail latency.

**Solution**:

```python
from rpycbench.core.benchmark import LatencyBenchmark
import rpyc

def my_operation(conn):
    return conn.root.fetch_data(query_id=123)

bench = LatencyBenchmark(
    name="data_fetch",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=my_operation,
    num_requests=10000,  # Large sample for accurate distribution
    warmup_requests=100  # Exclude warmup from stats
)

metrics = bench.run()
stats = metrics.compute_statistics()

print(f"Latency distribution for {metrics.total_requests} requests:")
print(f"  Mean: {stats['latency']['mean']*1000:.2f}ms")
print(f"  Median (P50): {stats['latency']['median']*1000:.2f}ms")
print(f"  P95: {stats['latency']['p95']*1000:.2f}ms")
print(f"  P99: {stats['latency']['p99']*1000:.2f}ms")
print(f"  Max: {stats['latency']['max']*1000:.2f}ms")
print(f"  Std Dev: {stats['latency']['stdev']*1000:.2f}ms")

# Check for tail latency issues
if stats['latency']['p99'] > stats['latency']['median'] * 5:
    print("\nWARNING: High tail latency (P99 >> P50)")
    print("This indicates inconsistent performance - investigate outliers")
```

### Test Bandwidth for Different Payload Sizes

**Problem**: Need to understand how payload size affects transfer performance.

**Solution**:

```python
from rpycbench.core.benchmark import BandwidthBenchmark
import rpyc

# Define data sizes to test
data_sizes = [
    1024,           # 1 KB
    10 * 1024,      # 10 KB
    100 * 1024,     # 100 KB
    1024 * 1024,    # 1 MB
    10 * 1024 * 1024  # 10 MB
]

bench = BandwidthBenchmark(
    name="payload_size_test",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    upload_func=lambda c, data: c.root.receive_data(data),
    download_func=lambda c, size: c.root.send_data(size),
    data_sizes=data_sizes,
    iterations=20
)

metrics = bench.run()
stats = metrics.compute_statistics()

print(f"Upload bandwidth:")
print(f"  Mean: {stats['upload_bandwidth']['mean']/1024/1024:.2f} MB/s")
print(f"  P95: {stats['upload_bandwidth']['p95']/1024/1024:.2f} MB/s")

print(f"\nDownload bandwidth:")
print(f"  Mean: {stats['download_bandwidth']['mean']/1024/1024:.2f} MB/s")
print(f"  P95: {stats['download_bandwidth']['p95']/1024/1024:.2f} MB/s")

# Export detailed results for analysis
import json
with open('bandwidth_results.json', 'w') as f:
    json.dump(metrics.to_dict(), f, indent=2)
```

### Benchmark Concurrent Client Performance

**Problem**: Need to test how your RPyC server handles many simultaneous clients.

**Solution**:

```python
from rpycbench.core.benchmark import ConcurrentBenchmark
import rpyc

def client_workload(conn):
    # Simulate realistic client workload
    conn.root.authenticate(user_id=123)
    data = conn.root.fetch_user_data()
    conn.root.update_status("active")
    return data

# Test increasing concurrency levels
for num_clients in [10, 50, 100, 200, 500]:
    bench = ConcurrentBenchmark(
        name=f"{num_clients}_clients",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18812),
        request_func=client_workload,
        num_clients=num_clients,
        requests_per_client=50,
        track_per_connection=False  # Set True to debug individual connections
    )

    metrics = bench.run()
    stats = metrics.compute_statistics()

    success_rate = (1 - metrics.failed_requests/metrics.total_requests) * 100

    print(f"\n{num_clients} concurrent clients:")
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  Mean latency: {stats['latency']['mean']*1000:.2f}ms")
    print(f"  P99 latency: {stats['latency']['p99']*1000:.2f}ms")
    print(f"  Total requests: {metrics.total_requests}")
    print(f"  Failed requests: {metrics.failed_requests}")

    # Stop if performance degrades significantly
    if success_rate < 95 or stats['latency']['p99'] > 5.0:
        print(f"\n  LIMIT REACHED at {num_clients} clients")
        break
```

### Test Large File Transfer Performance

**Problem**: Need to optimize large file transfers and find the best chunk size.

**Solution**:

```python
from rpycbench.core.benchmark import BinaryTransferBenchmark
import rpyc

# Test different chunk sizes
for chunk_size in [16*1024, 64*1024, 256*1024, 1024*1024]:
    bench = BinaryTransferBenchmark(
        name=f"chunk_{chunk_size//1024}kb",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18812),
        upload_func=lambda c, data: c.root.upload_file(data),
        download_func=lambda c, size: c.root.download_file(size),
        upload_chunked_func=lambda c, chunks: c.root.upload_chunked(chunks),
        download_chunked_func=lambda c, size, cs: c.root.download_chunked(size, cs),
        file_sizes=[10*1024*1024, 100*1024*1024],  # 10MB, 100MB
        chunk_size=chunk_size,
        iterations=5,
        test_upload=True,
        test_download=True,
        test_chunked=True
    )

    metrics = bench.run()
    stats = metrics.compute_statistics()

    print(f"\nChunk size: {chunk_size//1024}KB")
    print(f"  Upload: {stats['upload_bandwidth']['mean']/1024/1024:.2f} MB/s")
    print(f"  Download: {stats['download_bandwidth']['mean']/1024/1024:.2f} MB/s")
```

---

## Application Integration

### Add Lightweight Profiling to Production Code

**Problem**: Want to monitor RPyC performance in production without significant overhead.

**Solution**:

```python
import rpyc
from rpycbench.utils.profiler import RPyCTelemetry, ProfiledConnection
import logging

# Global telemetry instance with conservative settings
telemetry = RPyCTelemetry(
    enabled=True,
    track_netrefs=False,  # Disable for lower overhead
    track_stacks=False,   # Disable for lower overhead
    slow_call_threshold=1.0  # Only track calls > 1 second
)

def create_monitored_connection(host, port):
    """Connection factory with built-in monitoring"""
    base_conn = rpyc.connect(host, port)
    return ProfiledConnection(
        base_conn,
        telemetry_inst=telemetry,
        auto_print_on_slow=True,  # Log slow calls automatically
        auto_print_on_deep=False
    )

# Use in application
conn = create_monitored_connection('localhost', 18812)

try:
    result = conn.root.important_operation()
finally:
    # Periodic reporting (e.g., every 1000 requests)
    stats = telemetry.get_statistics()
    if stats['total_calls'] % 1000 == 0:
        logging.info(f"RPyC stats: {stats['total_calls']} calls, "
                     f"{stats['slow_calls']} slow calls")
    conn.close()
```

### Track Specific Operations with Context Manager

**Problem**: Want to measure specific operations in your application code.

**Solution**:

```python
from rpycbench.core.benchmark import BenchmarkContext
import rpyc

conn = rpyc.connect('localhost', 18812)

# Create context for each logical operation
user_ctx = BenchmarkContext(
    name="user_operations",
    protocol="rpyc",
    measure_latency=True,
    measure_system=True
)

order_ctx = BenchmarkContext(
    name="order_operations",
    protocol="rpyc",
    measure_latency=True,
    measure_system=True
)

# Track user operations
with user_ctx.measure_request(bytes_sent=512, bytes_received=4096):
    user = conn.root.get_user(user_id=123)
    user_ctx.record_request(success=True)

# Track order operations
with order_ctx.measure_request(bytes_sent=2048, bytes_received=8192):
    try:
        order = conn.root.create_order(user_id=123, items=[...])
        order_ctx.record_request(success=True)
    except Exception:
        order_ctx.record_request(success=False)

# Analyze results
user_stats = user_ctx.get_results().compute_statistics()
order_stats = order_ctx.get_results().compute_statistics()

print(f"User operations: {user_stats['latency']['mean']*1000:.2f}ms avg")
print(f"Order operations: {order_stats['latency']['mean']*1000:.2f}ms avg")
```

### Implement Performance Monitoring Dashboard

**Problem**: Want to collect and visualize RPyC performance metrics over time.

**Solution**:

```python
from rpycbench.core.benchmark import BenchmarkContext
from rpycbench.core.metrics import BenchmarkMetrics
import json
import time
from datetime import datetime

class PerformanceMonitor:
    def __init__(self, output_file='metrics.jsonl'):
        self.output_file = output_file
        self.contexts = {}

    def get_context(self, operation_name):
        if operation_name not in self.contexts:
            self.contexts[operation_name] = BenchmarkContext(
                name=operation_name,
                protocol="rpyc",
                measure_latency=True,
                measure_system=True
            )
        return self.contexts[operation_name]

    def track_operation(self, operation_name, func, *args, **kwargs):
        ctx = self.get_context(operation_name)

        start_time = time.time()
        try:
            with ctx.measure_request(bytes_sent=0, bytes_received=0):
                result = func(*args, **kwargs)
                ctx.record_request(success=True)
            return result
        except Exception as e:
            ctx.record_request(success=False)
            raise

    def flush_metrics(self):
        """Write metrics to file in JSON Lines format"""
        timestamp = datetime.utcnow().isoformat()

        with open(self.output_file, 'a') as f:
            for name, ctx in self.contexts.items():
                metrics = ctx.get_results()
                stats = metrics.compute_statistics()

                record = {
                    'timestamp': timestamp,
                    'operation': name,
                    'stats': stats,
                    'total_requests': metrics.total_requests,
                    'failed_requests': metrics.failed_requests
                }
                f.write(json.dumps(record) + '\n')

# Usage
monitor = PerformanceMonitor()

conn = rpyc.connect('localhost', 18812)

# Automatic tracking
result = monitor.track_operation('get_user', conn.root.get_user, 123)
result = monitor.track_operation('create_order', conn.root.create_order, {...})

# Periodic flushing (e.g., every minute)
import threading

def periodic_flush():
    monitor.flush_metrics()
    threading.Timer(60, periodic_flush).start()

periodic_flush()
```

### Alert on Performance Degradation

**Problem**: Want to be notified when RPyC performance degrades.

**Solution**:

```python
from rpycbench.core.benchmark import LatencyBenchmark
import rpyc
import smtplib
from email.message import EmailMessage

class PerformanceWatchdog:
    def __init__(self, baseline_p99_ms=50):
        self.baseline_p99 = baseline_p99_ms / 1000  # Convert to seconds
        self.alert_threshold = self.baseline_p99 * 2  # Alert if 2x baseline

    def check_performance(self):
        bench = LatencyBenchmark(
            name="health_check",
            protocol="rpyc",
            server_mode="threaded",
            connection_factory=lambda: rpyc.connect('localhost', 18812),
            request_func=lambda c: c.root.health_check(),
            num_requests=100
        )

        metrics = bench.run()
        stats = metrics.compute_statistics()

        current_p99 = stats['latency']['p99']

        if current_p99 > self.alert_threshold:
            self.send_alert(
                f"RPyC performance degraded: "
                f"P99 latency {current_p99*1000:.2f}ms "
                f"(baseline: {self.baseline_p99*1000:.2f}ms)"
            )
            return False

        return True

    def send_alert(self, message):
        # Send email, page, or log alert
        print(f"ALERT: {message}")
        # Implement your alerting mechanism here

# Run periodically
watchdog = PerformanceWatchdog(baseline_p99_ms=50)

import schedule
schedule.every(5).minutes.do(watchdog.check_performance)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Optimization Techniques

### Reduce Round Trips by Batching

**Problem**: Making many small RPyC calls instead of batching them.

**Before**:

```python
# SLOW: 100 network round trips
conn = rpyc.connect('localhost', 18812)
for user_id in range(100):
    user = conn.root.get_user(user_id)
    print(user)
```

**After**:

```python
# FAST: 1 network round trip
conn = rpyc.connect('localhost', 18812)
users = conn.root.get_users_batch(list(range(100)))
for user in users:
    print(user)
```

**Server implementation**:

```python
class MyService(rpyc.Service):
    def exposed_get_users_batch(self, user_ids):
        # Fetch all users in one database query
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        # Return primitive data, not objects
        return [
            {'id': u.id, 'name': u.name, 'email': u.email}
            for u in users
        ]
```

**Verify improvement**:

```python
from rpycbench.utils.profiler import profile_rpyc_calls

# Measure before
with profile_rpyc_calls(conn) as profiled:
    for user_id in range(100):
        user = profiled.root.get_user(user_id)

before_stats = profiled.telemetry.get_statistics()
print(f"Before: {before_stats['total_calls']} round trips")

# Measure after
profiled.telemetry.reset()
with profile_rpyc_calls(conn) as profiled:
    users = profiled.root.get_users_batch(list(range(100)))

after_stats = profiled.telemetry.get_statistics()
print(f"After: {after_stats['total_calls']} round trips")
print(f"Reduction: {(1 - after_stats['total_calls']/before_stats['total_calls'])*100:.0f}%")
```

### Eliminate NetRef Overhead

**Problem**: Returning objects creates NetRefs which cause network overhead on every attribute access.

**Before**:

```python
# Server
class User:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

class MyService(rpyc.Service):
    def exposed_get_user(self, user_id):
        return User(user_id, "John", "john@example.com")  # Returns object

# Client (SLOW)
conn = rpyc.connect('localhost', 18812)
user = conn.root.get_user(123)  # 1 network call
name = user.name   # NETWORK CALL!
email = user.email  # NETWORK CALL!
```

**After**:

```python
# Server
class MyService(rpyc.Service):
    def exposed_get_user(self, user_id):
        user = fetch_user_from_db(user_id)
        # Return dict, not object
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email
        }

# Client (FAST)
conn = rpyc.connect('localhost', 18812)
user = conn.root.get_user(123)  # 1 network call
name = user['name']   # Local dict access
email = user['email']  # Local dict access
```

**Alternative using obtain()**:

```python
from rpyc.utils.classic import obtain

# If you can't change the server
conn = rpyc.connect('localhost', 18812)
user = obtain(conn.root.get_user(123))  # Copies entire object tree locally
name = user.name   # Local access
email = user.email  # Local access
```

### Flatten Deep Call Stacks

**Problem**: Remote methods calling other remote methods creates latency multiplication.

**Before**:

```python
# Server with nested remote calls
class MyService(rpyc.Service):
    def exposed_get_user_report(self, user_id):
        user = self.exposed_get_user(user_id)  # Call 1
        orders = self.exposed_get_orders(user_id)  # Call 2
        metrics = self.exposed_calculate_metrics(user, orders)  # Call 3
        return metrics

    def exposed_get_user(self, user_id):
        return db.query(User).get(user_id)

    def exposed_get_orders(self, user_id):
        return db.query(Order).filter_by(user_id=user_id).all()

    def exposed_calculate_metrics(self, user, orders):
        return {'total': len(orders), 'user': user.name}

# Client (SLOW: 4 round trips for one operation)
conn = rpyc.connect('localhost', 18812)
report = conn.root.get_user_report(123)
```

**After**:

```python
# Server with flat structure
class MyService(rpyc.Service):
    def exposed_get_user_report(self, user_id):
        # Do all work server-side with internal methods
        user = self._get_user(user_id)  # Local call
        orders = self._get_orders(user_id)  # Local call
        metrics = self._calculate_metrics(user, orders)  # Local call
        return metrics

    def _get_user(self, user_id):
        return db.query(User).get(user_id)

    def _get_orders(self, user_id):
        return db.query(Order).filter_by(user_id=user_id).all()

    def _calculate_metrics(self, user, orders):
        return {'total': len(orders), 'user': user.name}

# Client (FAST: 1 round trip)
conn = rpyc.connect('localhost', 18812)
report = conn.root.get_user_report(123)
```

### Optimize Chunk Sizes for Large Transfers

**Problem**: Default chunk sizes may not be optimal for your network conditions.

**Solution**: Benchmark different chunk sizes to find the optimum.

```python
from rpycbench.core.benchmark import BinaryTransferBenchmark
import rpyc

chunk_sizes = [
    8 * 1024,      # 8 KB
    16 * 1024,     # 16 KB
    64 * 1024,     # 64 KB (RPyC default)
    256 * 1024,    # 256 KB
    1024 * 1024,   # 1 MB
]

results = []

for chunk_size in chunk_sizes:
    bench = BinaryTransferBenchmark(
        name=f"chunk_{chunk_size//1024}kb",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18812),
        upload_func=lambda c, data: c.root.upload(data),
        download_func=lambda c, size: c.root.download(size),
        file_sizes=[100 * 1024 * 1024],  # 100 MB
        chunk_size=chunk_size,
        iterations=3
    )

    metrics = bench.run()
    stats = metrics.compute_statistics()

    throughput = stats['upload_bandwidth']['mean'] / 1024 / 1024
    results.append((chunk_size // 1024, throughput))

    print(f"Chunk {chunk_size//1024}KB: {throughput:.2f} MB/s")

# Find optimal
optimal = max(results, key=lambda x: x[1])
print(f"\nOptimal chunk size: {optimal[0]}KB ({optimal[1]:.2f} MB/s)")
```

### Diagnose CPU-bound vs I/O-bound Bottlenecks

**Problem**: Many parallel clients are slow, but you don't know if it's CPU saturation, I/O wait, or network issues.

**Solution**: Create test workloads that isolate CPU-bound vs I/O-bound behavior, then benchmark under concurrent load.

```python
import hashlib
import time
from rpycbench.core.benchmark import ConcurrentBenchmark
from rpycbench.servers.rpyc_servers import RPyCServer
import rpyc

# Server implementations
class CPUBoundService(rpyc.Service):
    def exposed_cpu_work(self, iterations=100000):
        """CPU-intensive: hash computation loop"""
        result = b"start"
        for i in range(iterations):
            result = hashlib.sha256(result).digest()
        return result.hex()[:16]

class IOBoundService(rpyc.Service):
    def exposed_io_work(self, delay=0.01):
        """I/O-bound: simulates database query or file I/O"""
        time.sleep(delay)  # Simulates I/O wait
        return "data"

# Test CPU-bound workload with THREADED mode
print("=== CPU-Bound Workload ===")
with RPyCServer(port=18812, mode='threaded') as server:
    cpu_threaded = ConcurrentBenchmark(
        name="cpu_threaded",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18812),
        request_func=lambda c: c.root.cpu_work(),
        num_clients=128,
        requests_per_client=10
    )
    cpu_threaded_metrics = cpu_threaded.run()
    cpu_threaded_metrics.record_system_metrics()  # Capture CPU/memory

cpu_threaded_stats = cpu_threaded_metrics.compute_statistics()

# Test CPU-bound workload with FORKING mode
with RPyCServer(port=18813, mode='forking') as server:
    cpu_forking = ConcurrentBenchmark(
        name="cpu_forking",
        protocol="rpyc",
        server_mode="forking",
        connection_factory=lambda: rpyc.connect('localhost', 18813),
        request_func=lambda c: c.root.cpu_work(),
        num_clients=128,
        requests_per_client=10
    )
    cpu_forking_metrics = cpu_forking.run()
    cpu_forking_metrics.record_system_metrics()

cpu_forking_stats = cpu_forking_metrics.compute_statistics()

# Test I/O-bound workload with THREADED mode
print("\n=== I/O-Bound Workload ===")
with RPyCServer(port=18814, mode='threaded') as server:
    io_threaded = ConcurrentBenchmark(
        name="io_threaded",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18814),
        request_func=lambda c: c.root.io_work(),
        num_clients=128,
        requests_per_client=10
    )
    io_threaded_metrics = io_threaded.run()
    io_threaded_metrics.record_system_metrics()

io_threaded_stats = io_threaded_metrics.compute_statistics()

# Test I/O-bound workload with FORKING mode
with RPyCServer(port=18815, mode='forking') as server:
    io_forking = ConcurrentBenchmark(
        name="io_forking",
        protocol="rpyc",
        server_mode="forking",
        connection_factory=lambda: rpyc.connect('localhost', 18815),
        request_func=lambda c: c.root.io_work(),
        num_clients=128,
        requests_per_client=10
    )
    io_forking_metrics = io_forking.run()
    io_forking_metrics.record_system_metrics()

io_forking_stats = io_forking_metrics.compute_statistics()

# Compare results
print("\nCPU-Bound Results:")
print(f"  Threaded: {cpu_threaded_stats['latency']['mean']*1000:.2f}ms avg, "
      f"CPU: {cpu_threaded_stats['cpu_usage']['mean']:.1f}%")
print(f"  Forking:  {cpu_forking_stats['latency']['mean']*1000:.2f}ms avg, "
      f"CPU: {cpu_forking_stats['cpu_usage']['mean']:.1f}%")
print(f"  Improvement: {(1 - cpu_forking_stats['latency']['mean']/cpu_threaded_stats['latency']['mean'])*100:.1f}%")

print("\nI/O-Bound Results:")
print(f"  Threaded: {io_threaded_stats['latency']['mean']*1000:.2f}ms avg, "
      f"CPU: {io_threaded_stats['cpu_usage']['mean']:.1f}%")
print(f"  Forking:  {io_forking_stats['latency']['mean']*1000:.2f}ms avg, "
      f"CPU: {io_forking_stats['cpu_usage']['mean']:.1f}%")
print(f"  Difference: {((io_forking_stats['latency']['mean']/io_threaded_stats['latency']['mean'])-1)*100:.1f}%")
```

**Interpretation Guide**:

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| CPU-bound threaded: High single-core CPU (80-100%), poor scaling | **GIL contention** - Python's Global Interpreter Lock prevents parallel execution | Switch to forking mode |
| CPU-bound forking: Multi-core CPU usage, much faster than threaded | Proper parallelization, **no GIL** | Keep forking mode |
| I/O-bound: Low CPU usage (< 30%), high latency | **I/O wait time** dominates | Threaded is fine, optimize I/O operations |
| I/O-bound: Similar performance in both modes | I/O wait, not CPU, is bottleneck | Use threaded (lower memory overhead) |
| High P99 >> P50 in threaded mode | Resource contention / GIL queuing | Try forking or reduce concurrency |

**Key Insight**:
- **CPU-bound + threaded = GIL wall**: Only one thread executes Python code at a time, others wait
- **I/O-bound + threaded = good**: During I/O wait, GIL is released, other threads can run
- **Forking bypasses GIL**: Each process has its own Python interpreter, but costs more memory

### Detect Server vs Client Bottlenecks

**Problem**: Poor concurrent performance, but unclear if the server or clients are the bottleneck.

**Solution**: Use per-connection tracking and analyze patterns.

```python
from rpycbench.core.benchmark import ConcurrentBenchmark
import rpyc

# Enable per-connection tracking
bench = ConcurrentBenchmark(
    name="bottleneck_diagnosis",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=lambda c: c.root.some_method(),
    num_clients=128,
    requests_per_client=100,
    track_per_connection=True  # Track individual client performance
)

metrics = bench.run()
stats = metrics.compute_statistics()

# Analyze patterns
success_rate = (1 - metrics.failed_requests / metrics.total_requests) * 100
p50 = stats['latency']['median']
p99 = stats['latency']['p99']
ratio = p99 / p50 if p50 > 0 else 0

print(f"Overall Metrics:")
print(f"  Success rate: {success_rate:.1f}%")
print(f"  P50 latency: {p50*1000:.2f}ms")
print(f"  P99 latency: {p99*1000:.2f}ms")
print(f"  P99/P50 ratio: {ratio:.1f}x")
print(f"  CPU usage: {stats['cpu_usage']['mean']:.1f}%")
print(f"  Memory usage: {stats['memory_usage']['mean']/1024/1024:.0f}MB")

# Diagnosis
print("\nDiagnosis:")

if success_rate < 95:
    print("  SERVER EXHAUSTION: < 95% success rate indicates server is dropping connections")
    print("    - Check server logs for 'too many open files' or connection errors")
    print("    - Increase server ulimits: ulimit -n 65536")
    print("    - Reduce num_clients or switch to connection pooling")

if ratio > 10:
    print("  RESOURCE CONTENTION: P99 >> P50 indicates inconsistent performance")
    print("    - If CPU-bound: Switch to forking mode to avoid GIL contention")
    print("    - If I/O-bound: Server may be hitting I/O limits (file descriptors, database connections)")
    print("    - Check server-side resource usage separately")

if stats['cpu_usage']['mean'] > 80:
    print("  CPU SATURATION: High CPU usage indicates compute bottleneck")
    if ratio > 5:
        print("    - Likely GIL contention in threaded mode")
        print("    - Try forking mode or optimize CPU-intensive operations")
    else:
        print("    - Server handling load but at capacity")
        print("    - Scale horizontally or optimize hot code paths")

if stats['cpu_usage']['mean'] < 30 and p99 > 0.1:
    print("  I/O BOTTLENECK: Low CPU + high latency = waiting on I/O")
    print("    - Profile database queries or external API calls")
    print("    - Consider async I/O or connection pooling")
    print("    - Check network latency between server and backend services")

# Per-connection analysis (if track_per_connection=True)
if hasattr(metrics, 'per_connection_latencies'):
    import statistics
    conn_means = [statistics.mean(latencies) for latencies in metrics.per_connection_latencies if latencies]
    conn_variance = statistics.stdev(conn_means) if len(conn_means) > 1 else 0

    print(f"\nPer-Connection Variance: {conn_variance*1000:.2f}ms")

    if conn_variance > p50 * 0.5:
        print("  CLIENT/NETWORK ISSUE: High variance between connections")
        print("    - Some clients experiencing much worse performance than others")
        print("    - Check client-side resource limits or network path diversity")
    else:
        print("  SERVER BOTTLENECK: All clients affected equally")
        print("    - Server-side issue affecting all connections uniformly")
```

**Pattern Recognition**:

| Pattern | Root Cause | Action |
|---------|-----------|--------|
| All clients slow uniformly, P99/P50 < 3 | Server at steady capacity | Scale server or optimize operations |
| Random clients slow, high variance | Client or network issues | Investigate client-side resources, network paths |
| Increasing slowdown with more clients | Server resource exhaustion | Check CPU, memory, file descriptors; reduce concurrency |
| < 95% success rate | Connection/port exhaustion | Increase ulimits, use connection pooling |
| High CPU + high P99/P50 | GIL contention (threaded mode) | Switch to forking for CPU-bound work |
| Low CPU + high latency | I/O wait (database, disk, network) | Optimize I/O operations, consider async |

### Choose the Right Server Mode

**Problem**: Threaded server mode may not be optimal for your workload.

**Background: Understanding the Python GIL**:

Python's Global Interpreter Lock (GIL) is a mutex that protects access to Python objects, preventing multiple threads from executing Python bytecode simultaneously. This has major implications for concurrent RPyC servers:

- **Threaded mode**: All client connections share one Python interpreter with one GIL
  - **CPU-bound work**: Only one thread executes at a time → poor scaling, high latency
  - **I/O-bound work**: During I/O (network, disk, database), GIL is released → good scaling
  - **Memory efficient**: Threads share memory space

- **Forking mode**: Each client connection gets its own process with its own GIL
  - **CPU-bound work**: True parallelism, utilizes all CPU cores → excellent scaling
  - **I/O-bound work**: No better than threaded (I/O still waits) → memory overhead not worth it
  - **Memory intensive**: Each process duplicates memory

**Solution**: Benchmark different server modes and interpret CPU usage patterns.

```python
from rpycbench.core.benchmark import ConcurrentBenchmark
import rpyc

def test_workload(conn):
    return conn.root.cpu_intensive_task()

# Test threaded mode
threaded_bench = ConcurrentBenchmark(
    name="threaded",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=test_workload,
    num_clients=100,
    requests_per_client=50
)

# Test forking mode
forking_bench = ConcurrentBenchmark(
    name="forking",
    protocol="rpyc",
    server_mode="forking",
    connection_factory=lambda: rpyc.connect('localhost', 18813),  # Different port
    request_func=test_workload,
    num_clients=100,
    requests_per_client=50
)

threaded_metrics = threaded_bench.run()
forking_metrics = forking_bench.run()

threaded_stats = threaded_metrics.compute_statistics()
forking_stats = forking_metrics.compute_statistics()

print(f"Threaded mode P99: {threaded_stats['latency']['p99']*1000:.2f}ms")
print(f"Forking mode P99: {forking_stats['latency']['p99']*1000:.2f}ms")

# Recommendations:
# - Threaded: Good for I/O bound tasks, lower memory
# - Forking: Good for CPU bound tasks, isolated memory, higher overhead
```

---

## Testing and Validation

### Regression Test Performance

**Problem**: Want to ensure performance doesn't degrade in CI/CD pipeline.

**Solution**:

```python
from rpycbench.core.benchmark import LatencyBenchmark
import rpyc
import sys

def performance_test():
    bench = LatencyBenchmark(
        name="regression_test",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18812),
        request_func=lambda c: c.root.critical_operation(),
        num_requests=1000
    )

    metrics = bench.run()
    stats = metrics.compute_statistics()

    # Define performance SLA
    MAX_P99_MS = 100
    MAX_MEAN_MS = 50

    p99_ms = stats['latency']['p99'] * 1000
    mean_ms = stats['latency']['mean'] * 1000

    print(f"P99 latency: {p99_ms:.2f}ms (threshold: {MAX_P99_MS}ms)")
    print(f"Mean latency: {mean_ms:.2f}ms (threshold: {MAX_MEAN_MS}ms)")

    if p99_ms > MAX_P99_MS:
        print(f"FAIL: P99 latency {p99_ms:.2f}ms exceeds {MAX_P99_MS}ms")
        sys.exit(1)

    if mean_ms > MAX_MEAN_MS:
        print(f"FAIL: Mean latency {mean_ms:.2f}ms exceeds {MAX_MEAN_MS}ms")
        sys.exit(1)

    print("PASS: Performance within acceptable limits")
    return 0

if __name__ == '__main__':
    sys.exit(performance_test())
```

**In CI/CD** (e.g., GitHub Actions):

```yaml
- name: Run performance regression tests
  run: |
    python start_test_server.py &
    sleep 2
    python performance_regression.py
```

### Compare RPyC vs HTTP for Your Use Case

**Problem**: Evaluating whether RPyC is the right choice for your application.

**Solution**:

```python
from rpycbench.benchmarks.suite import BenchmarkSuite

suite = BenchmarkSuite(
    rpyc_host='localhost',
    rpyc_port=18812,
    http_host='localhost',
    http_port=5000
)

results = suite.run_all(
    test_rpyc_threaded=True,
    test_rpyc_forking=False,
    test_http=True,
    num_requests=1000,
    num_parallel_clients=100
)

results.print_summary()

# Analyze results
comparison = results.get_comparison_table()

rpyc_latency = comparison['rpyc_threaded']['latency_mean']
http_latency = comparison['http']['latency_mean']

if rpyc_latency < http_latency:
    print(f"\nRPyC is {(http_latency/rpyc_latency - 1)*100:.1f}% faster than HTTP")
else:
    print(f"\nHTTP is {(rpyc_latency/http_latency - 1)*100:.1f}% faster than RPyC")
    print("Consider investigating NetRef overhead and call patterns")
```

### Test Remote Server Performance

**Problem**: Need to test performance over real network conditions with remote servers.

**Solution**:

```python
from rpycbench.benchmarks.suite import BenchmarkSuite

# Test with remote server via SSH
suite = BenchmarkSuite(
    rpyc_host='remote-server.example.com',
    rpyc_port=18812,
    remote_host='user@remote-server.example.com'  # Enables SSH deployment
)

# Automatically deploys rpycbench to remote host and starts server
results = suite.run_all(
    test_rpyc_threaded=True,
    num_requests=1000
)

results.print_summary()

# Compare local vs remote performance
local_suite = BenchmarkSuite(rpyc_host='localhost', rpyc_port=18812)
local_results = local_suite.run_all(test_rpyc_threaded=True, num_requests=1000)

local_latency = local_results.results[0].compute_statistics()['latency']['mean']
remote_latency = results.results[0].compute_statistics()['latency']['mean']

network_overhead = (remote_latency - local_latency) * 1000
print(f"\nNetwork overhead: {network_overhead:.2f}ms")
```

### Validate Optimization Impact

**Problem**: Made optimizations but need to prove they work with statistical significance.

**Solution**:

```python
from rpycbench.core.benchmark import LatencyBenchmark
from rpycbench.core.metrics import BenchmarkResults
import rpyc
import scipy.stats

def benchmark_implementation(name, method_name, num_requests=1000):
    bench = LatencyBenchmark(
        name=name,
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18812),
        request_func=lambda c: getattr(c.root, method_name)(),
        num_requests=num_requests
    )
    return bench.run()

# Benchmark both implementations multiple times
before_runs = [benchmark_implementation("before", "old_method") for _ in range(5)]
after_runs = [benchmark_implementation("after", "new_method") for _ in range(5)]

# Extract latencies
before_latencies = [m.compute_statistics()['latency']['mean'] for m in before_runs]
after_latencies = [m.compute_statistics()['latency']['mean'] for m in after_runs]

# Statistical test
t_stat, p_value = scipy.stats.ttest_ind(before_latencies, after_latencies)

before_mean = sum(before_latencies) / len(before_latencies)
after_mean = sum(after_latencies) / len(after_latencies)
improvement = ((before_mean - after_mean) / before_mean) * 100

print(f"Before: {before_mean*1000:.2f}ms ± {scipy.stats.sem(before_latencies)*1000:.2f}ms")
print(f"After: {after_mean*1000:.2f}ms ± {scipy.stats.sem(after_latencies)*1000:.2f}ms")
print(f"Improvement: {improvement:.1f}%")
print(f"p-value: {p_value:.6f}")

if p_value < 0.05:
    print("Result is statistically significant (p < 0.05)")
else:
    print("Result is NOT statistically significant")
```
