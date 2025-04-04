"""Tests for the configuration module."""

import os
import tempfile
from unittest import mock

from orkl_mcp.config import load_config


def test_default_config():
    """Test that default configuration is loaded correctly."""
    config = load_config()
    assert config.api_base_url == "https://orkl.eu/api/v1"
    assert config.request_timeout == 30
    assert config.cache_ttl == 300
    assert config.use_cache is True
    assert config.rate_limit_requests == 90
    assert config.rate_limit_period == 30


def test_config_from_file():
    """Test loading configuration from a file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(
            """
            {
                "api_base_url": "https://orkl.eu/api/v1",
                "request_timeout": 60,
                "cache": {
                    "ttl": 600,
                    "enable": false
                },
                "rate_limit": {
                    "requests_per_window": 100,
                    "window_seconds": 60
                }
            }
            """
        )
        config_path = f.name

    try:
        with mock.patch.dict(os.environ, {"ORKL_CONFIG_FILE": config_path}):
            config = load_config()
            assert config.api_base_url == "https://orkl.eu/api/v1"
            assert config.request_timeout == 60
            assert config.cache_ttl == 600
            assert config.use_cache is False
            assert config.rate_limit_requests == 100
            assert config.rate_limit_period == 60
    finally:
        os.unlink(config_path)


def test_config_from_env():
    """Test loading configuration from environment variables."""
    with mock.patch.dict(
        os.environ,
        {
            "ORKL_API_BASE_URL": "https://env.example.com/api",
            "ORKL_REQUEST_TIMEOUT": "45",
            "ORKL_CACHE_TTL": "450",
            "ORKL_USE_CACHE": "0",
            "ORKL_RATE_LIMIT_REQUESTS": "80",
            "ORKL_RATE_LIMIT_PERIOD": "45",
        },
    ):
        config = load_config()
        assert config.api_base_url == "https://env.example.com/api"
        assert config.request_timeout == 45
        assert config.cache_ttl == 450
        assert config.use_cache is False
        assert config.rate_limit_requests == 80
        assert config.rate_limit_period == 45


def test_invalid_config_file():
    """Test handling of invalid configuration file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("invalid json")
        config_path = f.name

    try:
        with mock.patch.dict(os.environ, {"ORKL_CONFIG_FILE": config_path}):
            config = load_config()
            # Should fall back to defaults
            assert config.api_base_url == "https://orkl.eu/api/v1"
    finally:
        os.unlink(config_path)


def test_missing_config_file():
    """Test handling of missing configuration file."""
    with mock.patch.dict(os.environ, {"ORKL_CONFIG_FILE": "nonexistent.json"}):
        config = load_config()
        # Should fall back to defaults
        assert config.api_base_url == "https://orkl.eu/api/v1"
