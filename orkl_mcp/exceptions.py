"""Custom exceptions for the ORKL MCP server."""

from typing import Optional, Dict, Any


class OrklMCPError(Exception):
    """Base exception for all ORKL MCP errors."""
    pass


class OrklAPIError(OrklMCPError):
    """Exception raised when the ORKL API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class OrklConfigError(OrklMCPError):
    """Exception raised when there is a configuration error."""
    pass


class OrklRateLimitError(OrklAPIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class OrklAuthenticationError(OrklAPIError):
    """Exception raised when authentication fails."""
    pass


class OrklValidationError(OrklMCPError):
    """Exception raised when input validation fails."""
    pass


class OrklCacheError(OrklMCPError):
    """Exception raised when cache operations fail."""
    pass
