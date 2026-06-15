class ErpqaError(Exception):
    """Base class for controlled CLI errors."""

    exit_code = 1


class UsageError(ErpqaError):
    exit_code = 2


class WriteOutsideQaContextError(ErpqaError):
    exit_code = 3


class ValidationFailed(ErpqaError):
    exit_code = 1
