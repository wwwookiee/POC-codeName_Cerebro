import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, String, Table, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base


class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"


link_collections = Table(
    "link_collections",
    Base.metadata,
    Column("link_id", ForeignKey("links.id", ondelete="CASCADE"), primary_key=True),
    Column("collection_id", ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
)


class Link(Base):
    __tablename__ = "links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    source: Mapped[str] = mapped_column(String(32), default="youtube")
    title: Mapped[str | None] = mapped_column(String(512), default=None)
    creator: Mapped[str | None] = mapped_column(String(255), default=None)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.pending,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    # Début du traitement en cours. `created_at` ne peut pas en tenir lieu : sur
    # une relance il date de l'ajout du lien, et le compteur afficherait des
    # jours. Remis à l'heure courante à chaque passage en `processing`.
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    # Durée du dernier traitement réussi, et durée de l'audio : ensemble, elles
    # donnent l'historique à partir duquel les traitements suivants sont estimés.
    processing_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    audio_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    summary: Mapped["Summary | None"] = relationship(
        back_populates="link", cascade="all, delete-orphan", lazy="selectin"
    )
    collections: Mapped[list["Collection"]] = relationship(
        secondary=link_collections, lazy="selectin"
    )


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("links.id", ondelete="CASCADE"), unique=True
    )
    suggested_title: Mapped[str | None] = mapped_column(String(512), default=None)
    short_summary: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list[str]] = mapped_column(JSONB, default=list)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    complexity_level: Mapped[str | None] = mapped_column(String(32), default=None)
    # Notes structurées (5 min de lecture au maximum, moins si la vidéo dit peu),
    # générées à la demande au premier affichage, puis conservées :
    # [{"titre": ..., "puces": [...]}, ...].
    digest_notes: Mapped[list[dict] | None] = mapped_column(JSONB, deferred=True, default=None)
    transcript: Mapped[str] = mapped_column(Text, deferred=True, default="")
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.embedding_dimensions), deferred=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    link: Mapped[Link] = relationship(back_populates="summary")


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
