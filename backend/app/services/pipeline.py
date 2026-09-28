"""Pipeline de traitement d'une vidéo, en service asynchrone.

Étapes : téléchargement audio (yt-dlp) -> découpage en chunks (ffmpeg) ->
transcription (`TRANSCRIPTION_MODEL`) -> résumé structuré (`SUMMARY_MODEL`).
"""

import asyncio
import json
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

from app.config import settings
from app.services import openai_key

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "Tu résumes des transcriptions de vidéos pour un outil de veille personnelle. "
    "Réponds uniquement avec un objet JSON strict, sans texte avant ou après, sans balises markdown."
)

SUMMARY_PROMPT = """Voici la transcription d'une vidéo. Produis un résumé structuré en JSON strict avec ce format exact :

{{
  "titre_suggere": "...",
  "resume_court": "2-3 phrases résumant l'essentiel",
  "points_cles": ["point 1", "point 2", "..."],
  "tags_suggeres": ["tag1", "tag2", "..."],
  "niveau_complexite": "débutant | intermédiaire | avancé"
}}

Transcription :
---
{transcript}
---
"""

# ~1100 mots ≈ 5 minutes à 200-250 mots/minute. C'est un plafond, pas une
# cible : une vidéo qui dit peu doit donner des notes courtes. La contrainte
# est donnée au modèle plutôt qu'appliquée par troncature — couper à
# l'affichage laisserait une puce en plan.
DIGEST_TARGET_WORDS = 1100

DIGEST_SYSTEM_PROMPT = (
    "Tu prends des notes sur des vidéos pour un outil de veille personnelle. "
    "Réponds en français, uniquement avec un objet JSON strict, "
    "sans texte avant ou après, sans balises markdown."
)

DIGEST_PROMPT = """Voici la transcription d'une vidéo{title_hint}.

Prends des notes, comme un collègue compétent qui note pour lui-même et relira dans
six mois. Ce sont des notes, pas une rédaction.

Structure :
- La première section s'intitule exactement « À retenir » : 2 à 3 puces, les idées qui
  justifient d'avoir regardé la vidéo.
- Les sections suivantes reprennent le propos dans l'ordre où il est exposé.
- Le nombre de sections suit ce que la vidéo expose : au moins 3, et autant que
  nécessaire pour tout couvrir. {target_words} mots au maximum — c'est un plafond,
  pas un objectif à atteindre. Une vidéo qui dit peu donne des notes courtes.

Couverture :
- Si la vidéo énumère des éléments — un top, une liste d'outils, une suite d'étapes —
  CHACUN a sa propre section. Aucun ne doit être omis, ni fondu dans un autre. Une
  vidéo qui annonce huit outils donne huit sections, plus « À retenir ».
- Ne t'arrête pas avant d'avoir parcouru la transcription jusqu'au bout : le dernier
  tiers compte autant que le premier.
- À l'inverse, ne découpe pas pour découper : deux sections qui traitent du même sujet
  n'en font qu'une. Regrouper est permis, omettre ne l'est jamais — un élément énuméré
  garde sa section propre même s'il est peu développé.
- Ignore les passages sponsorisés, promotions et appels à l'action : ils sont dans la
  transcription mais ne sont pas le propos.

Règles :
- Les titres de section sont courts et tirés du contenu. Jamais « Introduction »,
  « Conclusion », « Contexte », « Généralités », « Résumé » ni « Présentation de X » :
  un titre doit dire de quoi on parle, pas annoncer qu'on va en parler. Aucun titre ne
  reprend le sujet global de la vidéo — c'est le rôle de « À retenir ».
- Les puces sont télégraphiques. Pas de « L'auteur explique que », pas de
  « Dans cette vidéo », pas de phrase de liaison.
- Reprends systématiquement les éléments concrets cités : chiffres, proportions, ordres
  de grandeur, noms d'outils, commandes, seuils, versions. Une puce qui dit « cela prend
  du temps » là où la vidéo dit « la moitié du temps total » est une puce ratée.
- Le nombre de puces suit la densité de la section : 2 quand elle dit peu, 5 ou 6
  quand elle est dense. Ne calibre pas toutes les sections sur le même gabarit.
- N'ajoute rien qui ne soit pas dans la transcription. Aucune recommandation de ton cru,
  aucun sujet connexe à explorer.

Format JSON strict, avec ce format exact :

{{
  "sections": [
    {{"titre": "À retenir", "puces": ["...", "..."]}},
    {{"titre": "...", "puces": ["...", "..."]}}
  ]
}}

Transcription :
---
{transcript}
---
"""


