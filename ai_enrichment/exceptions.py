class PowerplexyError(Exception):
    """Base class for PowerPlexy related errors."""


class PowerplexyConfigurationError(PowerplexyError):
    """Raised when the API is not properly configured."""


class PowerplexyRateLimitError(PowerplexyError):
    """Raised when the upstream API indicates a rate limit issue."""


class PowerplexyResponseError(PowerplexyError):
    """Raised when the upstream API returns an unexpected response."""
