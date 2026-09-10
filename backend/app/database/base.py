from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Standard constraint naming convention recommended by SQLAlchemy & Alembic:
# Ensures deterministic constraint names across Postgres migrations.
POSTGRES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all application models."""

    metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)

    def __repr__(self) -> str:
        """Informative string representation showing model name and primary key / identifier."""
        cols = []
        for col in self.__table__.columns:
            if col.primary_key or col.name in ("ticker", "email", "title", "role"):
                cols.append(f"{col.name}={getattr(self, col.name)!r}")
        return f"<{self.__class__.__name__}({', '.join(cols)})>"
