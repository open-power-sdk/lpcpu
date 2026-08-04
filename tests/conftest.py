"""
Pytest configuration for LPCPU tests
"""

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )

# Made with Bob
