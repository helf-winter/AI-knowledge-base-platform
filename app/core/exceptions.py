from __future__ import annotations


class AppError(Exception):
    """Base application error with stable error code."""

    def __init__(self, message: str, code: str = "APP_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationAppError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class NotFoundAppError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="NOT_FOUND")


class PermissionAppError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="PERMISSION_DENIED")
