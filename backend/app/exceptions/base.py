from typing import Optional


class EzRewardsException(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: Optional[list] = None,
    ):
        self.error_code  = error_code
        self.message     = message
        self.status_code = status_code
        self.details     = details
        super().__init__(message)


class TokenExpiredException(EzRewardsException):
    def __init__(self):
        super().__init__("TOKEN_EXPIRED", "Session expired. Please log in again.", 401)


class InsufficientRoleException(EzRewardsException):
    def __init__(self, required: str):
        super().__init__("INSUFFICIENT_ROLE", f"Access denied. {required} role required.", 403)


class WorkspaceNotFoundException(EzRewardsException):
    def __init__(self):
        super().__init__("WORKSPACE_NOT_FOUND", "Workspace not found.", 404)


class DatabaseTimeoutException(EzRewardsException):
    def __init__(self):
        super().__init__("DB_QUERY_TIMEOUT", "Request timed out. Please try again.", 504)