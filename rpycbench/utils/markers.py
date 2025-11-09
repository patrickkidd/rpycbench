"""Critical section markers for rpycbench profiling

Markers allow you to identify important time windows in your application
for detailed profiling analysis. They work as no-ops when autobench is not active.
"""

import time
from contextlib import contextmanager
from typing import Optional
from dataclasses import dataclass, field
from collections import deque

from rpycbench.utils.telemetry import get_telemetry


@dataclass
class Marker:
    """Represents a profiling marker for a critical section"""

    name: str
    start_time: float
    end_time: Optional[float] = None
    start_round_trips: int = 0
    end_round_trips: int = 0
    start_netrefs: int = 0
    end_netrefs: int = 0
    start_stack_depth: int = 0
    parent_marker: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def round_trips(self) -> int:
        return self.end_round_trips - self.start_round_trips

    @property
    def netrefs_created(self) -> int:
        return self.end_netrefs - self.start_netrefs


class MarkerManager:
    """Manages profiling markers and critical sections"""

    def __init__(self):
        self._enabled = False
        self._markers = []
        self._active_markers = deque()

    def enable(self):
        """Enable marker tracking"""
        self._enabled = True

    def disable(self):
        """Disable marker tracking"""
        self._enabled = False

    def start(self, name: str) -> Optional[Marker]:
        """Start a marker for a critical section

        Args:
            name: Descriptive name for the critical section

        Returns:
            Marker object if enabled, None otherwise
        """
        if not self._enabled:
            return None

        telemetry = get_telemetry()
        parent = self._active_markers[-1].name if self._active_markers else None

        marker = Marker(
            name=name,
            start_time=time.time(),
            start_round_trips=telemetry.total_network_roundtrips,
            start_netrefs=telemetry.total_netrefs_created,
            start_stack_depth=telemetry.get_current_stack_depth(),
            parent_marker=parent,
        )

        self._markers.append(marker)
        self._active_markers.append(marker)
        return marker

    def end(self):
        """End the most recent marker"""
        if not self._enabled or not self._active_markers:
            return

        marker = self._active_markers.pop()
        telemetry = get_telemetry()

        marker.end_time = time.time()
        marker.end_round_trips = telemetry.total_network_roundtrips
        marker.end_netrefs = telemetry.total_netrefs_created

    @contextmanager
    def section(self, name: str):
        """Context manager for marking a critical section

        Example:
            with mark.section("Establishing connections"):
                for i in range(128):
                    connections.append(rpyc.connect(host, port))
        """
        marker = self.start(name)
        try:
            yield marker
        finally:
            self.end()

    def get_markers(self):
        """Get all completed markers"""
        return [m for m in self._markers if m.end_time is not None]

    def print_markers(self):
        """Print human-readable marker summary"""
        markers = self.get_markers()

        if not markers:
            print("\nNo markers recorded.\n")
            return

        print(f"\n{'='*80}")
        print("PROFILING MARKERS - CRITICAL SECTIONS")
        print(f"{'='*80}")

        for marker in markers:
            indent = "  " * (marker.name.count("→") if marker.parent_marker else 0)

            print(f"{indent}{marker.name}")
            print(f"{indent}  Duration:       {marker.duration*1000:8.2f}ms")
            print(f"{indent}  Round Trips:    {marker.round_trips:8d}")
            print(f"{indent}  NetRefs Created: {marker.netrefs_created:8d}")

            if marker.parent_marker:
                print(f"{indent}  Parent:         {marker.parent_marker}")

            print()

        print(f"{'='*80}\n")

    def reset(self):
        """Clear all markers"""
        self._markers.clear()
        self._active_markers.clear()


_global_marker_manager = MarkerManager()


def get_marker_manager() -> MarkerManager:
    """Get global marker manager instance"""
    return _global_marker_manager


class mark:
    """Convenience class for marker operations

    Usage:
        from rpycbench import mark

        mark.start("Establishing connections")
        # ... critical code ...
        mark.end()

        # Or use context manager:
        with mark.section("Establishing connections"):
            # ... critical code ...
    """

    @staticmethod
    def start(name: str):
        """Start a marker (no-op if autobench not running)"""
        return _global_marker_manager.start(name)

    @staticmethod
    def end():
        """End the most recent marker (no-op if autobench not running)"""
        _global_marker_manager.end()

    @staticmethod
    @contextmanager
    def section(name: str):
        """Context manager for critical section (no-op if autobench not running)"""
        with _global_marker_manager.section(name):
            yield