class PipelineError(RuntimeError):
    pass


@dataclass
class SummaryPayload:
    suggested_title: str | None
    short_summary: str
    key_points: list[str]
    tags: list[str]
    complexity_level: str | None


@dataclass
class AudioDownload:
    title: str
    creator: str | None
    path: Path
    # Description YouTube. Elle n'est pas affichée : elle sert de source aux
    # termes passés au modèle de transcription, qui y trouve l'orthographe
    # exacte des outils cités — voir `extract_keywords`.
    description: str = ""


def openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=openai_key.current_key())


async def _run(*args: str) -> str:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=settings.subprocess_timeout
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        raise PipelineError(
            f"`{args[0]}` n'a pas répondu en {settings.subprocess_timeout}s"
        ) from None

    if process.returncode != 0:
        raise PipelineError(f"Échec de `{args[0]}` : {stderr.decode(errors='replace').strip()}")
    return stdout.decode(errors="replace")


async def download_audio(url: str, workdir: Path) -> AudioDownload:
    workdir.mkdir(parents=True, exist_ok=True)
    output = await _run(
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "5",
        "--no-playlist",
        "--no-progress",
        "--quiet",
        "-o",
        str(workdir / "%(id)s.%(ext)s"),
        "--print",
        # `j` encode la description en JSON : elle est multi-ligne, et la tenir
        # sur une seule ligne est ce qui permet de la lire ici sans changer de
        # format de sortie.
        "after_move:%(title)s\t%(uploader)s\t%(description)j\t%(filepath)s",
        url,
    )
    lines = [line for line in output.splitlines() if "\t" in line]
    if not lines:
        raise PipelineError("yt-dlp n'a produit aucun fichier audio")

    # rsplit depuis la fin : un titre peut contenir une tabulation, pas les
    # trois derniers champs — la description est échappée, le reste ne contient
    # ni tabulation ni saut de ligne.
    title, creator, description, filepath = lines[-1].rsplit("\t", 3)
    return AudioDownload(
        title=title.strip(),
        creator=_clean_creator(creator),
        path=Path(filepath.strip()),
        description=_decode_description(description),
    )


def _decode_description(raw: str) -> str:
    """Description JSON produite par `%(description)j`.

    Une description absente ou illisible ne coûte que des termes en moins
    passés au modèle : elle n'a pas à faire échouer un traitement déjà payé.
    """
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    return value if isinstance(value, str) else ""


def _clean_creator(raw: str) -> str | None:
    """yt-dlp imprime `NA` pour un champ absent : on ne stocke pas ce littéral."""
    creator = raw.strip()
    return creator if creator and creator != "NA" else None


async def fetch_creator(url: str) -> str | None:
    """Nom de la chaîne, sans télécharger l'audio.

    Sert au rattrapage des liens traités avant l'ajout de la colonne : seules
    les métadonnées sont lues, il n'y a ni téléchargement ni transcription à
    repayer.
    """
    output = await _run(
        "yt-dlp",
        "--skip-download",
        "--no-playlist",
        "--no-progress",
        "--quiet",
        "--print",
        "%(uploader)s",
        url,
    )
    lines = [line for line in output.splitlines() if line.strip()]
    return _clean_creator(lines[-1]) if lines else None


