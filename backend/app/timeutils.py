from datetime import datetime, timezone


def utcnow() -> datetime:
    """Horário atual em UTC, sem tzinfo.

    As colunas são ``DateTime`` (sem timezone) para manter compatibilidade com MySQL
    e SQLite. A conversão para UTC "com Z" acontece na serialização da API
    (ver ``schemas.py``), para que o frontend exiba o horário correto.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_utc(value: datetime | None) -> datetime | None:
    """Marca um datetime naive (assumidamente UTC) como UTC, para serialização correta."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
