"""Configuration management for the ORKL MCP server."""

import json
import os
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrklConfig:
    """Configuration for the ORKL API client."""

    api_base_url: str = "https://orkl.eu/api/v1"
    request_timeout: int = 30
    cache_ttl: int = 300
    use_cache: bool = True
    rate_limit_requests: int = 90
    rate_limit_period: int = 30

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrklConfig):
            return NotImplemented
        return (
                self.api_base_url == other.api_base_url
                and self.request_timeout == other.request_timeout
                and self.cache_ttl == other.cache_ttl
                and self.use_cache == other.use_cache
                and self.rate_limit_requests == other.rate_limit_requests
                and self.rate_limit_period == other.rate_limit_period
        )


def load_config() -> OrklConfig:
    """Load configuration from file and environment variables."""
    config = OrklConfig()

    # Load from config file if specified
    config_file = os.getenv("ORKL_CONFIG_FILE")
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file) as f:
                config_dict = json.load(f)

            if "api_base_url" in config_dict:
                config.api_base_url = str(config_dict["api_base_url"])
            if "request_timeout" in config_dict:
                config.request_timeout = int(config_dict["request_timeout"])
            if "cache" in config_dict:
                cache_config = config_dict["cache"]
                if "ttl" in cache_config:
                    config.cache_ttl = int(cache_config["ttl"])
                if "enable" in cache_config:
                    config.use_cache = bool(cache_config["enable"])
            if "rate_limit" in config_dict:
                rate_limit_config = config_dict["rate_limit"]
                if "requests_per_window" in rate_limit_config:
                    config.rate_limit_requests = int(rate_limit_config["requests_per_window"])
                if "window_seconds" in rate_limit_config:
                    config.rate_limit_period = int(rate_limit_config["window_seconds"])
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config file: {e}")

    # Override with environment variables if set
    if os.getenv("ORKL_API_BASE_URL"):
        config.api_base_url = os.getenv("ORKL_API_BASE_URL", config.api_base_url)
    if os.getenv("ORKL_REQUEST_TIMEOUT"):
        config.request_timeout = int(os.getenv("ORKL_REQUEST_TIMEOUT", str(config.request_timeout)))
    if os.getenv("ORKL_CACHE_TTL"):
        config.cache_ttl = int(os.getenv("ORKL_CACHE_TTL", str(config.cache_ttl)))
    if os.getenv("ORKL_USE_CACHE"):
        config.use_cache = os.getenv("ORKL_USE_CACHE", str(config.use_cache)).lower() == "true"
    if os.getenv("ORKL_RATE_LIMIT_REQUESTS"):
        config.rate_limit_requests = int(os.getenv("ORKL_RATE_LIMIT_REQUESTS", str(config.rate_limit_requests)))
    if os.getenv("ORKL_RATE_LIMIT_PERIOD"):
        config.rate_limit_period = int(os.getenv("ORKL_RATE_LIMIT_PERIOD", str(config.rate_limit_period)))

    return config
