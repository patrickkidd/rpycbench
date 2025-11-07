#!/usr/bin/env python3
"""
Example: Diagnosing slow RPyC calls in your application

This shows how to use profiling to identify and diagnose performance issues
in your application that uses RPyC.
"""

import rpyc
import time
from rpycbench.servers.rpyc_servers import RPyCServer
from rpycbench.utils.profiler import create_profiled_connection
from rpycbench.utils.telemetry import RPyCTelemetry
from rpycbench.utils.visualizer import format_full_report


class MyApplication:
    """Example application that might have performance issues"""

    def __init__(self, conn):
        self.conn = conn

    def process_batch(self, items):
        """
        Process a batch of items.
        This has a performance issue: making a remote call for each item!
        """
        results = []
        for item in items:
            # BAD: This makes N network round trips!
            result = self.conn.root.compute(item)
            results.append(result)
        return results

    def process_batch_optimized(self, items):
        """
        Optimized version that batches remote calls.
        This would require a batch API on the server side.
        """
        # GOOD: Single network round trip
        # (assuming the server has a batch_compute method)
        return [self.conn.root.compute(item) for item in items]

    def nested_operations(self):
        """
        Another common issue: deeply nested remote calls
        """
        # Each of these might trigger additional remote calls
        obj = self.conn.root.ping()  # Returns something
        # If we then access attributes or call methods on netrefs,
        # we create more round trips
        return obj


def diagnose_performance_issue():
    """Diagnose the performance issue in process_batch"""

    print("DIAGNOSING SLOW BATCH PROCESSING")
    print("=" * 80)

    with RPyCServer(host='localhost', port=18812, mode='threaded'):

        # Create telemetry with aggressive thresholds
        telemetry = RPyCTelemetry(
            enabled=True,
            track_netrefs=True,
            track_stacks=True,
            slow_call_threshold=0.05,  # 50ms
            deep_stack_threshold=2,
        )

        conn = create_profiled_connection(
            host='localhost',
            port=18812,
            telemetry_inst=telemetry,
        )

        app = MyApplication(conn)

        # Simulate the slow operation
        print("\nProcessing batch of 10 items...")
        print("(This will be slow due to N network round trips)")
        print("-" * 80)

        start = time.time()
        items = list(range(10, 20))
        results = app.process_batch(items)
        duration = time.time() - start

        print(f"\nCompleted in {duration*1000:.2f}ms")
        print(f"Average time per item: {duration/len(items)*1000:.2f}ms")

        conn.close()

        # Analyze the telemetry
        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)

        stats = telemetry.get_statistics()

        print(f"\nTotal network round trips: {stats['total_network_roundtrips']}")
        print(f"Expected round trips: 1 (connection) + 1 (batch call) = 2")
        print(f"Actual round trips: {stats['total_network_roundtrips']}")
        print(f"PROBLEM: Making {stats['total_network_roundtrips'] - 1} calls instead of 1!")

        print("\nCall pattern analysis:")
        print(f"  - Each item requires a separate network round trip")
        print(f"  - With {len(items)} items, that's {len(items)} round trips")
        print(f"  - Average latency per call: {stats['avg_call_duration']*1000:.2f}ms")
        print(f"  - Total overhead: {len(items) * stats['avg_call_duration']*1000:.2f}ms just from network!")

        print("\n" + "=" * 80)
        print("SOLUTION:")
        print("=" * 80)
        print("1. Create a batch API on the server that processes all items in one call")
        print("2. Or, minimize the data sent/received per call")
        print("3. Or, use async/concurrent calls if items are independent")

        # Show full telemetry report
        print("\n" + "=" * 80)
        print("DETAILED TELEMETRY REPORT")
        print(format_full_report(telemetry, include_timeline=True))


def show_netref_overhead():
    """Show overhead from excessive netref usage"""

    print("\n\n")
    print("DIAGNOSING NETREF OVERHEAD")
    print("=" * 80)

    with RPyCServer(host='localhost', port=18812, mode='threaded'):

        telemetry = RPyCTelemetry(
            enabled=True,
            track_netrefs=True,
        )

        conn = create_profiled_connection(
            host='localhost',
            port=18812,
            telemetry_inst=telemetry,
        )

        print("\nMaking calls that might return netrefs...")
        print("-" * 80)

        # Simple value calls (no netrefs)
        for i in range(5):
            conn.root.ping()

        conn.close()

        # Analyze netref usage
        print("\n" + "=" * 80)
        print("NETREF ANALYSIS")
        print("=" * 80)

        stats = telemetry.get_statistics()
        print(f"Total NetRefs created: {stats['total_netrefs_created']}")
        print(f"Active NetRefs: {stats['active_netrefs']}")

        if stats['total_netrefs_created'] > 0:
            print("\nNetRefs detected! Each netref operation requires network round trips.")
            print("Consider:")
            print("  - Return simple values instead of objects when possible")
            print("  - Batch operations on netrefs")
            print("  - Use async patterns for netref-heavy operations")
        else:
            print("\nGood! No unnecessary netrefs created.")
            print("All calls returned simple values efficiently.")


def main():
    print("RPyC Performance Diagnosis Example")
    print("=" * 80)
    print("\nThis example shows how to use profiling to identify and fix")
    print("common performance issues in RPyC applications.")
    print()

    # Diagnose the batch processing issue
    diagnose_performance_issue()

    # Show netref overhead
    show_netref_overhead()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("Use profiling to:")
    print("  1. Count actual network round trips vs expected")
    print("  2. Identify slow calls and deep call stacks")
    print("  3. Track netref creation and usage")
    print("  4. Visualize call patterns with trees and timelines")
    print("  5. Compare baseline vs application overhead")
    print()


if __name__ == '__main__':
    main()
