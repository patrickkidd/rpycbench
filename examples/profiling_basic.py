#!/usr/bin/env python3
"""
Example: Basic RPyC profiling

This example shows how to use the profiling features to track:
- Network round trips
- Netref creation and usage
- Call stacks
- Slow calls
"""

from rpycbench.servers.rpyc_servers import RPyCServer
from rpycbench.utils.profiler import create_profiled_connection
from rpycbench.utils.telemetry import RPyCTelemetry


def main():
    print("Basic RPyC Profiling Example")
    print("=" * 80)

    # Start RPyC server
    with RPyCServer(host='localhost', port=18812, mode='threaded'):

        # Create telemetry instance
        telemetry = RPyCTelemetry(
            enabled=True,
            track_netrefs=True,
            track_stacks=True,
            slow_call_threshold=0.01,  # 10ms
            deep_stack_threshold=3,
        )

        # Create profiled connection
        conn = create_profiled_connection(
            host='localhost',
            port=18812,
            telemetry_inst=telemetry,
        )

        print("\nMaking some remote calls...")
        print("-" * 80)

        # Simple call
        print("1. Simple ping call:")
        result = conn.root.ping()
        print(f"   Result: {result}")
        print(f"   Network round trips so far: {telemetry.total_network_roundtrips}")

        # Call that returns data
        print("\n2. Echo call with data:")
        data = b"Hello RPyC!" * 100
        result = conn.root.echo(data)
        print(f"   Sent {len(data)} bytes, received {len(result)} bytes")
        print(f"   Network round trips so far: {telemetry.total_network_roundtrips}")

        # Call with computation
        print("\n3. Compute call:")
        result = conn.root.compute(1000)
        print(f"   Result: {result}")
        print(f"   Network round trips so far: {telemetry.total_network_roundtrips}")

        # Multiple calls in sequence
        print("\n4. Multiple sequential calls:")
        for i in range(5):
            conn.root.ping()
        print(f"   Made 5 ping calls")
        print(f"   Network round trips so far: {telemetry.total_network_roundtrips}")

        conn.close()

        # Print detailed telemetry
        print("\n" + "=" * 80)
        telemetry.print_summary()


if __name__ == '__main__':
    main()
