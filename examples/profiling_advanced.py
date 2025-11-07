#!/usr/bin/env python3
"""
Example: Advanced RPyC profiling with visualization

This example demonstrates:
- Call tree visualization
- Timeline visualization
- NetRef tracking
- Slow call detection
- Deep stack detection
"""

import rpyc
from rpycbench.servers.rpyc_servers import RPyCServer, BenchmarkService
from rpycbench.utils.profiler import profile_rpyc_calls
from rpycbench.utils.visualizer import (
    format_call_tree,
    format_timeline,
    format_netref_report,
    format_slow_calls_report,
    format_full_report,
)


# Extended service with nested calls
class AdvancedService(BenchmarkService):
    """Service with methods that make nested calls"""

    def exposed_nested_call_level_1(self):
        """First level of nested calls"""
        return self.exposed_nested_call_level_2()

    def exposed_nested_call_level_2(self):
        """Second level of nested calls"""
        return self.exposed_nested_call_level_3()

    def exposed_nested_call_level_3(self):
        """Third level of nested calls"""
        import time
        time.sleep(0.05)  # Simulate some work
        return "nested_result"

    def exposed_get_object(self):
        """Return an object (creates netref)"""
        class RemoteObject:
            def method_a(self):
                return "result_a"

            def method_b(self):
                return self.method_a()

        return RemoteObject()


def main():
    print("Advanced RPyC Profiling Example")
    print("=" * 80)

    # Start server with advanced service
    # Note: For this example we'll use the basic service since we can't easily
    # swap services. In production you'd start your custom service.

    with RPyCServer(host='localhost', port=18812, mode='threaded'):
        conn = rpyc.connect('localhost', 18812, config={
            'allow_public_attrs': True,
            'allow_pickle': True,
        })

        # Use profiling context manager
        with profile_rpyc_calls(
            conn,
            print_summary=False,
            slow_call_threshold=0.01,  # 10ms
            deep_stack_threshold=2,
        ) as profiled:

            print("\nScenario 1: Simple calls")
            print("-" * 40)
            for i in range(3):
                profiled.root.ping()

            print("\nScenario 2: Data transfer")
            print("-" * 40)
            data = b"x" * 10240  # 10KB
            profiled.root.upload(data)
            result = profiled.root.download(5120)

            print("\nScenario 3: Computation (slower)")
            print("-" * 40)
            profiled.root.compute(10000)

            print("\nScenario 4: Sleep (triggers slow call detection)")
            print("-" * 40)
            profiled.root.sleep(0.02)

            telemetry = profiled.telemetry

        # Generate visualizations
        print("\n" + "=" * 80)
        print("CALL TREE VISUALIZATION")
        print(format_call_tree(telemetry, max_depth=10))

        print("\n" + "=" * 80)
        print("TIMELINE VISUALIZATION")
        print(format_timeline(telemetry, width=60))

        print("\n" + "=" * 80)
        print("NETREF REPORT")
        print(format_netref_report(telemetry))

        print("\n" + "=" * 80)
        print("SLOW CALLS REPORT")
        print(format_slow_calls_report(telemetry, top_n=10))

        print("\n" + "=" * 80)
        print("FULL TELEMETRY REPORT")
        print("=" * 80)
        telemetry.print_summary()


if __name__ == '__main__':
    main()
