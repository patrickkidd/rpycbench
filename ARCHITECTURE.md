# rpycbench Architecture

This document describes the key components and design decisions behind the rpycbench benchmark suite.

## Overview

rpycbench compares the performance of RPyC (Remote Python Call) against HTTP/REST APIs across three server configurations:

1. **RPyC Threaded** - Thread-per-connection model
2. **RPyC Forking** - Process-per-connection model
3. **HTTP Threaded** - Flask with threaded request handling

All servers run in separate processes (via `multiprocessing.Process`) to isolate them from the client's GIL and provide fair comparison.

## Core Components

### 1. Server Implementations

#### RPyC Servers ([rpyc_servers.py](rpycbench/servers/rpyc_servers.py))

**BenchmarkService** (lines 12-59)
- RPyC service exposing remote methods for benchmarking
- Methods: `ping()`, `echo()`, `upload()`, `download()`, `compute()`, `sleep()`
- File transfer methods: `upload_file()`, `download_file()`, `upload_file_chunked()`, `download_file_chunked()`

**Server Modes** (_run_rpyc_server, lines 61-109)
- **ThreadedServer** (lines 76-82): Spawns new thread for each client connection
- **ForkingServer** (lines 83-89): Spawns new process for each client connection
- Both use pickle serialization via RPyC protocol
- Configuration: `allow_public_attrs=True`, `allow_pickle=True`, `sync_request_timeout=30s`

**RPyCServer Wrapper** (lines 111-186)
- Context manager for server lifecycle management
- Runs server in separate process to isolate from client
- Uses `multiprocessing.Event()` for readiness signaling
- Socket verification ensures server is accepting connections before proceeding

**Connection Factory** (lines 188-199)
- `create_rpyc_connection()`: Creates client connection with matching protocol config
- Returns RPyC connection object with `.root` attribute for remote method calls

#### HTTP Server ([http_servers.py](rpycbench/servers/http_servers.py))

**Flask Application** (_run_http_server, lines 12-112)
- REST endpoints mirroring RPyC service methods
- `GET /ping` - latency testing
- `POST /upload`, `GET /download/<size>` - bandwidth testing
- `POST /upload-file`, `GET /download-file/<size>` - file transfer
- `POST /upload-file-chunked`, `GET /download-file-chunked/<size>/<chunk_size>` - chunked transfers
- **Line 104**: `threaded=True` enables Flask's threaded mode (thread-per-request)

**HTTPBenchmarkServer Wrapper** (lines 114-188)
- Context manager for server lifecycle management
- Runs Flask server in separate process
- Same readiness signaling pattern as RPyC server

**Connection Factory** (lines 190-203)
- `create_http_session()`: Creates `requests.Session` with connection pooling
- `HTTPAdapter`: 10 connections, max 100 pool size, 3 retries
- Supports HTTP keep-alive for persistent connections

### 2. Benchmark Framework ([benchmark.py](rpycbench/core/benchmark.py))

#### Base Framework (lines 14-51)

**BenchmarkBase** abstract class defines lifecycle:
```python
def execute() -> BenchmarkMetrics:
    setup()       # Create connections, warmup
    metrics.start()
    run()         # Actual benchmark
    metrics.end()
    teardown()    # Cleanup connections
    return metrics
```

All benchmarks follow this pattern with `BenchmarkMetrics` tracking results.

#### ConnectionBenchmark (lines 141-182)

**Purpose**: Measure connection establishment overhead

**Process**:
1. Sequential creation of `num_connections` (default 100) connections
2. Time each: `start → connection_factory() → duration`
3. Store all connections for cleanup

**What it tests**: Server's ability to accept and establish new connections quickly

#### LatencyBenchmark (lines 184-236)

**Purpose**: Measure request/response latency

**Process**:
1. Create single persistent connection
2. Warmup: 10 requests to prime caches
3. Timed requests: `num_requests` (default 1000) sequential calls
4. Time each: `start → request_func(conn) → duration`

**What it tests**: Round-trip time for minimal requests under no load

#### BandwidthBenchmark (lines 238-298)

**Purpose**: Measure data transfer throughput

