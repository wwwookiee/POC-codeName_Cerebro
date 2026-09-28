from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text, update

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.migrations_runner import upgrade_to_head
from app.models import Link, ProcessingStatus
from app.routers import collections, links, openai_settings, search
from app.services.openai_key import MissingOpenAIKey


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # pgvector doit exister avant la baseline, qui crée une colonne `vector`.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(upgrade_to_head)

    # Les traitements tournent en tâche de fond : un redémarrage les perd silencieusement.
    # `pending` compte aussi — la tâche ne démarre qu'après l'envoi de la réponse HTTP,
    # et seul le statut `error` autorise une relance.
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Link)
            .where(Link.status.in_((ProcessingStatus.pending, ProcessingStatus.processing)))
            .values(
                status=ProcessingStatus.error,
                error_message="Traitement interrompu par un redémarrage du serveur",
            )
        )
        await session.commit()

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Cerebro — API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(links.router)
app.include_router(collections.router)
app.include_router(search.router)
app.include_router(openai_settings.router)


@app.exception_handler(MissingOpenAIKey)
async def missing_openai_key(_: Request, exc: MissingOpenAIKey) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
