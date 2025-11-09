"""RPyC vs HTTP/REST Benchmark Suite"""

from rpycbench.core.benchmark import (
    BenchmarkContext,
    ConnectionBenchmark,
    LatencyBenchmark,
    BandwidthBenchmark,
    ConcurrentBenchmark,
)
from rpycbench.core.metrics import BenchmarkMetrics, BenchmarkResults
from rpycbench.utils.telemetry import (
    RPyCTelemetry,
    get_telemetry,
    enable_telemetry,
    disable_telemetry,
    telemetry_context,
)
from rpycbench.utils.profiler import (
    ProfiledConnection,
    create_profiled_connection,
    profile_rpyc_calls,
)

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError

try:
    __version__ = version("rpycbench")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
__all__ = [
    "BenchmarkContext",
    "ConnectionBenchmark",
    "LatencyBenchmark",
    "BandwidthBenchmark",
    "ConcurrentBenchmark",
    "BenchmarkMetrics",
    "BenchmarkResults",
    "RPyCTelemetry",
    "get_telemetry",
    "enable_telemetry",
    "disable_telemetry",
    "telemetry_context",
    "ProfiledConnection",
    "create_profiled_connection",
    "profile_rpyc_calls",
]