**Process**:
1. Test multiple data sizes: 1KB, 10KB, 100KB, 1MB
2. For each size, run 10 iterations:
   - **Upload**: `upload_func(conn, data)`
   - **Download**: `download_func(conn, size)`
3. Calculate bandwidth: `bytes / duration`

**What it tests**: Protocol overhead and serialization cost at different data sizes

#### BinaryTransferBenchmark (lines 300-498)

**Purpose**: Test large file transfers with realistic sizes

**File sizes**: 1.5MB, 128MB, 500MB
**Chunk size**: 64KB (configurable)
**Iterations**: 3 per test

**Process**:
1. **Non-chunked transfers** (lines 376-426):
   - Single call with entire file
   - Tests maximum throughput with minimal call overhead
2. **Chunked transfers** (lines 429-489):
   - Multiple calls with 64KB chunks
   - Tests latency impact when data must be split

**What it tests**:
- Raw transfer throughput for large files
- Impact of chunking on overall transfer time
- Tradeoff between latency and bandwidth

#### ConcurrentBenchmark (lines 500-647)

**Purpose**: Measure performance under concurrent load

**Configuration**:
- `num_clients`: Number of concurrent connections (default 10 for suite, supports 128+)
- `requests_per_client`: Requests each client makes (default 100)
- `max_workers`: Thread pool size (capped at 128)

**Process** (lines 586-632):
1. Create `ThreadPoolExecutor` with `num_clients` threads
2. Each worker thread (`_client_worker`, lines 537-584):
   - Establishes own connection
   - Makes `requests_per_client` requests
   - Tracks per-client metrics (latencies, errors)
   - Closes connection
3. Aggregate all client metrics

**Critical detail**: All clients run in threads **within the client process**, not separate processes. This tests how well the server handles concurrent load from multiple simultaneous connections.

**What it tests**:
- Server's ability to handle multiple concurrent connections
- Performance degradation under load
- Connection establishment overhead under concurrent load

### 3. Orchestration ([suite.py](rpycbench/benchmarks/suite.py))

#### BenchmarkSuite (lines 17-286)

**Configuration**:
- `num_serial_connections`: Connections for ConnectionBenchmark (default 100)
- `num_requests`: Requests for LatencyBenchmark (default 1000)
- `num_parallel_clients`: Concurrent clients for ConcurrentBenchmark (default 10)
- `requests_per_client`: Requests per client in concurrent test (default 100)

#### Execution Flow (run_all, lines 35-104)

**Sequential execution** of three server configurations:

1. **RPyC Threaded** (lines 55-68):
   ```python
   with RPyCServer(host, port, mode='threaded'):
       _run_rpyc_benchmarks(...)
   ```
   - Starts ThreadedServer in separate process
   - Runs all 5 benchmark types
   - Server context manager ensures cleanup

2. **RPyC Forking** (lines 71-84):
   ```python
   with RPyCServer(host, port, mode='forking'):
       _run_rpyc_benchmarks(...)
   ```
   - Starts ForkingServer in separate process
   - Runs same 5 benchmark types

3. **HTTP Threaded** (lines 87-99):
   ```python
   with HTTPBenchmarkServer(host, port, threaded=True):
       _run_http_benchmarks(...)
   ```
   - Starts Flask server with `threaded=True`
   - Runs same 5 benchmark types

#### RPyC Benchmark Execution (_run_rpyc_benchmarks, lines 106-193)

**Connection pattern**:
```python
connection_factory = lambda: create_rpyc_connection(host, port)
request_func = lambda conn: conn.root.ping()
```

- Direct method calls via `conn.root.method()`
- Binary data passed as Python objects (pickle serialization)
- Single persistent TCP connection per benchmark

#### HTTP Benchmark Execution (_run_http_benchmarks, lines 194-286)

**Connection pattern**:
```python
connection_factory = lambda: create_http_session()
request_func = lambda session: session.get(f"{url}/ping")
```

- REST endpoints via `session.get/post(url)`
- Binary data as raw bytes in request body
- Chunked data as JSON with hex-encoded chunks
- HTTP connection pooling via requests.Session

## Critical Differences Between Server Modes

