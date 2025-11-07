#!/usr/bin/env python3
"""
Example: Binary file transfer benchmark

This demonstrates large file transfer performance testing:
- Configurable file sizes (1.5MB, 128MB, 500MB by default)
- Configurable chunk sizes (8KB, 64KB, 512KB, 4MB by default)
- Both chunked and non-chunked transfer modes
- Throughput measurements (Mbps) for each combination

Useful for understanding the impact of latency vs bandwidth tradeoffs.
"""

from rpycbench.benchmarks.suite import BenchmarkSuite


def run_binary_transfer_full():
    """Run complete binary transfer benchmark with default sizes"""

    print("BINARY FILE TRANSFER BENCHMARK")
    print("=" * 80)
    print("\nThis tests large file transfer performance:")
    print("  - File sizes: 1.5MB, 128MB, 500MB")
    print("  - Chunk size: 64KB (default)")
    print("  - Both chunked and non-chunked modes")
    print("  - RPyC vs HTTP comparison")
    print("  - Run multiple times with different chunk sizes to compare")
    print("=" * 80)

    suite = BenchmarkSuite()

    results = suite.run_all(
        test_rpyc_threaded=True,
        test_rpyc_forking=False,
        test_http=True,
        test_binary_transfer=True,
        binary_file_sizes=[1_572_864, 134_217_728, 524_288_000],  # 1.5MB, 128MB, 500MB
        binary_chunk_size=65_536,  # 64KB
        binary_iterations=3,
        num_serial_connections=10,
        num_requests=10,
        num_parallel_clients=1,
    )

    results.print_summary()

    with open('binary_transfer.json', 'w') as f:
        f.write(results.to_json())

    print("\n" + "=" * 80)
    print("Results saved to binary_transfer.json")
    print("\nTo analyze transfer results:")
    print("  import json")
    print("  data = json.load(open('binary_transfer.json'))")
    print("  for result in data['rpyc_threaded']['metadata']['transfer_results']:")
    print("      print(f\"{result['type']}: {result['throughput_mbps']:.2f} Mbps\")")
    print("\nTo compare chunk sizes, run with different --binary-chunk-size values:")
    print("  rpycbench --test-binary-transfer --binary-chunk-size 8192   # 8KB")
    print("  rpycbench --test-binary-transfer --binary-chunk-size 524288 # 512KB")


def run_binary_transfer_quick():
    """Run quick binary transfer test with smaller files"""

    print("\nQUICK BINARY TRANSFER TEST")
    print("=" * 80)

    suite = BenchmarkSuite()

    results = suite.run_all(
        test_rpyc_threaded=True,
        test_rpyc_forking=False,
        test_http=True,
        test_binary_transfer=True,
        binary_file_sizes=[1_048_576, 10_485_760],  # 1MB, 10MB
        binary_chunk_size=8_192,  # 8KB
        binary_iterations=2,
        num_serial_connections=5,
        num_requests=5,
        num_parallel_clients=1,
    )

    results.print_summary()


def run_binary_transfer_custom():
    """
    Custom binary transfer benchmark with specific parameters

    Demonstrates programmatic usage with context manager support.
    """
    from rpycbench.core.benchmark import BinaryTransferBenchmark, BenchmarkContext
    from rpycbench.servers.rpyc_servers import RPyCServer, create_rpyc_connection

    print("\nCUSTOM BINARY TRANSFER TEST")
    print("=" * 80)
    print("Demonstrating both direct benchmark and context manager usage")
    print("=" * 80)

    with RPyCServer(host='localhost', port=18812, mode='threaded'):
        # Method 1: Direct benchmark with 16KB chunks
        print("\n1. Direct Benchmark (16KB chunks):")
        bench = BinaryTransferBenchmark(
            name="Custom Transfer",
            protocol="rpyc",
            server_mode="threaded",
            connection_factory=lambda: create_rpyc_connection('localhost', 18812),
            upload_func=lambda conn, data: conn.root.upload_file(data),
            download_func=lambda conn, size: conn.root.download_file(size),
            upload_chunked_func=lambda conn, chunks: conn.root.upload_file_chunked(chunks),
            download_chunked_func=lambda conn, size, chunk_size: conn.root.download_file_chunked(size, chunk_size),
            file_sizes=[5_242_880],  # 5MB only
            chunk_size=16_384,  # 16KB
            iterations=3,
        )

        metrics = bench.execute()

        print("\nResults:")
        print("-" * 80)
        for result in metrics.metadata['transfer_results']:
            chunk_info = f", chunk={result['chunk_size_kb']:.0f}KB" if result['chunk_size'] else ""
            print(f"{result['type']:20s}: {result['file_size_mb']:8.1f}MB{chunk_info:20s} @ {result['throughput_mbps']:8.2f} Mbps ({result['duration']:.3f}s)")

        # Method 2: Using context manager for integration
        print("\n2. Context Manager Usage:")
        with BenchmarkContext(
            name="App Integration",
            protocol="rpyc",
            measure_bandwidth=True,
        ) as ctx:
            conn = create_rpyc_connection('localhost', 18812)

            # Your application code with measurement
            test_data = b'\x00' * 1048576  # 1MB
            for i in range(5):
                with ctx.measure_request(bytes_sent=len(test_data)):
                    conn.root.upload_file(test_data)
                    ctx.record_request(success=True)

            conn.close()

        stats = ctx.get_results().compute_statistics()
        print(f"\nContext Manager Results:")
        print(f"  Upload bandwidth: {stats['upload_bandwidth']['mean'] / (1024*1024):.2f} MB/s")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--quick':
            run_binary_transfer_quick()
        elif sys.argv[1] == '--custom':
            run_binary_transfer_custom()
        else:
            print("Usage: python binary_transfer.py [--quick|--custom]")
            sys.exit(1)
    else:
        run_binary_transfer_full()
