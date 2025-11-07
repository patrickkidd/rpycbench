"""Visualization utilities for RPyC telemetry"""

from typing import List, Dict, Any, Optional
from rpycbench.utils.telemetry import RPyCCallInfo, RPyCTelemetry
import time


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 0.001:
        return f"{seconds*1000000:.0f}µs"
    elif seconds < 1:
        return f"{seconds*1000:.2f}ms"
    else:
        return f"{seconds:.2f}s"


def format_call_tree(
    telemetry: RPyCTelemetry,
    max_depth: Optional[int] = None,
    min_duration: float = 0.0,
    show_netrefs: bool = True,
) -> str:
    """
    Format call history as a tree

    Args:
        telemetry: Telemetry instance
        max_depth: Maximum depth to display
        min_duration: Minimum call duration to display
        show_netrefs: Whether to show netref information
    """
    lines = []
    lines.append("=" * 80)
    lines.append("RPYC CALL TREE")
    lines.append("=" * 80)

    # Build parent-child relationships
    children_map: Dict[Optional[int], List[RPyCCallInfo]] = {}

    for call in telemetry._call_history:
        if call.duration is None or call.duration < min_duration:
            continue

        parent_id = call.parent_call_id
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(call)

    def print_tree(parent_id: Optional[int], depth: int, prefix: str = ""):
        """Recursively print tree"""
        if max_depth and depth >= max_depth:
            return

        if parent_id not in children_map:
            return

        calls = children_map[parent_id]

        for i, call in enumerate(calls):
            is_last = i == len(calls) - 1
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            # Format call info
            duration_str = format_duration(call.duration) if call.duration else "..."
            call_type_str = call.call_type.upper()

            netref_str = ""
            if show_netrefs and call.is_netref:
                netref_str = f" [NetRef #{call.netref_id}]"
                if call.result_is_netref:
                    netref_str += f" → [NetRef #{call.result_netref_id}]"

            exception_str = ""
            if call.exception:
                exception_str = f" ⚠ {call.exception[:30]}"

            line = f"{prefix}{connector}{call.method_name} ({call_type_str}){netref_str} [{duration_str}]{exception_str}"
            lines.append(line)

            # Recurse for children
            print_tree(call.call_id, depth + 1, prefix + extension)

    # Start from root calls (no parent)
    print_tree(None, 0)

    lines.append("=" * 80)
    return "\n".join(lines)


