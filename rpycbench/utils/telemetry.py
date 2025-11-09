"""RPyC telemetry and profiling utilities"""

import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
import rpyc
from rpyc.core import netref
import inspect
import traceback as tb


@dataclass
class RPyCCallInfo:
    """Information about a single RPyC remote call"""

    call_id: int
    timestamp: float
    method_name: str
    call_type: str  # 'method', 'getattr', 'setattr', 'call'
    parent_call_id: Optional[int] = None
    duration: Optional[float] = None
    is_netref: bool = False
    netref_id: Optional[int] = None
    result_is_netref: bool = False
    result_netref_id: Optional[int] = None
    exception: Optional[str] = None
    stack_depth: int = 0
    source_location: Optional[str] = None

    def __str__(self):
        if self.duration:
            return f"{self.method_name} ({self.call_type}) [{self.duration*1000:.2f}ms]"
        return f"{self.method_name} ({self.call_type})"


@dataclass
class NetRefInfo:
    """Information about a netref object"""

    netref_id: int
    created_at: float
    class_name: str
    num_accesses: int = 0
    num_method_calls: int = 0
    num_attr_accesses: int = 0
    last_access: Optional[float] = None
    created_by_call_id: Optional[int] = None

    def __str__(self):
        age = time.time() - self.created_at
        return (f"NetRef<{self.class_name}> id={self.netref_id} "
                f"age={age:.2f}s calls={self.num_method_calls} "
                f"attrs={self.num_attr_accesses}")


