"""Domain errors mapped to HTTP at the API edge."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(detail, status_code=404)


class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class ValidationAppError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=422)


class UpstreamError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=502)


class NotConfiguredError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=501)
