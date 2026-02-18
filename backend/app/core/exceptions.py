from app.schemas.error import ErrorDetails


class AppException(Exception):  # noqa: N818
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: ErrorDetails = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class BadRequestException(AppException):
    def __init__(
        self,
        message: str = "Bad request",
        details: ErrorDetails = None,
    ) -> None:
        super().__init__(400, "BAD_REQUEST", message, details)


class UnauthorizedException(AppException):
    def __init__(
        self,
        message: str = "Unauthorized",
        details: ErrorDetails = None,
    ) -> None:
        super().__init__(401, "UNAUTHORIZED", message, details)


class ForbiddenException(AppException):
    def __init__(
        self,
        message: str = "Forbidden",
        details: ErrorDetails = None,
    ) -> None:
        super().__init__(403, "FORBIDDEN", message, details)


class NotFoundException(AppException):
    def __init__(
        self,
        message: str = "Not found",
        details: ErrorDetails = None,
    ) -> None:
        super().__init__(404, "NOT_FOUND", message, details)


class ConflictException(AppException):
    def __init__(
        self,
        message: str = "Conflict",
        details: ErrorDetails = None,
    ) -> None:
        super().__init__(409, "CONFLICT", message, details)


class InternalServerException(AppException):
    def __init__(
        self,
        message: str = "Internal server error",
        details: ErrorDetails = None,
    ) -> None:
        super().__init__(500, "INTERNAL_ERROR", message, details)