class RPyCTelemetry:
    """
    Telemetry system for tracking RPyC operations

    Tracks:
    - Network round trips
    - Netref creation and lifecycle
    - Call stacks and nesting
    - Performance metrics
    """

    def __init__(
        self,
        enabled: bool = True,
        track_netrefs: bool = True,
        track_stacks: bool = True,
        slow_call_threshold: float = 0.1,  # seconds
        deep_stack_threshold: int = 5,
    ):
        self.enabled = enabled
        self.track_netrefs = track_netrefs
        self.track_stacks = track_stacks
        self.slow_call_threshold = slow_call_threshold
        self.deep_stack_threshold = deep_stack_threshold

        # Counters
        self.total_calls = 0
        self.total_network_roundtrips = 0
        self.total_netrefs_created = 0
        self.active_netrefs = 0

        # Call tracking
        self._call_counter = 0
        self._call_stack = deque()  # Stack of active call IDs
        self._calls: Dict[int, RPyCCallInfo] = {}
        self._call_history: List[RPyCCallInfo] = []

        # Netref tracking
        self._netrefs: Dict[int, NetRefInfo] = {}
        self._netref_counter = 0

        # Performance tracking
        self.slow_calls: List[RPyCCallInfo] = []
        self.deep_stacks: List[tuple] = []  # (depth, call_stack)

        # Thread safety
        self._lock = threading.Lock()

    def start_call(
        self,
        method_name: str,
        call_type: str = 'method',
        is_netref: bool = False,
        netref_id: Optional[int] = None,
    ) -> int:
        """Start tracking a remote call"""
        if not self.enabled:
            return -1

        with self._lock:
            self._call_counter += 1
            call_id = self._call_counter
            self.total_calls += 1
            self.total_network_roundtrips += 1

            parent_id = self._call_stack[-1] if self._call_stack else None

            source_location = None
            if self.track_stacks:
                frame = inspect.currentframe()
                try:
                    caller_frame = frame.f_back.f_back.f_back
                    if caller_frame:
                        filename = caller_frame.f_code.co_filename
                        lineno = caller_frame.f_lineno
                        func_name = caller_frame.f_code.co_name
                        source_location = f"{filename}:{lineno} in {func_name}"
                except:
                    pass
                finally:
                    del frame

            call_info = RPyCCallInfo(
                call_id=call_id,
                timestamp=time.time(),
                method_name=method_name,
                call_type=call_type,
                parent_call_id=parent_id,
                is_netref=is_netref,
                netref_id=netref_id,
                stack_depth=len(self._call_stack),
                source_location=source_location,
            )

            self._calls[call_id] = call_info
            self._call_stack.append(call_id)

            # Track netref access
            if is_netref and netref_id and self.track_netrefs:
                if netref_id in self._netrefs:
                    netref_info = self._netrefs[netref_id]
                    netref_info.num_accesses += 1
                    netref_info.last_access = time.time()
                    if call_type == 'method':
                        netref_info.num_method_calls += 1
                    else:
                        netref_info.num_attr_accesses += 1

            return call_id

    def end_call(
        self,
        call_id: int,
        result_is_netref: bool = False,
        result_netref_id: Optional[int] = None,
        exception: Optional[Exception] = None,
    ):
        """End tracking a remote call"""
        if not self.enabled or call_id < 0:
            return

        with self._lock:
            if call_id not in self._calls:
                return

            call_info = self._calls[call_id]
            call_info.duration = time.time() - call_info.timestamp
            call_info.result_is_netref = result_is_netref
            call_info.result_netref_id = result_netref_id

            if exception:
                call_info.exception = str(exception)

            # Check for slow calls
            if call_info.duration >= self.slow_call_threshold:
                self.slow_calls.append(call_info)

            # Check for deep stacks
            if self.track_stacks and len(self._call_stack) >= self.deep_stack_threshold:
                self.deep_stacks.append((len(self._call_stack), list(self._call_stack)))

            # Remove from active stack
            if self._call_stack and self._call_stack[-1] == call_id:
                self._call_stack.pop()

            # Move to history
            self._call_history.append(call_info)
            del self._calls[call_id]

    def register_netref(
        self,
        netref_obj: Any,
        created_by_call_id: Optional[int] = None,
    ) -> int:
        """Register a netref object"""
        if not self.enabled or not self.track_netrefs:
            return -1

        with self._lock:
            self._netref_counter += 1
            netref_id = self._netref_counter
            self.total_netrefs_created += 1
            self.active_netrefs += 1

            class_name = type(netref_obj).__name__
            if hasattr(netref_obj, '____class__'):
                try:
                    class_name = netref_obj.____class__.__name__
                except:
                    pass

            netref_info = NetRefInfo(
                netref_id=netref_id,
                created_at=time.time(),
                class_name=class_name,
                created_by_call_id=created_by_call_id,
            )

            self._netrefs[netref_id] = netref_info
            return netref_id

    def unregister_netref(self, netref_id: int):
        """Unregister a netref object"""
        if not self.enabled or netref_id < 0:
            return

        with self._lock:
            if netref_id in self._netrefs:
                del self._netrefs[netref_id]
                self.active_netrefs -= 1

    def get_current_stack_depth(self) -> int:
        """Get current call stack depth"""
        with self._lock:
            return len(self._call_stack)

    def get_call_stack(self) -> List[RPyCCallInfo]:
        """Get current call stack"""
        with self._lock:
            return [self._calls.get(cid) for cid in self._call_stack if cid in self._calls]

    def _build_call_chain(self, call_id: int) -> List[RPyCCallInfo]:
        """Build chain of calls from root to given call_id"""
        chain = []
        current_call = next((c for c in self._call_history if c.call_id == call_id), None)

        while current_call:
            chain.insert(0, current_call)
            if current_call.parent_call_id:
                current_call = next((c for c in self._call_history if c.call_id == current_call.parent_call_id), None)
            else:
                break

        return chain

    def print_call_stack(self, title: str = "RPyC Call Stack"):
        """Print ASCII representation of current call stack"""
        print(f"\n{'='*80}")
        print(f"{title}")
        print(f"{'='*80}")

        stack = self.get_call_stack()

        if not stack:
            print("(empty stack)")
            return

        for i, call in enumerate(stack):
            indent = "  " * i
            arrow = "└─> " if i == len(stack) - 1 else "├─> "

            netref_str = ""
            if call.is_netref:
                netref_str = f" [NetRef #{call.netref_id}]"

            elapsed = time.time() - call.timestamp
            print(f"{indent}{arrow}{call.method_name} ({call.call_type}){netref_str} [{elapsed*1000:.2f}ms]")

        print(f"{'='*80}\n")

    def get_statistics(self) -> Dict[str, Any]:
        """Get telemetry statistics"""
        with self._lock:
            avg_call_duration = 0
            if self._call_history:
                durations = [c.duration for c in self._call_history if c.duration]
                if durations:
                    avg_call_duration = sum(durations) / len(durations)

            return {
                'total_calls': self.total_calls,
                'total_network_roundtrips': self.total_network_roundtrips,
                'total_netrefs_created': self.total_netrefs_created,
                'active_netrefs': self.active_netrefs,
                'current_stack_depth': len(self._call_stack),
                'max_stack_depth': max([d for d, _ in self.deep_stacks], default=0),
                'num_slow_calls': len(self.slow_calls),
                'avg_call_duration': avg_call_duration,
                'call_history_size': len(self._call_history),
            }

    def print_summary(self):
        """Print telemetry summary"""
        stats = self.get_statistics()

        print(f"\n{'='*80}")
        print("RPyC TELEMETRY SUMMARY")
        print(f"{'='*80}")
        print(f"Total Calls:              {stats['total_calls']}")
        print(f"Network Round Trips:      {stats['total_network_roundtrips']}")
        print(f"NetRefs Created:          {stats['total_netrefs_created']}")
        print(f"Active NetRefs:           {stats['active_netrefs']}")
        print(f"Current Stack Depth:      {stats['current_stack_depth']}")
        print(f"Max Stack Depth:          {stats['max_stack_depth']}")
        print(f"Slow Calls (>{self.slow_call_threshold}s): {stats['num_slow_calls']}")
        print(f"Avg Call Duration:        {stats['avg_call_duration']*1000:.2f}ms")

        # Show slow calls with call stacks
        if self.slow_calls:
            print(f"\n{'-'*80}")
            print(f"SLOW CALLS (>{self.slow_call_threshold}s):")
            print(f"{'-'*80}")

            for call in self.slow_calls[-10:]:  # Last 10
                print(f"\n  {call.method_name} ({call.call_type})")
                print(f"    Duration:    {call.duration*1000:8.2f}ms")
                print(f"    Stack Depth: {call.stack_depth}")

                if call.source_location:
                    print(f"    Called from: {call.source_location}")

                if call.parent_call_id:
                    print(f"    Call Stack:")
                    stack_chain = self._build_call_chain(call.call_id)
                    for i, stack_call in enumerate(stack_chain):
                        indent = "      " + ("  " * i)
                        arrow = "└─>" if i == len(stack_chain) - 1 else "├─>"
                        duration_str = f"{stack_call.duration*1000:.2f}ms" if stack_call.duration else "..."
                        print(f"{indent}{arrow} {stack_call.method_name} ({stack_call.call_type}) [{duration_str}]")
                        if stack_call.source_location and i == len(stack_chain) - 1:
                            print(f"{indent}    at {stack_call.source_location}")

        # Show deep stacks
        if self.deep_stacks:
            print(f"\n{'-'*80}")
            print(f"DEEP CALL STACKS (>{self.deep_stack_threshold} levels):")
            print(f"{'-'*80}")
            seen = set()
            for depth, stack in self.deep_stacks[-5:]:  # Last 5 unique
                stack_key = tuple(stack)
                if stack_key not in seen:
                    seen.add(stack_key)
                    print(f"  Depth: {depth}")
                    for cid in stack:
                        if cid in self._call_history:
                            call = next((c for c in self._call_history if c.call_id == cid), None)
                            if call:
                                print(f"    → {call.method_name} ({call.call_type})")
                    print()

        # Show active netrefs
        if self._netrefs:
            print(f"\n{'-'*80}")
            print("ACTIVE NETREFS:")
            print(f"{'-'*80}")
            for netref_id, netref_info in sorted(
                self._netrefs.items(),
                key=lambda x: x[1].num_accesses,
                reverse=True
            )[:10]:  # Top 10 by access count
                print(f"  {netref_info}")

        print(f"{'='*80}\n")

    def reset(self):
        """Reset all telemetry data"""
        with self._lock:
            self.total_calls = 0
            self.total_network_roundtrips = 0
            self.total_netrefs_created = 0
            self.active_netrefs = 0
            self._call_counter = 0
            self._call_stack.clear()
            self._calls.clear()
            self._call_history.clear()
            self._netrefs.clear()
            self._netref_counter = 0
            self.slow_calls.clear()
            self.deep_stacks.clear()


# Global telemetry instance
_global_telemetry = RPyCTelemetry(enabled=False)


def get_telemetry() -> RPyCTelemetry:
    """Get global telemetry instance"""
    return _global_telemetry


def enable_telemetry(**kwargs):
    """Enable global telemetry with optional configuration"""
    global _global_telemetry
    _global_telemetry = RPyCTelemetry(enabled=True, **kwargs)
    return _global_telemetry


def disable_telemetry():
    """Disable global telemetry"""
    _global_telemetry.enabled = False


@contextmanager
def telemetry_context(**kwargs):
    """Context manager for temporary telemetry"""
    old_telemetry = _global_telemetry
    new_telemetry = RPyCTelemetry(enabled=True, **kwargs)

    # Temporarily replace global telemetry
    globals()['_global_telemetry'] = new_telemetry

    try:
        yield new_telemetry
    finally:
        globals()['_global_telemetry'] = old_telemetry