| Aspect | RPyC Threaded | RPyC Forking | HTTP Threaded |
|--------|---------------|--------------|---------------|
| **Server concurrency** | Thread per connection | Process per connection | Thread per request |
| **Server file** | [rpyc_servers.py:76-82](rpycbench/servers/rpyc_servers.py#L76-L82) | [rpyc_servers.py:83-89](rpycbench/servers/rpyc_servers.py#L83-L89) | [http_servers.py:104](rpycbench/servers/http_servers.py#L104) |
| **Isolation** | Low (shared memory) | High (separate process) | Low (shared memory) |
| **Connection cost** | Low | High (fork overhead) | Low |
| **Memory overhead** | Low | High (copy-on-write) | Low |
| **GIL impact** | High (threads share GIL) | None (separate processes) | High (threads share GIL) |
| **Serialization** | pickle (binary) | pickle (binary) | JSON + HTTP headers |
| **Transport** | Raw TCP | Raw TCP | HTTP over TCP |
| **Protocol overhead** | Minimal (RPyC) | Minimal (RPyC) | High (HTTP headers, JSON) |
| **Client API** | `conn.root.method()` | `conn.root.method()` | `session.get/post(url)` |
| **Keep-alive** | Single persistent connection | Single persistent connection | HTTP connection pooling |

## Performance Expectations

Based on the architecture:

### Connection Establishment
- **RPyC Threaded**: Fast (thread creation)
- **RPyC Forking**: Slow (process fork overhead)
- **HTTP**: Fast (thread creation)

### Latency (minimal requests)
- **RPyC Threaded**: Fastest (minimal protocol overhead)
- **RPyC Forking**: Fast (minimal protocol overhead)
- **HTTP**: Slower (HTTP headers, JSON parsing)

### Bandwidth (large transfers)
- **RPyC Threaded**: Fast (pickle is efficient for binary)
- **RPyC Forking**: Fast (pickle is efficient for binary)
- **HTTP**: Slower for chunked (JSON hex encoding), comparable for raw binary

### Concurrent Load
- **RPyC Threaded**: May degrade due to GIL contention
- **RPyC Forking**: Better isolation, higher memory cost
- **HTTP**: May degrade due to GIL contention

## Design Decisions

### 1. Separate Server Processes
All servers run in separate processes via `multiprocessing.Process` to:
- Isolate server from client's GIL
- Prevent client measurement from affecting server performance
- Provide fair comparison between protocols

### 2. Readiness Signaling
Both server types use:
1. `multiprocessing.Event()` - server signals when started
2. Socket verification - client verifies connection acceptance

This ensures benchmarks don't start until server is truly ready.

### 3. Context Managers
All servers and some benchmarks use context managers (`__enter__`/`__exit__`) to:
- Guarantee cleanup even on errors
- Simplify server lifecycle management
- Make benchmark code cleaner

### 4. Concurrent vs Sequential Tests
- **ConnectionBenchmark**: Sequential (tests raw connection overhead)
- **LatencyBenchmark**: Sequential (tests baseline latency)
- **BandwidthBenchmark**: Sequential (tests maximum throughput)
- **ConcurrentBenchmark**: Parallel threads (tests under load)

This separation allows understanding both optimal and realistic performance.

### 5. HTTP Chunked Transfer Encoding
HTTP chunked transfers use JSON with hex-encoded chunks rather than streaming because:
- Simplifies implementation for benchmarking
- Allows measuring serialization overhead
- Tests JSON parsing performance
- More comparable to RPyC's object serialization

This may not represent optimal HTTP performance but provides fair protocol comparison.

## Benchmark Interpretation

### When RPyC Performs Better
- Minimal request latency (less protocol overhead)
- Binary data transfer (efficient pickle serialization)
- Persistent connections (no HTTP header overhead per request)
- Python-to-Python communication (native object serialization)

### When HTTP Performs Better
- Multi-language environments (standard protocol)
- Firewall-friendly deployments (standard port 80/443)
- REST API compatibility (standard HTTP verbs)
- Caching and proxy support (HTTP infrastructure)

### When Forking Performs Better
- CPU-bound server operations (no GIL contention)
- Isolation requirements (separate memory space)
- Per-connection state that shouldn't leak

### When Threading Performs Better
- I/O-bound operations (less overhead than forking)
- Memory-constrained environments (shared memory)
- High connection rate (faster than fork)
