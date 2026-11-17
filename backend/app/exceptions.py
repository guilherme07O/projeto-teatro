class DomainError(Exception):
    """Base para erros de domínio."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass