"""Domain-level exceptions for job processing."""


class RetryableError(Exception):
    """
    Raised when a job encounters a transient failure that should be retried.
    
    Examples: temporary network issues, database connection timeouts.
    """
    pass


class PermanentError(Exception):
    """
    Raised when a job encounters a permanent failure that should not be retried.
    
    Examples: malformed input, validation failure, logic error.
    """
    pass