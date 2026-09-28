from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ProcessingStatus
from app.services.youtube import canonical_url, extract_video_id


class LinkCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def must_be_youtube(cls, value: str) -> str:
        video_id = extract_video_id(value.strip())
        if video_id is None:
            raise ValueError("URL YouTube invalide")
        return canonical_url(video_id)


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None


class CollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None


class CollectionRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class CollectionRead(CollectionRef):
    description: str | None
    created_at: datetime
    link_count: int


class LinkCollectionsUpdate(BaseModel):
    collection_ids: list[UUID]


class SummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    suggested_title: str | None
    short_summary: str
    key_points: list[str]
    tags: list[str]
    complexity_level: str | None


class DigestSection(BaseModel):
    titre: str
    puces: list[str]


class SummaryDetail(SummaryRead):
    transcript: str
    # `null` tant que le digest n'a pas été demandé pour ce lien.
    digest_notes: list[DigestSection] | None


class DigestRead(BaseModel):
    digest_notes: list[DigestSection]


class LinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    source: str
    title: str | None
    creator: str | None
    status: ProcessingStatus
    error_message: str | None
    created_at: datetime
    processing_started_at: datetime | None
    # Renseignée par le routeur pour un lien en cours, à partir de l'historique
    # des traitements : elle ne se lit pas sur le lien lui-même.
    estimated_seconds: float | None = None
    summary: SummaryRead | None
    collections: list[CollectionRef]


class LinkDetail(LinkRead):
    summary: SummaryDetail | None


class SearchResult(BaseModel):
    link: LinkRead
    score: float


class OpenAIKeyUpdate(BaseModel):
    api_key: str = Field(min_length=20)

    @field_validator("api_key", mode="before")
    @classmethod
    def strip(cls, value: str) -> str:
        # Un copier-coller embarque souvent un espace ou un saut de ligne.
        return value.strip() if isinstance(value, str) else value


class OpenAIKeyStatus(BaseModel):
    configured: bool
    source: Literal["interface", "env"] | None
    hint: str | None
