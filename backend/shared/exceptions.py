# backend/shared/exceptions.py
"""Custom exception classes for ARGUS."""


class ARGUSException(Exception):
    """Base exception for all ARGUS errors."""
    
    def __init__(self, detail: str, error_code: str = "UNKNOWN", status_code: int = 500):
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.detail)


class DatabaseError(ARGUSException):
    """Database operation failed."""
    def __init__(self, detail: str):
        super().__init__(detail, "DB_ERROR", 500)


class ValidationError(ARGUSException):
    """Input validation failed."""
    def __init__(self, detail: str):
        super().__init__(detail, "VALIDATION_ERROR", 400)


class NotFoundError(ARGUSException):
    """Resource not found."""
    def __init__(self, detail: str):
        super().__init__(detail, "NOT_FOUND", 404)


class AuthenticationError(ARGUSException):
    """Authentication failed."""
    def __init__(self, detail: str):
        super().__init__(detail, "AUTH_ERROR", 401)


class PermissionError(ARGUSException):
    """Permission denied."""
    def __init__(self, detail: str):
        super().__init__(detail, "PERMISSION_ERROR", 403)


class ExternalServiceError(ARGUSException):
    """External service (VT, etc.) failed."""
    def __init__(self, detail: str):
        super().__init__(detail, "EXTERNAL_SERVICE_ERROR", 503)