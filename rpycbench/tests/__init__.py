"""RPyC Benchmark Test Suite

This test suite provides comprehensive coverage for:
- Server process isolation (no GIL interference)
- Multiple server modes (threaded, forking)
- Connection, latency, bandwidth, and concurrent benchmarks
- High concurrency testing (128+ connections)
- Per-connection metrics tracking
- Telemetry and profiling
- Metrics collection and statistics
- End-to-end workflows
- Error handling and robustness

Run tests with:
    pytest rpycbench/tests/
    pytest rpycbench/tests/ -v  # verbose
    pytest rpycbench/tests/ -k test_name  # specific test
"""
