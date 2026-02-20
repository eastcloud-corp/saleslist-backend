from typing import Optional


class PowerplexyError(Exception):
    """Base class for PowerPlexy related errors."""


class PowerplexyConfigurationError(PowerplexyError):
    """Raised when the API is not properly configured."""


class PowerplexyRateLimitError(PowerplexyError):
    """Raised when the upstream API indicates a rate limit issue."""


class PowerplexyResponseError(PowerplexyError):
    """Raised when the upstream API returns an unexpected response."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