def format_timeline(
    telemetry: RPyCTelemetry,
    width: int = 80,
    min_duration: float = 0.0,
) -> str:
    """
    Format call history as a timeline

    Args:
        telemetry: Telemetry instance
        width: Width of timeline in characters
        min_duration: Minimum call duration to display
    """
    lines = []
    lines.append("=" * 80)
    lines.append("RPYC CALL TIMELINE")
    lines.append("=" * 80)

    history = [c for c in telemetry._call_history if c.duration and c.duration >= min_duration]

    if not history:
        lines.append("(no calls recorded)")
        lines.append("=" * 80)
        return "\n".join(lines)

    # Find time range
    start_time = min(c.timestamp for c in history)
    end_time = max(c.timestamp + (c.duration or 0) for c in history)
    total_time = end_time - start_time

    if total_time == 0:
        total_time = 0.001

    # Draw timeline
    for call in history:
        # Calculate position and width
        rel_start = call.timestamp - start_time
        rel_pos = int((rel_start / total_time) * width)

        bar_width = max(1, int(((call.duration or 0) / total_time) * width))

        # Build timeline bar
        timeline = [' '] * width
        for i in range(rel_pos, min(rel_pos + bar_width, width)):
            timeline[i] = '█'

        timeline_str = ''.join(timeline)

        # Format call info
        duration_str = format_duration(call.duration)
        depth_str = f"{'  ' * call.stack_depth}"

        line = f"{timeline_str} {depth_str}{call.method_name} ({duration_str})"
        lines.append(line)

    lines.append("=" * 80)
    lines.append(f"Total time: {format_duration(total_time)}")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_netref_report(telemetry: RPyCTelemetry) -> str:
    """Format netref usage report"""
    lines = []
    lines.append("=" * 80)
    lines.append("NETREF REPORT")
    lines.append("=" * 80)

    if not telemetry._netrefs:
        lines.append("(no active netrefs)")
        lines.append("=" * 80)
        return "\n".join(lines)

    # Sort by activity
    sorted_netrefs = sorted(
        telemetry._netrefs.items(),
        key=lambda x: x[1].num_accesses,
        reverse=True
    )

    lines.append(f"{'ID':<8} {'Class':<25} {'Age':<10} {'Calls':<8} {'Attrs':<8} {'Total':<8}")
    lines.append("-" * 80)

    for netref_id, netref_info in sorted_netrefs:
        age = time.time() - netref_info.created_at
        age_str = format_duration(age)

        line = (
            f"{netref_id:<8} "
            f"{netref_info.class_name:<25} "
            f"{age_str:<10} "
            f"{netref_info.num_method_calls:<8} "
            f"{netref_info.num_attr_accesses:<8} "
            f"{netref_info.num_accesses:<8}"
        )
        lines.append(line)

    lines.append("=" * 80)
    lines.append(f"Total NetRefs: {len(telemetry._netrefs)}")
    lines.append(f"Total Created: {telemetry.total_netrefs_created}")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_slow_calls_report(
    telemetry: RPyCTelemetry,
    top_n: int = 20,
) -> str:
    """Format slow calls report"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"SLOW CALLS REPORT (threshold: {format_duration(telemetry.slow_call_threshold)})")
    lines.append("=" * 80)

    if not telemetry.slow_calls:
        lines.append("(no slow calls detected)")
        lines.append("=" * 80)
        return "\n".join(lines)

    # Sort by duration
    sorted_calls = sorted(
        telemetry.slow_calls,
        key=lambda c: c.duration or 0,
        reverse=True
    )[:top_n]

    lines.append(f"{'Method':<40} {'Duration':<12} {'Type':<10} {'Depth':<8}")
    lines.append("-" * 80)

    for call in sorted_calls:
        duration_str = format_duration(call.duration) if call.duration else "N/A"
        line = (
            f"{call.method_name[:40]:<40} "
            f"{duration_str:<12} "
            f"{call.call_type:<10} "
            f"{call.stack_depth:<8}"
        )
        lines.append(line)

    lines.append("=" * 80)
    lines.append(f"Total Slow Calls: {len(telemetry.slow_calls)} (showing top {len(sorted_calls)})")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_full_report(
    telemetry: RPyCTelemetry,
    include_tree: bool = True,
    include_timeline: bool = False,
    include_netrefs: bool = True,
    include_slow_calls: bool = True,
) -> str:
    """Generate a full telemetry report"""
    sections = []

    # Statistics
    stats = telemetry.get_statistics()
    lines = []
    lines.append("=" * 80)
    lines.append("RPYC TELEMETRY REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append("SUMMARY:")
    lines.append(f"  Total Calls:              {stats['total_calls']}")
    lines.append(f"  Network Round Trips:      {stats['total_network_roundtrips']}")
    lines.append(f"  NetRefs Created:          {stats['total_netrefs_created']}")
    lines.append(f"  Active NetRefs:           {stats['active_netrefs']}")
    lines.append(f"  Max Stack Depth:          {stats['max_stack_depth']}")
    lines.append(f"  Avg Call Duration:        {format_duration(stats['avg_call_duration'])}")
    lines.append(f"  Slow Calls:               {stats['num_slow_calls']}")
    lines.append("")
    sections.append("\n".join(lines))

    # Call tree
    if include_tree and telemetry._call_history:
        sections.append(format_call_tree(telemetry))
        sections.append("")

    # Timeline
    if include_timeline and telemetry._call_history:
        sections.append(format_timeline(telemetry))
        sections.append("")

    # NetRefs
    if include_netrefs and telemetry._netrefs:
        sections.append(format_netref_report(telemetry))
        sections.append("")

    # Slow calls
    if include_slow_calls and telemetry.slow_calls:
        sections.append(format_slow_calls_report(telemetry))
        sections.append("")

    return "\n".join(sections)


def print_live_stack(telemetry: RPyCTelemetry, threshold_ms: float = 100):
    """Print live call stack if current call exceeds threshold"""
    stack = telemetry.get_call_stack()

    if not stack:
        return

    # Check if we should print
    oldest_call = stack[0]
    elapsed = time.time() - oldest_call.timestamp

    if elapsed * 1000 >= threshold_ms:
        telemetry.print_call_stack(
            title=f"SLOW CALL DETECTED ({format_duration(elapsed)} elapsed)"
        )