async def duration_seconds(path: Path) -> float:
    output = await _run(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    )
    try:
        duration = float(json.loads(output)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        raise PipelineError("Durée de l'audio illisible (ffprobe)") from None

    if duration <= 0:
        raise PipelineError("Durée de l'audio nulle")
    return duration


async def _cut(path: Path, duration: float, n_chunks: int) -> list[Path]:
    chunk_duration = duration / n_chunks
    chunks = []
    for index in range(n_chunks):
        chunk_path = path.with_name(f"{path.stem}_chunk{index}.mp3")
        await _run(
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-ss",
            str(index * chunk_duration),
            "-t",
            str(chunk_duration),
            "-c",
            "copy",
            str(chunk_path),
        )
        chunks.append(chunk_path)
    return chunks


async def split_audio(path: Path, duration: float | None = None) -> list[Path]:
    """Découpe l'audio sous les limites de taille **et** de durée de l'API.

    Le plafond de taille ne suffit pas : 24 Mo représentent près de 40 minutes
    d'audio en qualité 5, bien au-delà de la durée vérifiée intacte en une seule
    requête. Le plafond de durée borne donc les morceaux à ce qui a été mesuré.

    `duration` est la durée déjà sondée par l'appelant, pour éviter un second
    ffprobe. Absente, elle est sondée ici.
    """
    limit = settings.max_chunk_mb * 1_000_000
    size = path.stat().st_size

    if duration is None:
        try:
            duration = await duration_seconds(path)
        except PipelineError:
            # Même contrat qu'en amont : une sonde en échec dégrade le
            # découpage plutôt que d'interrompre un traitement déjà payé. Sans
            # durée on ne sait pas découper ; un fichier sous la limite de
            # taille part tel quel, un fichier au-dessus n'a pas d'issue.
            logger.warning("Durée illisible pour %s, découpage sur la taille seule", path.name)
            if size <= limit:
                return [path]
            raise

    by_duration = math.ceil(duration / settings.max_chunk_seconds)
    if size <= limit and by_duration <= 1:
        return [path]

    # yt-dlp produit du VBR : à durée égale les morceaux n'ont pas la même taille.
    # D'où la marge au calcul, puis la vérification — un chunk trop gros ferait
    # échouer l'appel après avoir déjà payé le téléchargement.
    n_chunks = max(math.ceil(size / (limit * 0.8)), by_duration)

    for _ in range(3):
        chunks = await _cut(path, duration, n_chunks)
        if all(chunk.stat().st_size <= limit for chunk in chunks):
            return chunks
        for chunk in chunks:
            chunk.unlink(missing_ok=True)
        n_chunks *= 2

    raise PipelineError("Impossible de découper l'audio sous la limite de l'API")


# Suites de mots capitalisés ou en CamelCase : c'est sous cette forme que les
# noms d'outils apparaissent dans un titre ou une description YouTube.
_KEYWORD_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:[ -][A-Z][A-Za-z0-9]*)*\b")
_MAX_KEYWORDS = 60
# Les mots capitalisés qui se suivent sur une ligne sont agrégés, ce qui est
# voulu pour « DeepSeek Harness » ou « Comp AI ». Une ligne entièrement
# capitalisée produirait en revanche un seul terme interminable : on l'écarte.
_MAX_KEYWORD_CHARS = 60


def extract_keywords(*sources: str) -> list[str]:
    """Noms propres candidats, tirés du titre et de la description.

    Passés au modèle de transcription, ils lui donnent l'orthographe exacte
    des outils et des noms cités. Les termes ne sont pas connaissables à
    l'avance, mais l'auteur les a déjà écrits dans sa description.

    Les URLs sont retirées d'abord : leurs fragments capitalisés sont du bruit.
    """
    seen: set[str] = set()
    keywords: list[str] = []
    for source in sources:
        for match in _KEYWORD_RE.findall(re.sub(r"https?://\S+", " ", source)):
            term = match.strip()
            if not 3 <= len(term) <= _MAX_KEYWORD_CHARS or term.lower() in seen:
                continue
            seen.add(term.lower())
            keywords.append(term)
            if len(keywords) >= _MAX_KEYWORDS:
                return keywords
    return keywords


async def transcribe(chunks: list[Path], meta: AudioDownload | None = None) -> str:
    client = openai_client()
    is_whisper = settings.transcription_model.startswith("whisper")

    # Whisper (`TRANSCRIPTION_MODEL=whisper-1`) n'accepte ni `keywords` ni
    # `languages`, et rend `text` brut.
    options: dict = {"response_format": "text"} if is_whisper else {
        "response_format": "json",
        "languages": list(settings.transcription_languages),
    }
    if not is_whisper and meta is not None:
        keywords = extract_keywords(meta.title, meta.description)
        if keywords:
            options["keywords"] = keywords

    parts = []
    for chunk in chunks:
        audio = await asyncio.to_thread(chunk.read_bytes)
        transcript = await client.audio.transcriptions.create(
            model=settings.transcription_model,
            file=(chunk.name, audio),
            **options,
        )
        if not is_whisper:
            _warn_if_token_capped(chunk, transcript)
        parts.append(str(transcript) if is_whisper else transcript.text)
    return "\n".join(parts)


