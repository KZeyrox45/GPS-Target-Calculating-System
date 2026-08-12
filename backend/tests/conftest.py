"""
conftest.py - Session-scoped fixtures for test performance
==========================================================
Pre-loads expensive dataset caches once per session so individual
tests don't re-parse 18,670 Geolife files.
"""
import pytest


@pytest.fixture(scope="session")
def geolife_data():
    """Pre-load Geolife dataset once. Tests request this explicitly."""
    from app.simulation.data_loaders import GeolifeWalkLoader
    return GeolifeWalkLoader.load()


@pytest.fixture(scope="session")
def amit_data():
    """Pre-load AMIT dataset once. Tests request this explicitly."""
    from app.simulation.data_loaders import AMITMotorcycleLoader
    return AMITMotorcycleLoader.load()
