# RPyC Benchmark Tests

This directory contains the comprehensive test suite for rpycbench.

## Test Coverage

### test_servers.py
- Server process isolation (separate processes from client)
- Server lifecycle management (start, stop, cleanup)
- Server readiness synchronization
- Different server modes (threaded, forking)
- All server endpoints (ping, echo, upload, download, compute, sleep)

### test_benchmarks.py
- ConnectionBenchmark (connection establishment timing)
- LatencyBenchmark (request/response round-trip time)
- BandwidthBenchmark (upload/download throughput)
- BenchmarkContext (custom benchmark integration)

### test_concurrency.py
- 128 concurrent connections
- Per-connection metrics tracking
- Different concurrency levels (10, 50, 100, 128)
- Server mode comparison under load
- Slowest connection identification

### test_telemetry.py
- Network round trip tracking
- NetRef creation and lifecycle
- Slow call detection
- Call stack depth tracking
- ProfiledConnection wrapper
- Statistics computation

### test_metrics.py
- Metrics collection (connection time, latency, bandwidth)
- Concurrent connection metrics
- Duration tracking
- Results aggregation
- Statistical calculations (mean, median, percentiles, stdev)
- JSON/dict export

### test_integration.py
- End-to-end baseline comparisons
- App integration workflows
- Error handling
- Server cleanup
- Data integrity
- Robustness testing

## Running Tests

```bash
# Run all tests
pytest rpycbench/tests/

# Run with verbose output
pytest rpycbench/tests/ -v

# Run specific test file
pytest rpycbench/tests/test_servers.py

# Run specific test
pytest rpycbench/tests/test_concurrency.py::TestHighConcurrency::test_128_concurrent_rpyc_connections

# Run tests matching pattern
pytest rpycbench/tests/ -k "concurrency"

# Run with coverage
pytest rpycbench/tests/ --cov=rpycbench --cov-report=html
```

## Test Requirements

Tests require:
- pytest >= 7.4.0
- pytest-timeout >= 2.1.0 (for timeout protection)
- All rpycbench dependencies

## Notes

- Tests use dynamic port allocation to avoid conflicts
- Servers are started/stopped for each test
- Tests verify process isolation (no GIL interference)
- 128-connection tests may take 30-60 seconds
- Tests are designed to be stable and repeatable
