# RPyCBench Python API Reference

## Table of Contents

- [Core Benchmark Classes](#core-benchmark-classes)
  - [BenchmarkContext](#benchmarkcontext)
  - [ConnectionBenchmark](#connectionbenchmark)
  - [LatencyBenchmark](#latencybenchmark)
  - [BandwidthBenchmark](#bandwidthbenchmark)
  - [BinaryTransferBenchmark](#binarytransferbenchmark)
  - [ConcurrentBenchmark](#concurrentbenchmark)
- [Metrics Classes](#metrics-classes)
  - [BenchmarkMetrics](#benchmarkmetrics)
  - [BenchmarkResults](#benchmarkresults)
- [Profiling and Telemetry](#profiling-and-telemetry)
  - [RPyCTelemetry](#rpyctelemetry)
  - [ProfiledConnection](#profiledconnection)
  - [create_profiled_connection](#create_profiled_connection)
  - [profile_rpyc_calls](#profile_rpyc_calls)
  - [Global Telemetry Functions](#global-telemetry-functions)
- [Visualization](#visualization)
  - [format_call_tree](#format_call_tree)
  - [format_timeline](#format_timeline)
  - [format_netref_report](#format_netref_report)
  - [format_slow_calls_report](#format_slow_calls_report)
  - [format_full_report](#format_full_report)
- [Server Management](#server-management)
  - [RPyCServer](#rpycserver)
  - [RemoteRPyCServer](#remoterpycserver)
  - [create_rpyc_connection](#create_rpyc_connection)
- [Benchmark Suite](#benchmark-suite)
  - [BenchmarkSuite](#benchmarksuite)

---

## Core Benchmark Classes

### BenchmarkContext

Context manager for integrating benchmarking into existing applications. Useful for production monitoring and targeted performance measurement.

**Location**: `rpycbench.core.benchmark`

**Constructor**:

```python
BenchmarkContext(
    name: str,
    protocol: str,
    server_mode: Optional[str] = None,
    measure_connection: bool = False,
    measure_latency: bool = True,
    measure_bandwidth: bool = False,
    measure_system: bool = True,
)
```

**Parameters**:

- `name` (str): Identifier for this benchmark context
- `protocol` (str): Protocol being measured, e.g., 'rpyc' or 'http'
- `server_mode` (Optional[str]): Server mode if applicable ('threaded', 'forking', 'oneshot')
- `measure_connection` (bool): Whether to measure connection establishment time
- `measure_latency` (bool): Whether to measure request latency
- `measure_bandwidth` (bool): Whether to measure bandwidth
- `measure_system` (bool): Whether to measure system resources (CPU, memory)

**Methods**:

#### `measure_connection_time()`

Context manager for measuring connection establishment time.

```python
with ctx.measure_connection_time():
    conn = rpyc.connect('localhost', 18812)
```

**Returns**: Context manager

#### `measure_request(bytes_sent: int = 0, bytes_received: int = 0)`

Context manager for measuring request execution.

```python
with ctx.measure_request(bytes_sent=1024, bytes_received=2048):
    result = conn.root.some_method()
```

**Parameters**:
- `bytes_sent` (int): Number of bytes sent in this request
- `bytes_received` (int): Number of bytes received in this request

**Returns**: Context manager

#### `record_request(success: bool)`

Record a request completion status.

```python
ctx.record_request(success=True)
```

**Parameters**:
- `success` (bool): Whether the request succeeded

#### `get_results()`

Get the collected benchmark metrics.

```python
metrics = ctx.get_results()
```

**Returns**: [BenchmarkMetrics](#benchmarkmetrics)

**Example**:

```python
from rpycbench.core.benchmark import BenchmarkContext

ctx = BenchmarkContext(
    name="user_fetch",
    protocol="rpyc",
    measure_latency=True
)

with ctx.measure_request(bytes_sent=512, bytes_received=4096):
    user = conn.root.get_user(123)
    ctx.record_request(success=True)

metrics = ctx.get_results()
stats = metrics.compute_statistics()
print(f"Mean latency: {stats['latency']['mean']*1000:.2f}ms")
```

---

### ConnectionBenchmark

Measures connection establishment performance by creating multiple connections and timing each one.

**Location**: `rpycbench.core.benchmark`

**Constructor**:

```python
ConnectionBenchmark(
    name: str,
    protocol: str,
    server_mode: Optional[str],
    connection_factory: Callable[[], Any],
    num_connections: int = 100,
)
```

**Parameters**:

- `name` (str): Benchmark name
- `protocol` (str): Protocol being tested ('rpyc', 'http', etc.)
- `server_mode` (Optional[str]): Server mode ('threaded', 'forking', 'oneshot')
- `connection_factory` (Callable): Function that creates and returns a new connection
- `num_connections` (int): Number of connections to establish for sampling

**Methods**:

#### `run()`

Execute the benchmark.

```python
metrics = bench.run()
```

**Returns**: [BenchmarkMetrics](#benchmarkmetrics)

**Example**:

```python
from rpycbench.core.benchmark import ConnectionBenchmark
import rpyc

bench = ConnectionBenchmark(
    name="rpyc_connection",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    num_connections=100
)

metrics = bench.run()
stats = metrics.compute_statistics()
print(f"Mean connection time: {stats['connection_time']['mean']*1000:.2f}ms")
print(f"P99 connection time: {stats['connection_time']['p99']*1000:.2f}ms")
```

---

### LatencyBenchmark

Measures request/response latency by executing a request function repeatedly.

**Location**: `rpycbench.core.benchmark`

**Constructor**:

```python
LatencyBenchmark(
    name: str,
    protocol: str,
    server_mode: Optional[str],
    connection_factory: Callable[[], Any],
    request_func: Callable[[Any], Any],
    num_requests: int = 1000,
    warmup_requests: int = 10,
)
```

**Parameters**:

- `name` (str): Benchmark name
- `protocol` (str): Protocol being tested
- `server_mode` (Optional[str]): Server mode
- `connection_factory` (Callable): Function that creates a connection
- `request_func` (Callable): Function that takes a connection and performs a request
- `num_requests` (int): Number of requests to execute
- `warmup_requests` (int): Number of warmup requests to exclude from statistics

**Methods**:

#### `run()`

Execute the benchmark.

**Returns**: [BenchmarkMetrics](#benchmarkmetrics)

**Example**:

```python
from rpycbench.core.benchmark import LatencyBenchmark
import rpyc

def echo_request(conn):
    return conn.root.echo("test")

bench = LatencyBenchmark(
    name="echo_latency",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=echo_request,
    num_requests=1000,
    warmup_requests=10
)

metrics = bench.run()
stats = metrics.compute_statistics()
print(f"Mean latency: {stats['latency']['mean']*1000:.2f}ms")
print(f"P50 latency: {stats['latency']['median']*1000:.2f}ms")
print(f"P95 latency: {stats['latency']['p95']*1000:.2f}ms")
print(f"P99 latency: {stats['latency']['p99']*1000:.2f}ms")
```

---

### BandwidthBenchmark

Measures upload and download bandwidth for various data payload sizes.

**Location**: `rpycbench.core.benchmark`

**Constructor**:

```python
BandwidthBenchmark(
    name: str,
    protocol: str,
    server_mode: Optional[str],
    connection_factory: Callable[[], Any],
    upload_func: Callable[[Any, bytes], Any],
    download_func: Callable[[Any, int], bytes],
    data_sizes: Optional[List[int]] = None,
    iterations: int = 10,
)
```

**Parameters**:

- `name` (str): Benchmark name
- `protocol` (str): Protocol being tested
- `server_mode` (Optional[str]): Server mode
- `connection_factory` (Callable): Function that creates a connection
- `upload_func` (Callable): Function that takes connection and data bytes, uploads them
- `download_func` (Callable): Function that takes connection and size, downloads that many bytes
- `data_sizes` (Optional[List[int]]): List of payload sizes to test. Default: [1KB, 10KB, 100KB, 1MB]
- `iterations` (int): Number of iterations per data size

**Methods**:

#### `run()`

Execute the benchmark.

**Returns**: [BenchmarkMetrics](#benchmarkmetrics)

**Example**:

```python
from rpycbench.core.benchmark import BandwidthBenchmark
import rpyc

bench = BandwidthBenchmark(
    name="data_transfer",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    upload_func=lambda c, data: c.root.receive_data(data),
    download_func=lambda c, size: c.root.send_data(size),
    data_sizes=[1024, 10*1024, 100*1024, 1024*1024],
    iterations=20
)

metrics = bench.run()
stats = metrics.compute_statistics()
print(f"Upload bandwidth: {stats['upload_bandwidth']['mean']/1024/1024:.2f} MB/s")
print(f"Download bandwidth: {stats['download_bandwidth']['mean']/1024/1024:.2f} MB/s")
```

---

### BinaryTransferBenchmark

Measures large file transfer performance with various chunk sizes and transfer methods.

**Location**: `rpycbench.core.benchmark`

**Constructor**:

```python
BinaryTransferBenchmark(
    name: str,
    protocol: str,
    server_mode: Optional[str],
    connection_factory: Callable[[], Any],
    upload_func: Callable[[Any, bytes], Any],
    download_func: Callable[[Any, int], bytes],
    upload_chunked_func: Optional[Callable[[Any, List[bytes]], Any]] = None,
    download_chunked_func: Optional[Callable[[Any, int, int], List[bytes]]] = None,
    file_sizes: Optional[List[int]] = None,
    chunk_size: Optional[int] = None,
    iterations: int = 3,
    test_upload: bool = True,
    test_download: bool = True,
    test_chunked: bool = True,
)
```

**Parameters**:

- `name` (str): Benchmark name
- `protocol` (str): Protocol being tested
- `server_mode` (Optional[str]): Server mode
- `connection_factory` (Callable): Function that creates a connection
- `upload_func` (Callable): Function for uploading entire file at once
- `download_func` (Callable): Function for downloading entire file at once
- `upload_chunked_func` (Optional[Callable]): Function for uploading file in chunks
- `download_chunked_func` (Optional[Callable]): Function for downloading file in chunks
- `file_sizes` (Optional[List[int]]): File sizes to test. Default: [1.5MB, 128MB, 500MB]
- `chunk_size` (Optional[int]): Chunk size for chunked transfers. Default: 64KB
- `iterations` (int): Number of iterations per file size
- `test_upload` (bool): Whether to test uploads
- `test_download` (bool): Whether to test downloads
- `test_chunked` (bool): Whether to test chunked transfers

**Methods**:

#### `run()`

Execute the benchmark.

**Returns**: [BenchmarkMetrics](#benchmarkmetrics)

**Example**:

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
    upload_chunked_func=lambda c, chunks: c.root.upload_chunked(chunks),
    download_chunked_func=lambda c, size, cs: c.root.download_chunked(size, cs),
    file_sizes=[10*1024*1024, 100*1024*1024],  # 10MB, 100MB
    chunk_size=64*1024,
    iterations=3
)

metrics = bench.run()
stats = metrics.compute_statistics()
print(f"Upload: {stats['upload_bandwidth']['mean']/1024/1024:.2f} MB/s")
print(f"Download: {stats['download_bandwidth']['mean']/1024/1024:.2f} MB/s")
```

---

### ConcurrentBenchmark

Measures performance under concurrent load by simulating multiple clients.

**Location**: `rpycbench.core.benchmark`

**Constructor**:

```python
ConcurrentBenchmark(
    name: str,
    protocol: str,
    server_mode: Optional[str],
    connection_factory: Callable[[], Any],
    request_func: Callable[[Any], Any],
    num_clients: int = 128,
    requests_per_client: int = 100,
    max_workers: Optional[int] = None,
    track_per_connection: bool = False,
)
```

**Parameters**:

- `name` (str): Benchmark name
- `protocol` (str): Protocol being tested
- `server_mode` (Optional[str]): Server mode
- `connection_factory` (Callable): Function that creates a connection
- `request_func` (Callable): Function that performs a request
- `num_clients` (int): Number of concurrent clients to simulate
- `requests_per_client` (int): Number of requests each client should make
- `max_workers` (Optional[int]): Maximum thread pool size. Default: num_clients
- `track_per_connection` (bool): Whether to track metrics per connection (higher memory usage)

**Methods**:

#### `run()`

Execute the benchmark.

**Returns**: [BenchmarkMetrics](#benchmarkmetrics)

**Example**:

```python
from rpycbench.core.benchmark import ConcurrentBenchmark
import rpyc

bench = ConcurrentBenchmark(
    name="concurrent_load",
    protocol="rpyc",
    server_mode="threaded",
    connection_factory=lambda: rpyc.connect('localhost', 18812),
    request_func=lambda c: c.root.process_request(),
    num_clients=128,
    requests_per_client=100,
    track_per_connection=False
)

metrics = bench.run()
stats = metrics.compute_statistics()

success_rate = (1 - metrics.failed_requests / metrics.total_requests) * 100
print(f"Success rate: {success_rate:.1f}%")
print(f"Mean latency: {stats['latency']['mean']*1000:.2f}ms")
print(f"P99 latency: {stats['latency']['p99']*1000:.2f}ms")
print(f"Failed requests: {metrics.failed_requests}/{metrics.total_requests}")
```

---

## Metrics Classes

### BenchmarkMetrics

Container for benchmark measurements and statistics.

**Location**: `rpycbench.core.metrics`

**Constructor**:

```python
@dataclass
class BenchmarkMetrics:
    name: str
    protocol: str
    server_mode: Optional[str]
    connection_times: List[float]
    latencies: List[float]
    upload_bandwidth: List[float]
    download_bandwidth: List[float]
    concurrent_connections: int
    total_requests: int
    failed_requests: int
    cpu_usage: List[float]
    memory_usage: List[float]
    metadata: Dict[str, Any]
```

**Attributes**:

- `name` (str): Benchmark name
- `protocol` (str): Protocol tested
- `server_mode` (Optional[str]): Server mode
- `connection_times` (List[float]): Connection establishment times in seconds
- `latencies` (List[float]): Request latencies in seconds
- `upload_bandwidth` (List[float]): Upload bandwidth measurements in bytes/second
- `download_bandwidth` (List[float]): Download bandwidth measurements in bytes/second
- `concurrent_connections` (int): Number of concurrent connections
- `total_requests` (int): Total number of requests attempted
- `failed_requests` (int): Number of failed requests
- `cpu_usage` (List[float]): CPU usage percentages
- `memory_usage` (List[float]): Memory usage in bytes
- `metadata` (Dict[str, Any]): Additional metadata

**Methods**:

#### `add_connection_time(duration: float)`

Record a connection establishment time.

**Parameters**:
- `duration` (float): Time in seconds

#### `add_latency(duration: float)`

Record a request latency.

**Parameters**:
- `duration` (float): Time in seconds

#### `add_upload_bandwidth(bytes_sent: int, duration: float)`

Record an upload operation.

**Parameters**:
- `bytes_sent` (int): Number of bytes sent
- `duration` (float): Time taken in seconds

#### `add_download_bandwidth(bytes_received: int, duration: float)`

Record a download operation.

**Parameters**:
- `bytes_received` (int): Number of bytes received
- `duration` (float): Time taken in seconds

#### `record_system_metrics()`

Capture current CPU and memory usage.

#### `compute_statistics()`

Compute comprehensive statistics from collected metrics.

**Returns**: Dict with keys:
- `'connection_time'`: Dict with 'mean', 'median', 'min', 'max', 'stdev', 'p95', 'p99'
- `'latency'`: Dict with 'mean', 'median', 'min', 'max', 'stdev', 'p95', 'p99'
- `'upload_bandwidth'`: Dict with 'mean', 'median', 'min', 'max', 'stdev', 'p95', 'p99'
- `'download_bandwidth'`: Dict with 'mean', 'median', 'min', 'max', 'stdev', 'p95', 'p99'
- `'cpu_usage'`: Dict with 'mean', 'median', 'min', 'max'
- `'memory_usage'`: Dict with 'mean', 'median', 'min', 'max'

**Example**:

```python
metrics = bench.run()
stats = metrics.compute_statistics()

print(f"Latency mean: {stats['latency']['mean']*1000:.2f}ms")
print(f"Latency median: {stats['latency']['median']*1000:.2f}ms")
print(f"Latency P95: {stats['latency']['p95']*1000:.2f}ms")
print(f"Latency P99: {stats['latency']['p99']*1000:.2f}ms")
print(f"Latency stdev: {stats['latency']['stdev']*1000:.2f}ms")
```

**Interpreting Metrics**:

Understanding what metric values mean helps diagnose performance issues:

| Metric | Normal Range | Warning Signs | Diagnosis |
|--------|--------------|---------------|-----------|
| **CPU Usage** | | | |
| `cpu_usage['mean']` | 30-70% | > 80% | High CPU - check if GIL-bound (threaded mode) |
| | | < 10% | Server idle or I/O-bound |
| **Latency** | | | |
| `latency['p99'] / latency['median']` | < 3x | > 5x | Inconsistent performance - resource contention |
| | | > 10x | Severe contention - GIL or I/O limits |
| `latency['stdev']` | Low relative to mean | High stdev | High variance indicates instability |
| **Success Rate** | | | |
| `(1 - failed/total) * 100` | > 99% | 95-99% | Approaching limits |
| | | < 95% | Server exhaustion - increase ulimits |
| **Memory Usage** | | | |
| `memory_usage['mean']` | Stable | Growing | Memory leak or unbounded caching |

**Common Patterns**:

```python
stats = metrics.compute_statistics()
success_rate = (1 - metrics.failed_requests / metrics.total_requests) * 100

# Pattern 1: GIL Contention (CPU-bound threaded mode)
if stats['cpu_usage']['mean'] > 80 and stats['latency']['p99'] / stats['latency']['median'] > 5:
    print("DIAGNOSIS: GIL contention in threaded mode")
    print("ACTION: Switch to server_mode='forking' for CPU-bound workload")

# Pattern 2: I/O Bottleneck
if stats['cpu_usage']['mean'] < 30 and stats['latency']['p99'] > 0.1:
    print("DIAGNOSIS: I/O bottleneck - low CPU but high latency")
    print("ACTION: Optimize database queries, add connection pooling")

# Pattern 3: Server Exhaustion
if success_rate < 95:
    print("DIAGNOSIS: Server dropping connections - exhausted")
    print("ACTION: Increase ulimits (ulimit -n 65536), reduce load")

# Pattern 4: Consistent Performance
if stats['latency']['p99'] / stats['latency']['median'] < 3:
    print("DIAGNOSIS: Consistent performance - well-behaved system")
    if stats['latency']['mean'] > target_latency:
        print("ACTION: Latency is consistent but too high - optimize application logic")
```

**Red Flags**:

- **High CPU (>80%) + High P99/P50 ratio (>5)**: GIL contention - switch to forking mode
- **Low CPU (<30%) + High P99 (>100ms)**: I/O bottleneck - optimize I/O operations
- **Success rate < 95%**: Server exhaustion - increase limits or reduce concurrency
- **High memory growth**: Potential memory leak - investigate caching and object lifecycle
- **P99 > 10x P50**: Severe resource contention - system under stress

#### `to_dict()`

Convert metrics to dictionary representation.

**Returns**: Dict

#### `to_json()`

Convert metrics to JSON string.

**Returns**: str

---

### BenchmarkResults

Collection of multiple benchmark results for comparison.

**Location**: `rpycbench.core.metrics`

**Constructor**:

```python
@dataclass
class BenchmarkResults:
    results: List[BenchmarkMetrics] = field(default_factory=list)
```

**Methods**:

#### `add_result(metrics: BenchmarkMetrics)`

Add a benchmark result to the collection.

**Parameters**:
- `metrics` (BenchmarkMetrics): Metrics to add

#### `get_comparison_table()`

Get a comparison table of all results.

**Returns**: Dict mapping benchmark names to their statistics

**Example**:

```python
results = BenchmarkResults()
results.add_result(rpyc_metrics)
results.add_result(http_metrics)

comparison = results.get_comparison_table()
print(f"RPyC latency: {comparison['rpyc']['latency_mean']*1000:.2f}ms")
print(f"HTTP latency: {comparison['http']['latency_mean']*1000:.2f}ms")
```

#### `to_json()`

Export all results as JSON string.

**Returns**: str

#### `to_dict()`

Export all results as dictionary.

**Returns**: Dict

#### `print_summary()`

Print a human-readable summary of all results.

**Example**:

```python
results = BenchmarkResults()
results.add_result(rpyc_threaded_metrics)
results.add_result(rpyc_forking_metrics)
results.add_result(http_metrics)

results.print_summary()
```

---

## Profiling and Telemetry

### RPyCTelemetry

Tracks RPyC operations for profiling and performance analysis.

**Location**: `rpycbench.utils.telemetry`

**Constructor**:

```python
RPyCTelemetry(
    enabled: bool = True,
    track_netrefs: bool = True,
    track_stacks: bool = True,
    slow_call_threshold: float = 0.1,
    deep_stack_threshold: int = 5,
)
```

**Parameters**:

- `enabled` (bool): Whether telemetry is enabled
- `track_netrefs` (bool): Whether to track NetRef creation and lifecycle
- `track_stacks` (bool): Whether to track call stacks
- `slow_call_threshold` (float): Threshold in seconds for flagging slow calls
- `deep_stack_threshold` (int): Threshold for flagging deep call stacks

**Methods**:

#### `start_call(method_name: str, call_type: str, is_netref: bool, netref_id: Optional[int])`

Start tracking a remote call.

**Parameters**:
- `method_name` (str): Name of the method being called
- `call_type` (str): Type of call ('method', 'getattr', 'setattr', etc.)
- `is_netref` (bool): Whether the target is a NetRef
- `netref_id` (Optional[int]): NetRef ID if applicable

**Returns**: int (call_id)

#### `end_call(call_id: int, result_is_netref: bool = False, result_netref_id: Optional[int] = None, exception: Optional[Exception] = None)`

End tracking a remote call.

**Parameters**:
- `call_id` (int): Call ID returned from start_call
- `result_is_netref` (bool): Whether result is a NetRef
- `result_netref_id` (Optional[int]): NetRef ID of result if applicable
- `exception` (Optional[Exception]): Exception if call failed

#### `register_netref(netref_obj: Any, created_by_call_id: Optional[int] = None)`

Register a NetRef object for tracking.

**Parameters**:
- `netref_obj` (Any): The NetRef object
- `created_by_call_id` (Optional[int]): Call ID that created this NetRef

**Returns**: int (netref_id)

#### `get_current_stack_depth()`

Get current call stack depth.

**Returns**: int

#### `get_call_stack()`

Get current call stack.

**Returns**: List[RPyCCallInfo]

#### `print_call_stack(title: str = "RPyC Call Stack")`

Print current call stack to stdout.

**Parameters**:
- `title` (str): Title for the stack trace

#### `get_statistics()`

Get telemetry statistics.

**Returns**: Dict with keys:
- `'total_calls'`: int
- `'slow_calls'`: int
- `'netrefs_created'`: int
- `'netrefs_accessed'`: int
- `'max_stack_depth'`: int
- `'total_duration'`: float

#### `print_summary()`

Print comprehensive telemetry summary to stdout.

#### `reset()`

Clear all telemetry data.

**Example**:

```python
from rpycbench.utils.telemetry import RPyCTelemetry

telemetry = RPyCTelemetry(
    slow_call_threshold=0.05,  # 50ms
    deep_stack_threshold=3,
    track_netrefs=True,
    track_stacks=True
)

# Use with ProfiledConnection...
# ... after operations ...

telemetry.print_summary()
stats = telemetry.get_statistics()
print(f"Total calls: {stats['total_calls']}")
print(f"Slow calls: {stats['slow_calls']}")
print(f"NetRefs created: {stats['netrefs_created']}")
```

---

### ProfiledConnection

Wrapper around RPyC connection that tracks all operations.

**Location**: `rpycbench.utils.profiler`

**Constructor**:

```python
ProfiledConnection(
    connection: rpyc.Connection,
    telemetry_inst: Optional[RPyCTelemetry] = None,
    auto_print_on_slow: bool = True,
    auto_print_on_deep: bool = True,
)
```

**Parameters**:

- `connection` (rpyc.Connection): The RPyC connection to wrap
- `telemetry_inst` (Optional[RPyCTelemetry]): Telemetry instance to use. Creates new one if None
- `auto_print_on_slow` (bool): Automatically print call stack when slow calls detected
- `auto_print_on_deep` (bool): Automatically print call stack when deep nesting detected

**Properties**:

#### `root`

Access the root service object (returns ProfiledNetRef).

```python
profiled_conn.root.some_method()  # Tracked
```

#### `telemetry`

Access the underlying telemetry instance.

```python
stats = profiled_conn.telemetry.get_statistics()
```

**Methods**:

#### `close()`

Close the underlying connection.

**Example**:

```python
from rpycbench.utils.profiler import ProfiledConnection
from rpycbench.utils.telemetry import RPyCTelemetry
import rpyc

telemetry = RPyCTelemetry(slow_call_threshold=0.1)
conn = rpyc.connect('localhost', 18812)
profiled = ProfiledConnection(conn, telemetry_inst=telemetry)

result = profiled.root.some_method()

telemetry.print_summary()
profiled.close()
```

---

### create_profiled_connection

Factory function for creating a profiled RPyC connection.

**Location**: `rpycbench.utils.profiler`

**Signature**:

```python
create_profiled_connection(
    host: str = 'localhost',
    port: int = 18812,
    telemetry_inst: Optional[RPyCTelemetry] = None,
    auto_print_on_slow: bool = False,
    auto_print_on_deep: bool = False,
    **rpyc_config
) -> ProfiledConnection
```

**Parameters**:

- `host` (str): Server hostname
- `port` (int): Server port
- `telemetry_inst` (Optional[RPyCTelemetry]): Telemetry instance to use
- `auto_print_on_slow` (bool): Auto-print on slow calls
- `auto_print_on_deep` (bool): Auto-print on deep stacks
- `**rpyc_config`: Additional RPyC configuration options

**Returns**: ProfiledConnection

**Example**:

```python
from rpycbench.utils.profiler import create_profiled_connection

conn = create_profiled_connection(
    host='localhost',
    port=18812,
    auto_print_on_slow=True
)

result = conn.root.some_method()
conn.telemetry.print_summary()
conn.close()
```

---

### profile_rpyc_calls

Context manager for profiling RPyC operations.

**Location**: `rpycbench.utils.profiler`

**Signature**:

```python
profile_rpyc_calls(
    connection: rpyc.Connection,
    print_summary: bool = False,
    **telemetry_kwargs
) -> ProfiledConnection
```

**Parameters**:

- `connection` (rpyc.Connection): Existing RPyC connection to profile
- `print_summary` (bool): Whether to automatically print summary on exit
- `**telemetry_kwargs`: Arguments to pass to RPyCTelemetry constructor

**Returns**: ProfiledConnection (as context manager)

**Example**:

```python
from rpycbench.utils.profiler import profile_rpyc_calls
import rpyc

conn = rpyc.connect('localhost', 18812)

with profile_rpyc_calls(conn, print_summary=True, slow_call_threshold=0.05) as profiled:
    result = profiled.root.some_method()
    # Summary printed automatically on exit
```

---

### Global Telemetry Functions

**Location**: `rpycbench.utils.telemetry`

#### `get_telemetry()`

Get the global telemetry instance.

```python
from rpycbench.utils.telemetry import get_telemetry

telemetry = get_telemetry()
stats = telemetry.get_statistics()
```

**Returns**: RPyCTelemetry

#### `enable_telemetry(**kwargs)`

Enable global telemetry with specified settings.

```python
from rpycbench.utils.telemetry import enable_telemetry

enable_telemetry(
    slow_call_threshold=0.1,
    track_netrefs=True,
    track_stacks=True
)
```

**Parameters**: Same as RPyCTelemetry constructor

**Returns**: RPyCTelemetry

#### `disable_telemetry()`

Disable global telemetry.

```python
from rpycbench.utils.telemetry import disable_telemetry

disable_telemetry()
```

#### `telemetry_context(**kwargs)`

Context manager for temporary telemetry.

```python
from rpycbench.utils.telemetry import telemetry_context

with telemetry_context(slow_call_threshold=0.05) as telemetry:
    # Operations tracked
    pass
# Telemetry disabled after context
```

**Parameters**: Same as RPyCTelemetry constructor

**Returns**: Context manager yielding RPyCTelemetry

---

## Visualization

### format_call_tree

Format call history as a tree structure.

**Location**: `rpycbench.utils.visualizer`

**Signature**:

```python
format_call_tree(
    telemetry: RPyCTelemetry,
    max_depth: Optional[int] = None,
    min_duration: float = 0.0,
    show_netrefs: bool = True,
) -> str
```

**Parameters**:

- `telemetry` (RPyCTelemetry): Telemetry instance with call history
- `max_depth` (Optional[int]): Maximum depth to display. None for unlimited
- `min_duration` (float): Minimum call duration to include (seconds)
- `show_netrefs` (bool): Whether to show NetRef information

**Returns**: str (formatted tree)

**Example**:

```python
from rpycbench.utils.visualizer import format_call_tree

tree = format_call_tree(
    telemetry,
    max_depth=5,
    min_duration=0.01,
    show_netrefs=True
)
print(tree)
```

---

### format_timeline

Format call history as a timeline.

**Location**: `rpycbench.utils.visualizer`

**Signature**:

```python
format_timeline(
    telemetry: RPyCTelemetry,
    width: int = 80,
    min_duration: float = 0.0,
) -> str
```

**Parameters**:

- `telemetry` (RPyCTelemetry): Telemetry instance
- `width` (int): Width of timeline in characters
- `min_duration` (float): Minimum duration to include

**Returns**: str (formatted timeline)

**Example**:

```python
from rpycbench.utils.visualizer import format_timeline

timeline = format_timeline(telemetry, width=100)
print(timeline)
```

---

### format_netref_report

Generate NetRef usage report.

**Location**: `rpycbench.utils.visualizer`

**Signature**:

```python
format_netref_report(telemetry: RPyCTelemetry) -> str
```

**Parameters**:

- `telemetry` (RPyCTelemetry): Telemetry instance

**Returns**: str (formatted report)

**Example**:

```python
from rpycbench.utils.visualizer import format_netref_report

report = format_netref_report(telemetry)
print(report)
```

---

### format_slow_calls_report

Generate report of slow calls sorted by duration.

**Location**: `rpycbench.utils.visualizer`

**Signature**:

```python
format_slow_calls_report(
    telemetry: RPyCTelemetry,
    top_n: int = 20,
) -> str
```

**Parameters**:

- `telemetry` (RPyCTelemetry): Telemetry instance
- `top_n` (int): Number of top slow calls to include

**Returns**: str (formatted report)

**Example**:

```python
from rpycbench.utils.visualizer import format_slow_calls_report

report = format_slow_calls_report(telemetry, top_n=10)
print(report)
```

---

### format_full_report

Generate comprehensive profiling report.

**Location**: `rpycbench.utils.visualizer`

**Signature**:

```python
format_full_report(
    telemetry: RPyCTelemetry,
    include_tree: bool = True,
    include_timeline: bool = False,
    include_netrefs: bool = True,
    include_slow_calls: bool = True,
) -> str
```

**Parameters**:

- `telemetry` (RPyCTelemetry): Telemetry instance
- `include_tree` (bool): Include call tree
- `include_timeline` (bool): Include timeline
- `include_netrefs` (bool): Include NetRef report
- `include_slow_calls` (bool): Include slow calls report

**Returns**: str (formatted report)

**Example**:

```python
from rpycbench.utils.visualizer import format_full_report

report = format_full_report(
    telemetry,
    include_tree=True,
    include_timeline=False,
    include_netrefs=True,
    include_slow_calls=True
)
print(report)
```

---

## Server Management

### RPyCServer

Manages local RPyC server lifecycle.

**Location**: `rpycbench.servers.rpyc_servers`

**Constructor**:

```python
RPyCServer(
    host: str = 'localhost',
    port: int = 18812,
    mode: str = 'threaded',
    auto_register: bool = False
)
```

**Parameters**:

- `host` (str): Host to bind to
- `port` (int): Port to bind to
- `mode` (str): Server mode ('threaded', 'forking', 'oneshot')
- `auto_register` (bool): Whether to auto-register with RPyC registry

**Methods**:

#### `start()`

Start the server in a separate process.

#### `stop()`

Stop the server.

**Example**:

```python
from rpycbench.servers.rpyc_servers import RPyCServer

# As context manager
with RPyCServer(port=18812, mode='threaded') as server:
    # Server running
    # ... run tests ...
    pass
# Server stopped

# Or manually
server = RPyCServer(port=18812, mode='threaded')
server.start()
# ... run tests ...
server.stop()
```

---

### RemoteRPyCServer

Manages RPyC server on remote host via SSH.

**Location**: `rpycbench.remote.ssh`

**Constructor**:

```python
RemoteRPyCServer(
    remote_host: str,
    host: str = 'localhost',
    port: int = 18812,
    mode: str = 'threaded',
    ssh_port: int = 22,
    verbose: bool = True,
)
```

**Parameters**:

- `remote_host` (str): Remote host in format 'user@hostname'
- `host` (str): Host for RPyC server to bind to on remote machine
- `port` (int): Port for RPyC server
- `mode` (str): Server mode ('threaded', 'forking', 'oneshot')
- `ssh_port` (int): SSH port
- `verbose` (bool): Whether to print deployment progress

**Methods**:

#### `start()`

Deploy code to remote host and start server.

Automatically:
- Creates deployment archive
- Uploads via SSH
- Installs dependencies on remote host
- Starts server process
- Caches deployment (only redeploys if code changed)

#### `stop()`

Stop remote server.

**Example**:

```python
from rpycbench.remote.ssh import RemoteRPyCServer

# As context manager
with RemoteRPyCServer(
    remote_host='user@remote-server.example.com',
    port=18812,
    mode='threaded'
) as server:
    # Server deployed and running on remote host
    # Connect from local machine:
    conn = rpyc.connect('remote-server.example.com', 18812)
    # ... run tests ...
    conn.close()
# Server stopped and cleaned up

# Or manually
server = RemoteRPyCServer(remote_host='user@remote.com', port=18812)
server.start()
# ... run tests ...
server.stop()
```

---

### create_rpyc_connection

Factory for creating RPyC connections with standard configuration.

**Location**: `rpycbench.utils.connection`

**Signature**:

```python
create_rpyc_connection(
    host: str = 'localhost',
    port: int = 18812,
    timeout: int = 5
) -> rpyc.Connection
```

**Parameters**:

- `host` (str): Server hostname
- `port` (int): Server port
- `timeout` (int): Connection timeout in seconds

**Returns**: rpyc.Connection

**Example**:

```python
from rpycbench.utils.connection import create_rpyc_connection

conn = create_rpyc_connection('localhost', 18812, timeout=10)
result = conn.root.some_method()
conn.close()
```

---

## Benchmark Suite

### BenchmarkSuite

Orchestrates complete benchmark suite comparing RPyC vs HTTP across multiple dimensions.

**Location**: `rpycbench.benchmarks.suite`

**Constructor**:

```python
BenchmarkSuite(
    rpyc_host: str = 'localhost',
    rpyc_port: int = 18812,
    http_host: str = 'localhost',
    http_port: int = 5000,
    remote_host: Optional[str] = None,
)
```

**Parameters**:

- `rpyc_host` (str): RPyC server hostname
- `rpyc_port` (int): RPyC server port
- `http_host` (str): HTTP server hostname
- `http_port` (int): HTTP server port
- `remote_host` (Optional[str]): Remote host for SSH deployment ('user@hostname')

**Methods**:

#### `run_all(...)`

Run complete benchmark suite.

```python
run_all(
    test_rpyc_threaded: bool = True,
    test_rpyc_forking: bool = False,
    test_http: bool = False,
    num_serial_connections: int = 100,
    num_requests: int = 1000,
    num_parallel_clients: int = 128,
    requests_per_client: int = 100,
    test_binary_transfer: bool = False,
    binary_file_sizes: Optional[List[int]] = None,
    binary_chunk_size: int = 64 * 1024,
    binary_iterations: int = 3,
) -> BenchmarkResults
```

**Parameters**:

- `test_rpyc_threaded` (bool): Test RPyC in threaded mode
- `test_rpyc_forking` (bool): Test RPyC in forking mode
- `test_http` (bool): Test HTTP/REST
- `num_serial_connections` (int): Sample size for connection benchmarks
- `num_requests` (int): Sample size for latency benchmarks
- `num_parallel_clients` (int): Number of concurrent clients
- `requests_per_client` (int): Requests per concurrent client
- `test_binary_transfer` (bool): Whether to test large file transfers
- `binary_file_sizes` (Optional[List[int]]): File sizes for binary transfer tests
- `binary_chunk_size` (int): Chunk size for binary transfers
- `binary_iterations` (int): Iterations for binary transfer tests

**Returns**: [BenchmarkResults](#benchmarkresults)

**Example**:

```python
from rpycbench.benchmarks.suite import BenchmarkSuite

# Local testing
suite = BenchmarkSuite(
    rpyc_host='localhost',
    rpyc_port=18812,
    http_host='localhost',
    http_port=5000
)

results = suite.run_all(
    test_rpyc_threaded=True,
    test_rpyc_forking=True,
    test_http=True,
    num_requests=1000,
    num_parallel_clients=128
)

results.print_summary()

# Remote testing
remote_suite = BenchmarkSuite(
    rpyc_host='remote.example.com',
    rpyc_port=18812,
    remote_host='user@remote.example.com'
)

remote_results = remote_suite.run_all(
    test_rpyc_threaded=True,
    num_requests=1000
)

remote_results.print_summary()
```
