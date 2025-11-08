"""Pytest configuration and fixtures"""

import pytest
import time
import socket
from pathlib import Path


def find_free_port():
    """Find a free port for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture
def rpyc_port():
    """Provide a free port for RPyC server"""
    return find_free_port()


@pytest.fixture
def http_port():
    """Provide a free port for HTTP server"""
    return find_free_port()


@pytest.fixture
def test_data_small():
    """Small test data (1KB)"""
    return b'x' * 1024


@pytest.fixture
def test_data_medium():
    """Medium test data (10KB)"""
    return b'x' * 10240


@pytest.fixture
def test_data_large():
    """Large test data (100KB)"""
    return b'x' * 102400


@pytest.fixture
def integration_host(request):
    """Provide SSH host for integration tests"""
    return request.config.getoption("--integration-host")


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests (requires SSH access)"
    )
    parser.addoption(
        "--integration-host",
        action="store",
        default="localhost",
        help="SSH host for integration tests (default: localhost)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --integration flag or explicitly selected"""
    if config.getoption("--integration"):
        return

    # Check if integration tests were explicitly selected by looking at collected items
    # If ALL items are integration tests, assume they were explicitly selected
    integration_items = [item for item in items if "integration" in item.keywords]

    if integration_items and len(integration_items) == len(items):
        # All collected items are integration tests = explicitly selected
        return

    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in integration_items:
        item.add_marker(skip_integration)
