# RPyCBench Python API Quickstart

## Table of Contents

- [Problem: Your RPyC Application is Slow](#problem-your-rpyc-application-is-slow)
- [Installation](#installation)
- [5-Minute Diagnosis](#5-minute-diagnosis)
  - [Step 1: Profile Your Existing RPyC Application](#step-1-profile-your-existing-rpyc-application)
  - [Step 2: Measure Baseline vs Application Performance](#step-2-measure-baseline-vs-application-performance)
  - [Step 3: Integrate Profiling Into Your Application](#step-3-integrate-profiling-into-your-application)
- [Common Scenarios](#common-scenarios)
  - [Scenario: "Many parallel clients on the same port perform poorly"](#scenario-many-parallel-clients-on-the-same-port-perform-poorly)
  - [Scenario: "I have a slow RPyC call and need to diagnose it"](#scenario-i-have-a-slow-rpyc-call-and-need-to-diagnose-it)
  - [Scenario: "My RPyC calls are slower than HTTP"](#scenario-my-rpyc-calls-are-slower-than-http)
  - [Scenario: "Concurrency is terrible"](#scenario-concurrency-is-terrible)
  - [Scenario: "Large file transfers are slow"](#scenario-large-file-transfers-are-slow)
- [Next Steps](#next-steps)

## Problem: Your RPyC Application is Slow

You have an RPyC application that's performing poorly. Is it the network? RPyC overhead? Your application logic? This guide shows you how to find out.

## Installation

```bash
pip install rpycbench
```

## 5-Minute Diagnosis

### Step 1: Profile Your Existing RPyC Application

```python
import rpyc
from rpycbench.utils.profiler import profile_rpyc_calls

# Your existing RPyC connection
conn = rpyc.connect('localhost', 18812)

# Wrap it with profiling (zero code changes needed)
with profile_rpyc_calls(conn, print_summary=True) as profiled:
    # Run your slow operation
    result = profiled.root.your_slow_method()

# Telemetry summary printed automatically with:
# - Total network round trips
# - Slow calls (> 100ms by default)
# - NetRef overhead
# - Call stack depth issues
```

**What you'll see:**
```
RPyC Telemetry Summary
======================
Total calls: 347
Network round trips: 347
NetRefs created: 89
Slow calls: 12

Top Slow Calls:
  1. load_user_data: 2.34s (23 round trips)
  2. process_records: 1.87s (156 round trips)
  3. calculate_stats: 0.45s (8 round trips)
```

**Immediate insights:**
- High round trip count = chatty network calls (batch them)
- Many NetRefs = unnecessary object proxying (pass data, not objects)
- Deep call stacks = nested remote calls (flatten them)

### Step 2: Measure Baseline vs Application Performance

```python
from rpycbench.core.benchmark import LatencyBenchmark
import rpyc

def simple_echo(conn):
    return conn.root.echo("test")

def your_application_method(conn):
    return conn.root.your_slow_method()

# Baseline: pure RPyC latency
baseline = LatencyBenchmark(
    name="baseline",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=simple_echo,
    num_requests=1000
)

# Application: your actual method
application = LatencyBenchmark(
    name="application",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=your_application_method,
    num_requests=1000
)

baseline_metrics = baseline.run()
app_metrics = application.run()

baseline_stats = baseline_metrics.compute_statistics()
app_stats = app_metrics.compute_statistics()

print(f"Baseline latency: {baseline_stats['latency']['mean']*1000:.2f}ms")
print(f"Application latency: {app_stats['latency']['mean']*1000:.2f}ms")
print(f"Overhead: {(app_stats['latency']['mean'] - baseline_stats['latency']['mean'])*1000:.2f}ms")
```

**Interpretation:**
- Small overhead (< 10ms) = Your application logic is slow
- Large overhead (> 100ms) = Network/serialization is the problem
- Moderate overhead = Combination of both

### Step 3: Integrate Profiling Into Your Application

```python
from rpycbench.core.benchmark import BenchmarkContext

# Drop-in profiling for production code
ctx = BenchmarkContext(
    name="user_processing",
    protocol="rpyc",
    measure_latency=True,
    measure_system=True
)

# Measure specific operations
with ctx.measure_request(bytes_sent=1024, bytes_received=2048):
    result = conn.root.process_user(user_id)
    ctx.record_request(success=True)

# Get detailed metrics
metrics = ctx.get_results()
stats = metrics.compute_statistics()

if stats['latency']['mean'] > 0.5:
    print(f"WARNING: Slow operation detected: {stats['latency']['mean']}s")
```

## Common Scenarios

### Scenario: "Many parallel clients on the same port perform poorly"

**Problem**: Multiple clients connecting to the same RPyC server are experiencing high latency or failures.

**Diagnosis Workflow**:

```python
from rpycbench.core.benchmark import ConcurrentBenchmark
import rpyc

# Test with increasing client counts to find breaking point
for num_clients in [10, 50, 100, 200, 500]:
    bench = ConcurrentBenchmark(
        name=f"{num_clients}_clients",
        protocol="rpyc",
        server_mode="threaded",
        connection_factory=lambda: rpyc.connect('localhost', 18812),
        request_func=lambda c: c.root.some_method(),
        num_clients=num_clients,
        requests_per_client=50
    )

    metrics = bench.run()
    metrics.record_system_metrics()  # Capture CPU/memory
    stats = metrics.compute_statistics()

    success_rate = (1 - metrics.failed_requests/metrics.total_requests) * 100
    p99_ms = stats['latency']['p99'] * 1000
    cpu_pct = stats['cpu_usage']['mean']

    print(f"\n{num_clients} concurrent clients:")
    print(f"  Success rate: {success_rate:.1f}%")
    print(f"  P99 latency: {p99_ms:.2f}ms")
    print(f"  CPU usage: {cpu_pct:.1f}%")

    # Stop when performance degrades
    if success_rate < 95 or p99_ms > 500:
        print(f"  LIMIT REACHED at {num_clients} clients")
        break
```

**Interpret the results**:

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Success rate < 95% | **Server exhaustion** - dropping connections | Increase ulimits (`ulimit -n 65536`) or reduce clients |
| High CPU (> 80%) + high P99 | **GIL contention** (threaded mode) | Switch to `server_mode="forking"` for CPU-bound work |
| Low CPU (< 30%) + high P99 | **I/O bottleneck** - waiting on database/network | Optimize I/O operations, use connection pooling |
| P99 >> P50 (> 5x) | **Resource contention** - inconsistent performance | Try forking mode or scale horizontally |

**Quick Fix Examples**:

```python
# If diagnosis shows GIL contention (high CPU, poor scaling):
# Switch to forking mode
from rpycbench.servers.rpyc_servers import RPyCServer

with RPyCServer(port=18812, mode='forking'):  # Changed from 'threaded'
    # Re-run benchmark
    bench = ConcurrentBenchmark(..., server_mode="forking", ...)
    # Expect: Better scaling, lower P99 for CPU-bound work

# If diagnosis shows server exhaustion (< 95% success):
# Check and increase system limits
import subprocess
subprocess.run(['ulimit', '-n', '65536'])  # Increase file descriptor limit

# If diagnosis shows I/O bottleneck (low CPU, high latency):
# Optimize server-side I/O (example: database connection pooling)
# Or reduce concurrent load until I/O is optimized
```

### Scenario: "I have a slow RPyC call and need to diagnose it"

```python
import rpyc
from rpycbench.utils.profiler import profile_rpyc_calls, RPyCTelemetry
from rpycbench.utils.visualizer import format_call_tree, format_slow_calls_report

# Create telemetry with custom thresholds
telemetry = RPyCTelemetry(
    slow_call_threshold=0.05,  # Flag calls > 50ms
    track_netrefs=True,
    track_stacks=True
)

conn = rpyc.connect('localhost', 18812)

with profile_rpyc_calls(conn, telemetry_inst=telemetry) as profiled:
    # Run the slow operation
    result = profiled.root.your_slow_method(arg1, arg2)

# Detailed diagnosis
print(format_slow_calls_report(telemetry, top_n=10))
print(format_call_tree(telemetry, show_netrefs=True))

stats = telemetry.get_statistics()
print(f"\nTotal round trips: {stats['total_calls']}")
print(f"NetRefs created: {stats['netrefs_created']}")
print(f"Max call depth: {stats['max_stack_depth']}")
```

**What to look for:**
- **Slow call report**: Identifies which specific remote calls are taking the most time
- **Call tree**: Shows nested calls and their relationships
- **Round trip count**: High count indicates chatty communication pattern
- **NetRef count**: High count indicates excessive object proxying
- **Max call depth**: Deep nesting creates latency multiplication

**Common fixes:**
- Batch multiple calls into a single remote method
- Return primitive data (dicts, lists) instead of objects
- Flatten nested remote calls by doing work server-side
- Use `rpyc.utils.classic.obtain()` to copy objects locally

### Scenario: "My RPyC calls are slower than HTTP"

```python
from rpycbench.benchmarks.suite import BenchmarkSuite

suite = BenchmarkSuite(
    rpyc_host='localhost',
    rpyc_port=18812,
    http_host='localhost',
    http_port=5000
)

# Compare RPyC vs HTTP for your workload
results = suite.run_all(
    test_rpyc_threaded=True,
    test_http=True,
    num_requests=1000
)

results.print_summary()
```

If HTTP is faster:
- **Cause**: Likely excessive NetRefs or deep call nesting
- **Fix**: Pass data instead of objects, flatten call structure

### Scenario: "Concurrency is terrible"

```python
from rpycbench.core.benchmark import ConcurrentBenchmark
import rpyc

bench = ConcurrentBenchmark(
    name="concurrent_users",
    protocol="rpyc",
    server_mode="threaded",  # Try "forking" if slow
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=lambda c: c.root.your_method(),
    num_clients=128,
    requests_per_client=100,
    track_per_connection=True  # See individual connection stats
)

metrics = bench.run()
stats = metrics.compute_statistics()

print(f"Success rate: {(1 - metrics.failed_requests/metrics.total_requests)*100:.1f}%")
print(f"Mean latency: {stats['latency']['mean']*1000:.2f}ms")
print(f"P99 latency: {stats['latency']['p99']*1000:.2f}ms")
```

High P99 or failures:
- **Cause**: Server mode bottleneck or resource exhaustion
- **Fix**: Switch to forking mode or tune server resources

### Scenario: "Large file transfers are slow"

```python
from rpycbench.core.benchmark import BinaryTransferBenchmark
import rpyc

bench = BinaryTransferBenchmark(
    name="file_transfer",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    upload_func=lambda c, data: c.root.upload_file(data),
    download_func=lambda c, size: c.root.download_file(size),
    file_sizes=[1024*1024*10, 1024*1024*100],  # 10MB, 100MB
    chunk_size=64*1024,  # Try different chunk sizes
    iterations=3
)

metrics = bench.run()
stats = metrics.compute_statistics()

print(f"Upload: {stats['upload_bandwidth']['mean']/1024/1024:.2f} MB/s")
print(f"Download: {stats['download_bandwidth']['mean']/1024/1024:.2f} MB/s")
```

Low throughput:
- **Cause**: Inefficient chunking or serialization overhead
- **Fix**: Increase chunk size, use binary-safe transfer methods

## Next Steps

- **Cookbook**: See [docs/cookbook-python-api.md](cookbook-python-api.md) for detailed optimization patterns
- **API Reference**: See [docs/api-reference.md](api-reference.md) for complete API documentation
- **Examples**: See `examples/` directory for complete working examples