# Plafond de sortie des modèles facturés aux tokens (`gpt-4o-transcribe`), qui
# s'y arrêtent net, sans erreur, au-delà de ~9 min d'audio : c'est le signal
# direct de la troncature, bien plus sûr que le débit de mots, qui ne la
# distingue pas d'un orateur lent. `gpt-transcribe`, facturé à la durée, ne
# rapporte pas ce champ et n'est pas concerné.
_OUTPUT_TOKEN_CAP = 2000


def _warn_if_token_capped(chunk: Path, transcript: object) -> None:
    usage = getattr(transcript, "usage", None)
    produced = getattr(usage, "output_tokens", None)
    if isinstance(produced, int) and produced >= _OUTPUT_TOKEN_CAP:
        logger.warning(
            "Transcription de %s arrêtée au plafond de %d tokens (%d produits) : "
            "le texte est tronqué. Baisser MAX_CHUNK_SECONDS ou repasser sur un "
            "modèle facturé à la durée.",
            chunk.name,
            _OUTPUT_TOKEN_CAP,
            produced,
        )


# Plancher de débit, en mots par minute. Second filet, complémentaire de
# `_warn_if_token_capped` : il ne dépend d'aucun champ `usage` et couvre donc
# les pertes d'autre origine — un chunk vide, un téléchargement partiel.
# Volontairement bas : un débit de parole réel tourne autour de 150, mais une
# vidéo avec démonstrations et silences descend légitimement bien plus bas.
# Il ne prétend donc pas attraper une amputation partielle — c'est le rôle du
# contrôle de plafond de tokens, qui, lui, est exact.
MIN_WORDS_PER_MINUTE = 40.0


def looks_truncated(transcript: str, audio_seconds: float | None) -> bool:
    if not audio_seconds or audio_seconds <= 0:
        return False
    return len(transcript.split()) / (audio_seconds / 60) < MIN_WORDS_PER_MINUTE


def _str_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


async def summarize(transcript: str) -> SummaryPayload:
    client = openai_client()
    response = await client.chat.completions.create(
        model=settings.summary_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            # Une transcription de plusieurs heures dépasserait la fenêtre du modèle.
            {
                "role": "user",
                "content": SUMMARY_PROMPT.format(
                    transcript=transcript[: settings.max_transcript_chars]
                ),
            },
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise PipelineError("Le modèle n'a renvoyé aucun résumé")

    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        raise PipelineError("Résumé illisible : JSON invalide") from None

    return SummaryPayload(
        suggested_title=raw.get("titre_suggere") or None,
        short_summary=str(raw.get("resume_court") or ""),
        key_points=_str_list(raw.get("points_cles")),
        tags=_str_list(raw.get("tags_suggeres")),
        complexity_level=raw.get("niveau_complexite") or None,
    )


def _sections(raw: object) -> list[dict]:
    """Ne garde que les sections réellement exploitables : un titre et des puces."""
    if not isinstance(raw, list):
        return []

    sections = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        titre = str(item.get("titre") or "").strip()
        puces = [puce.strip() for puce in _str_list(item.get("puces")) if puce.strip()]
        if titre and puces:
            sections.append({"titre": titre, "puces": puces})
    return sections


async def generate_digest(transcript: str, title: str | None = None) -> list[dict]:
    """Prend les notes d'une transcription déjà en base."""
    if not transcript.strip():
        raise PipelineError("Transcription vide : digest impossible")

    client = openai_client()
    response = await client.chat.completions.create(
        model=settings.summary_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": DIGEST_PROMPT.format(
                    title_hint=f' intitulée « {title} »' if title else "",
                    target_words=DIGEST_TARGET_WORDS,
                    transcript=transcript[: settings.max_transcript_chars],
                ),
            },
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise PipelineError("Le modèle n'a renvoyé aucun digest")

    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        raise PipelineError("Digest illisible : JSON invalide") from None

    sections = _sections(raw.get("sections"))
    if not sections:
        raise PipelineError("Le modèle n'a renvoyé aucune section exploitable")
    return sections
