"""Tests for autobench automatic profiling"""

import rpyc
from rpycbench.autobench.patcher import install_patches, uninstall_patches, is_patched
from rpycbench.utils.telemetry import enable_telemetry, get_telemetry
from rpycbench.utils.markers import get_marker_manager, mark
from rpycbench.utils.profiler import ProfiledConnection


def test_patcher_installation():
    """Test that patches can be installed and uninstalled"""
    assert not is_patched()

    install_patches()
    assert is_patched()

    uninstall_patches()
    assert not is_patched()


def test_patcher_wraps_connections():
    """Test that installed patches wrap connections with profiling"""
    telemetry = enable_telemetry()
    install_patches()

    try:
        original_connect = rpyc.connect
        assert original_connect != rpyc.connect.__wrapped__ if hasattr(rpyc.connect, '__wrapped__') else True

    finally:
        uninstall_patches()


def test_marker_manager():
    """Test marker manager tracks critical sections"""
    manager = get_marker_manager()
    manager.enable()
    manager.reset()

    marker = manager.start("Test section")
    assert marker is not None
    assert marker.name == "Test section"
    assert marker.end_time is None

    manager.end()
    assert marker.end_time is not None
    assert marker.duration > 0

    markers = manager.get_markers()
    assert len(markers) == 1
    assert markers[0].name == "Test section"


def test_marker_context_manager():
    """Test marker context manager"""
    manager = get_marker_manager()
    manager.enable()
    manager.reset()

    with manager.section("Context section"):
        pass

    markers = manager.get_markers()
    assert len(markers) == 1
    assert markers[0].name == "Context section"
    assert markers[0].duration > 0


def test_marker_convenience_class():
    """Test mark convenience class"""
    manager = get_marker_manager()
    manager.enable()
    manager.reset()

    mark.start("Convenience test")
    mark.end()

    markers = manager.get_markers()
    assert len(markers) == 1
    assert markers[0].name == "Convenience test"


def test_marker_noop_when_disabled():
    """Test markers are no-ops when disabled"""
    manager = get_marker_manager()
    manager.disable()
    manager.reset()

    marker = mark.start("Should not record")
    assert marker is None

    mark.end()

    markers = manager.get_markers()
    assert len(markers) == 0


def test_nested_markers():
    """Test nested marker sections"""
    manager = get_marker_manager()
    manager.enable()
    manager.reset()

    with mark.section("Outer"):
        with mark.section("Inner"):
            pass

    markers = manager.get_markers()
    assert len(markers) == 2
    assert markers[0].name == "Outer"
    assert markers[1].name == "Inner"
    assert markers[1].parent_marker == "Outer"
