# Cerebro

[![CI](https://github.com/wwwookiee/POC-codeName_Cerebro/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/wwwookiee/POC-codeName_Cerebro/actions/workflows/ci.yml)

<p align="center">
  <img src="docs/demo/cerebro-demo.gif" alt="Cerebro : flux, notes, collections et clé API" width="800">
</p>

**[English](#english)** · **[Français](#français)**

## English

A personal watch tool: paste the URL of a YouTube video, and Cerebro transcribes it, turns it
into a structured summary and reading notes, then lets you find any video again by asking a
question in plain language.

**Cerebro runs locally, on your machine.** There is no deployment, no account and no remote
server: a Postgres database, an API and a web interface start in Docker, and only the calls to
the OpenAI API (transcription, summary, search) leave your machine. It is a single-user tool,
meant to be started whenever you need it.

The interface is in French; the labels quoted below are given as they appear on screen.

### Contents

- [Screenshots](#screenshots)
- [Quick start](#quick-start)
- [The OpenAI key](#the-openai-key)
- [Usage](#usage)
- [Stop, restart, start over](#stop-restart-start-over)
- [Troubleshooting](#troubleshooting)
- [Configuration](#configuration)
- [Under the hood](#under-the-hood)
- [Development](#development)
- [Roadmap — SaaS version](#roadmap--saas-version)

### Screenshots

The images and the [video version (MP4, 18 s)](docs/demo/cerebro-demo.mp4) use sample data: the
channels and videos shown are made up.

| | |
| --- | --- |
| <a href="docs/demo/screens/01-flux.png"><img src="docs/demo/screens/01-flux.png" alt="Feed, with a video being processed" width="400"></a><br>Feed, with a video being processed | <a href="docs/demo/screens/02-flux-points-cles.png"><img src="docs/demo/screens/02-flux-points-cles.png" alt="A card's key points" width="400"></a><br>A card's key points |
| <a href="docs/demo/screens/03-flux-filtre-collection.png"><img src="docs/demo/screens/03-flux-filtre-collection.png" alt="Feed filtered by collection" width="400"></a><br>Feed filtered by collection | <a href="docs/demo/screens/04-notes.png"><img src="docs/demo/screens/04-notes.png" alt="A video's notes" width="400"></a><br>A video's notes |
| <a href="docs/demo/screens/05-notes-suite.png"><img src="docs/demo/screens/05-notes-suite.png" alt="Notes, key points and transcript" width="400"></a><br>Notes, key points and transcript | <a href="docs/demo/screens/06-collections.png"><img src="docs/demo/screens/06-collections.png" alt="Collections" width="400"></a><br>Collections |
| <a href="docs/demo/screens/07-cle-api.png"><img src="docs/demo/screens/07-cle-api.png" alt="OpenAI key tab" width="400"></a><br>OpenAI key tab |  |

### Quick start

**Requirements**: [Docker](https://docs.docker.com/get-docker/) with Compose, and an OpenAI API
key ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)).

```bash
docker compose up --build
```

Then open **http://localhost:3000**. The first launch builds the images and takes a few
minutes; later ones start in seconds.

As long as no key is configured, a yellow banner says so at the top of the feed (**Flux**):
click **Colle ta clé** ("paste your key"), paste it, and you're set.

| Service | Address | Role |
| --- | --- | --- |
| Interface | http://localhost:3000 | The application |
| API | http://localhost:8000 | FastAPI backend — interactive docs at `/docs` |
| Database | `localhost:5432` | Postgres + pgvector (user, password and database: `cerebro`) |

All three ports listen on `127.0.0.1` only: nothing is exposed to the rest of the network.

### The OpenAI key

Two ways to provide it, your choice.

#### In the interface — to try things out

**Clé API** tab (http://localhost:3000/settings): paste the key, then **Enregistrer** ("save").
The backend checks it with OpenAI before accepting it — an invalid key is rejected right away,
not in the middle of a job. The panel then shows "Clé active …xxxx — collée ici" (active key,
pasted here).

- The key stays **in the backend's memory**: never written to the database or to disk.
- It is **lost when the backend restarts**: you will have to paste it again.
- The interface and the API only ever show its last 4 characters.
- **Oublier** ("forget") removes it; Cerebro then falls back on the key from `.env`, if any.
- While it is set, it takes precedence over the one in `.env`.

#### In `.env` — to set it once

Create a `.env` file at the project root:

```
OPENAI_API_KEY=sk-...
```

Docker Compose reads it at startup, so the key survives restarts. The **Clé API** tab shows it
as "lue dans OPENAI_API_KEY" (read from OPENAI_API_KEY). The file is ignored by git.

### Usage

#### Add a video

In **Flux**, paste a YouTube URL (or click *Coller depuis le presse-papiers*, "paste from
clipboard"), then **Ajouter** ("add"). Every YouTube URL format is accepted; a video that was
already added is rejected.

Processing runs in the background: download the audio, transcribe it, summarize it, index it
for search. The card's badge goes from *En attente* (queued) to *Traitement…* (processing),
with the elapsed time and an estimate of the time left (which gets sharper as more videos are
processed). The page refreshes on its own; the badge disappears once done. Expect roughly a few
minutes for a half-hour video.

Once processed, the card shows the title, the channel, a short summary, key points and tags.

#### Read the notes

Click a video's title to open its page. On first opening, Cerebro generates **notes**: an
"À retenir" (key takeaways) block, then the content split into bulleted sections — one per item
when the video lists things. They take 5 minutes to read at most, less if the video says
little, and they are kept: later openings are instant.

The full transcript is available on the same page. The URL under the title leads back to the
video.

#### Organize into collections

On a card, **+ Collection** assigns the video to one or more collections — you can create one on
the fly. The **Collections** tab lets you create, rename and delete collections, and browse
their content. In the feed, the drop-down filters by collection.

#### Search

Click the magnifying glass at the top right and describe what you are looking for, in plain
language: *"the video about pgvector"*, *"how to structure a monorepo"*. Search works on the
meaning of the summaries, not on exact words; the closest videos come up with their similarity
score.

#### When processing fails

The card switches to an error state and shows the cause (private video, unreadable audio,
rejected key…). The **Relancer** ("retry") button restarts processing from scratch. Deleting the
video and adding it again does the same.

#### Cost

Everything goes through your OpenAI key. Transcription dominates: about **$0.0045 per minute of
video**, i.e. ~$0.14 for a half-hour video. Summary, notes and search cost a fraction of a cent.

### Stop, restart, start over

```bash
docker compose down          # stops everything; your videos and collections are kept
docker compose up            # restarts (add --build after a code update)
docker compose down -v       # stops AND wipes the database: all data is lost
```

Data lives in the `pgdata` Docker volume. A job running when the stack stops is lost: the video
switches to an error state ("Traitement interrompu par un redémarrage du serveur", processing
interrupted by a server restart) and can be retried in one click.

### Troubleshooting

**`address already in use` at startup** — another program is using port 3000, 8000 or 5432.
Stop it, or change the host port in `docker-compose.yml`. For the interface, also change the
origin allowed by the API:

```yaml
  backend:
    environment:
      CORS_ORIGINS: '["http://localhost:3100"]'
  frontend:
    ports:
      - "127.0.0.1:3100:3000"
```

**"Backend injoignable" (backend unreachable) or lists failing to load** — the API is not
running or crashed: `docker compose logs backend`.

**"Aucune clé OpenAI configurée" (no OpenAI key configured)** — the backend restarted and
forgot the pasted key, or none was ever provided. Paste it again in **Clé API**, or put it in
`.env`.

**"Clé refusée par OpenAI" (key rejected by OpenAI)** — revoked key, bad copy, or an account
with no credit. Check it on platform.openai.com.

**A video keeps failing at download** — private, deleted, members-only or region-blocked video.
YouTube also changes its protections regularly: after a while without updates,
`docker compose build --no-cache backend` fetches the latest `yt-dlp`.

### Configuration

Settings are environment variables passed to the backend (the `environment` section of
`docker-compose.yml`). The defaults suit normal use.

| Variable | Default | Role |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | OpenAI key. Optional if it is pasted in the interface |
| `SUMMARY_MODEL` | `gpt-4o-mini` | Model for the summary and the notes |
| `TRANSCRIPTION_MODEL` | `gpt-transcribe` | Transcription model (`whisper-1` also accepted) |
| `TRANSCRIPTION_LANGUAGES` | `["fr","en"]` | Languages expected in the audio |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model for semantic search |
| `MAX_CHUNK_MB` | `24` | Max size of an audio chunk sent (API limit: 25 MB) |
| `MAX_CHUNK_SECONDS` | `2100` | Max duration of an audio chunk |
| `MAX_TRANSCRIPT_CHARS` | `400000` | Transcript truncation before summarizing |
| `SUBPROCESS_TIMEOUT` | `1800` | Max time for a download or split, in seconds |
| `DATABASE_URL` | `postgresql+asyncpg://cerebro:cerebro@localhost:5432/cerebro` | Postgres connection |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origins allowed to call the API |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API address as seen by the browser (frontend) |

### Under the hood

| Part | Technology |
| --- | --- |
| Interface | Next.js 16 (App Router, TypeScript, Tailwind, SWR) |
| API | FastAPI (Python 3.12), async SQLAlchemy, Alembic |
| Database | Postgres 16 + pgvector |
| Download | yt-dlp (+ deno), ffmpeg |
| AI | OpenAI: `gpt-transcribe`, `gpt-4o-mini`, `text-embedding-3-small` |

A video's pipeline (`backend/app/services/`):

1. **Download** the audio with yt-dlp, along with the title, channel and description.
2. **Split** it with ffmpeg into chunks capped in size *and* duration: 24 MB can hold well over
   an hour of low-bitrate audio, beyond what has been checked to come back complete.
3. **Transcribe** chunk by chunk. The title and description are passed to the model as
   keywords: it finds the exact spelling of the tools and names mentioned there. A warning is
   logged if the resulting text is abnormally short for the duration — a sign of silent
   truncation.
4. **Summarize** into a structured result (short summary, key points, tags, level).
5. **Embed** the summary, stored in pgvector for cosine-similarity search.

Detailed notes are generated separately, the first time a video is opened.

#### API

Full interactive documentation at http://localhost:8000/docs.

| Method | Route | Role |
| --- | --- | --- |
| `POST` | `/api/links` | Adds a YouTube URL and starts processing |
| `GET` | `/api/links` | Lists videos (`collection_id` filter) |
| `GET` | `/api/links/{id}` | A video's details, transcript and notes included |
| `POST` | `/api/links/{id}/digest` | Returns the notes, generating them on first call |
| `PUT` | `/api/links/{id}/collections` | Sets a video's collections |
| `POST` | `/api/links/{id}/retry` | Retries a failed video |
| `DELETE` | `/api/links/{id}` | Deletes a video |
| `GET/POST/PATCH/DELETE` | `/api/collections` | Collection management |
| `GET` | `/api/search?q=` | Semantic search |
| `GET/PUT/DELETE` | `/api/settings/openai-key` | Status, setting and forgetting of the pasted key |

The API has no authentication: that is acceptable because it only listens locally. Do not
expose it on a network — anyone could read your data or replace the key.

### Development

The code is mounted into the containers: backend and frontend reload on every change, with no
rebuild. A rebuild is only needed after a dependency change (`requirements.txt`,
`package.json`).

#### Tests

The backend has a pytest suite (`backend/tests/`) covering the pipeline helpers (YouTube URL
parsing, keyword extraction, audio chunking), processing-time estimation, the embedded text and
OpenAI key handling. It runs without a database or network access: no real OpenAI call is made.

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

The frontend has no tests; it is checked by typing and building:

```bash
cd frontend
npm ci
npm run typecheck
npm run build
```

GitHub Actions CI (`.github/workflows/ci.yml`) runs both jobs on every push and pull request
to `dev`; the badge at the top of this page shows the result.

#### Without Docker

The backend needs `ffmpeg`, `deno` (JS runtime required by yt-dlp) and a Postgres/pgvector
database — the simplest is the Compose one:

```bash
docker compose up db

cd backend && pip install -r requirements.txt
DATABASE_URL=postgresql+asyncpg://cerebro:cerebro@localhost:5432/cerebro uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

#### Schema migrations

The schema is versioned with Alembic (`backend/migrations/`) and applied automatically every
time the backend starts. After changing `backend/app/models.py`:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
```

`alembic.ini` holds no URL: it is read from `DATABASE_URL`, like the backend does.

### Roadmap — SaaS version

1. **Multi-user foundation.** Move from single-account use to per-user isolation:
   authentication, partitioning of data and corpus, per-account secret management. This is the
   seam everything else depends on.
2. **Industrialized processing.** Take ingestion out of the web process: durable queue,
   dedicated workers, recovery after failure, idempotency. Today a restart loses in-flight jobs.
3. **Unit economics.** Lower the marginal cost of an ingestion: alternative acquisition sources,
   pre-filtering before the paid steps, caching of intermediate results. This is what decides
   whether the pricing model holds at scale.
4. **Augmented retrieval.** Make use of the accumulated corpus rather than each document in
   isolation: vector indexing, hybrid search, source-grounded generation (RAG). Value grows with
   the volume already ingested.
5. **Operations.** Usage metering, quotas, observability and per-account cost tracking. Without
   them, billing relies on estimates rather than measurements.

---

## Français

Outil de veille personnel : tu colles l'URL d'une vidéo YouTube, Cerebro la transcrit, en tire
un résumé structuré et des notes de lecture, et te permet ensuite de retrouver n'importe quelle
vidéo en posant une question en langage naturel.

**Cerebro tourne en local, sur ta machine.** Il n'y a ni déploiement, ni comptes, ni serveur
distant : une base Postgres, une API et une interface web démarrent dans Docker, et seuls les
appels à l'API OpenAI (transcription, résumé, recherche) sortent de ta machine. C'est un outil
mono-utilisateur, pensé pour être lancé quand tu en as besoin.

### Sommaire

- [Captures d'écran](#captures-décran)
- [Démarrage rapide](#démarrage-rapide)
- [La clé OpenAI](#la-clé-openai)
- [Utilisation](#utilisation)
- [Arrêter, relancer, repartir de zéro](#arrêter-relancer-repartir-de-zéro)
- [Dépannage](#dépannage)
- [Configuration](#configuration-1)
- [Sous le capot](#sous-le-capot)
- [Développement](#développement)
- [Roadmap — version SaaS](#roadmap--version-saas)

### Captures d'écran

Les images et la [version vidéo (MP4, 18 s)](docs/demo/cerebro-demo.mp4) montrent des données
d'exemple : les chaînes et vidéos affichées sont inventées.

| | |
| --- | --- |
| <a href="docs/demo/screens/01-flux.png"><img src="docs/demo/screens/01-flux.png" alt="Flux, avec une vidéo en cours de traitement" width="400"></a><br>Flux, avec une vidéo en cours de traitement | <a href="docs/demo/screens/02-flux-points-cles.png"><img src="docs/demo/screens/02-flux-points-cles.png" alt="Points clés d'une carte" width="400"></a><br>Points clés d'une carte |
| <a href="docs/demo/screens/03-flux-filtre-collection.png"><img src="docs/demo/screens/03-flux-filtre-collection.png" alt="Flux filtré par collection" width="400"></a><br>Flux filtré par collection | <a href="docs/demo/screens/04-notes.png"><img src="docs/demo/screens/04-notes.png" alt="Notes d'une vidéo" width="400"></a><br>Notes d'une vidéo |
| <a href="docs/demo/screens/05-notes-suite.png"><img src="docs/demo/screens/05-notes-suite.png" alt="Notes, points clés et transcription" width="400"></a><br>Notes, points clés et transcription | <a href="docs/demo/screens/06-collections.png"><img src="docs/demo/screens/06-collections.png" alt="Collections" width="400"></a><br>Collections |
| <a href="docs/demo/screens/07-cle-api.png"><img src="docs/demo/screens/07-cle-api.png" alt="Onglet Clé API" width="400"></a><br>Onglet Clé API |  |

### Démarrage rapide

**Prérequis** : [Docker](https://docs.docker.com/get-docker/) avec Compose, et une clé API
OpenAI ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)).

```bash
docker compose up --build
```

Puis ouvre **http://localhost:3000**. Le premier lancement construit les images et prend
quelques minutes ; les suivants démarrent en quelques secondes.

Tant qu'aucune clé n'est configurée, un bandeau jaune le signale en haut du Flux : clique sur
**Colle ta clé**, colle-la, et c'est prêt.

| Service | Adresse | Rôle |
| --- | --- | --- |
| Interface | http://localhost:3000 | L'application |
| API | http://localhost:8000 | Backend FastAPI — documentation interactive sur `/docs` |
| Base | `localhost:5432` | Postgres + pgvector (utilisateur, mot de passe et base : `cerebro`) |

Les trois ports n'écoutent que sur `127.0.0.1` : rien n'est exposé au reste du réseau.

### La clé OpenAI

Deux façons de la fournir, au choix.

#### Dans l'interface — pour tester

Onglet **Clé API** (http://localhost:3000/settings) : colle la clé, **Enregistrer**. Le backend
la vérifie auprès d'OpenAI avant de l'accepter — une clé invalide est refusée tout de suite, pas
au milieu d'un traitement. L'encart passe alors à « Clé active …xxxx — collée ici ».

- La clé reste **en mémoire du backend** : jamais écrite en base ni sur disque.
- Elle **disparaît au redémarrage** du backend : il faudra la recoller.
- L'interface et l'API n'en montrent jamais que les 4 derniers caractères.
- **Oublier** la retire ; Cerebro retombe alors sur la clé du fichier `.env`, s'il y en a une.
- Tant qu'elle est posée, elle a priorité sur celle du `.env`.

#### Dans `.env` — pour ne plus y penser

Crée un fichier `.env` à la racine du projet :

```
OPENAI_API_KEY=sk-...
```

Docker Compose le lit au lancement ; la clé survit alors aux redémarrages. L'onglet **Clé API**
l'affiche comme « lue dans OPENAI_API_KEY ». Le fichier est ignoré par git.

### Utilisation

#### Ajouter une vidéo

Dans **Flux**, colle une URL YouTube (ou clique sur *Coller depuis le presse-papiers*) puis
**Ajouter**. Tous les formats d'URL YouTube sont acceptés ; une vidéo déjà ajoutée est refusée.

Le traitement part en tâche de fond : télécharger l'audio, le transcrire, le résumer, l'indexer
pour la recherche. Le badge de la carte passe de *En attente* à *Traitement…*, avec le temps
écoulé et une estimation du temps restant (qui s'affine au fil des vidéos traitées). La page se
rafraîchit seule ; le badge disparaît quand c'est fini. Compte grossièrement quelques minutes
pour une vidéo d'une demi-heure.

Une fois traitée, la carte affiche le titre, la chaîne, un résumé court, les points clés et des
tags.

#### Lire les notes

Clique sur le titre d'une vidéo pour ouvrir sa page. À la première ouverture, Cerebro génère
des **notes** : un bloc « À retenir », puis le propos découpé en sections à puces — une par
élément quand la vidéo énumère des choses. Elles se lisent en 5 minutes au plus, moins si la
vidéo dit peu, et sont conservées : les ouvertures suivantes sont instantanées.

La transcription complète est disponible sur la même page. L'URL sous le titre ramène à la
vidéo.

#### Ranger en collections

Sur une carte, **+ Collection** assigne la vidéo à une ou plusieurs collections — tu peux en
créer une à la volée. L'onglet **Collections** permet de créer, renommer et supprimer les
collections, et d'en consulter le contenu. Dans le Flux, le menu déroulant filtre par
collection.

#### Rechercher

Clique sur la loupe en haut à droite et décris ce que tu cherches, en langage naturel :
*« la vidéo qui parlait de pgvector »*, *« comment structurer un monorepo »*. La recherche
porte sur le sens des résumés, pas sur les mots exacts ; les vidéos les plus proches remontent
avec leur score de similarité.

#### Quand un traitement échoue

La carte passe en erreur et affiche la cause (vidéo privée, audio illisible, clé refusée…).
Le bouton **Relancer** recommence le traitement depuis le début. Supprimer la vidéo puis la
rajouter revient au même.

#### Coût

Tout passe par ta clé OpenAI. La transcription domine : environ **0,0045 $ par minute de
vidéo**, soit ~0,14 $ pour une vidéo d'une demi-heure. Le résumé, les notes et la recherche
coûtent une fraction de centime.

### Arrêter, relancer, repartir de zéro

```bash
docker compose down          # arrête tout ; tes vidéos et collections sont conservées
docker compose up            # relance (ajoute --build après une mise à jour du code)
docker compose down -v       # arrête ET efface la base : toutes les données sont perdues
```

Les données vivent dans le volume Docker `pgdata`. Un traitement en cours au moment d'un arrêt
est perdu : la vidéo passe en erreur (« Traitement interrompu par un redémarrage du serveur »)
et se relance d'un clic.

### Dépannage

**`address already in use` au lancement** — un autre programme occupe le port 3000, 8000 ou
5432. Arrête-le, ou change le port côté hôte dans `docker-compose.yml`. Pour l'interface, change
aussi l'origine autorisée par l'API :

```yaml
  backend:
    environment:
      CORS_ORIGINS: '["http://localhost:3100"]'
  frontend:
    ports:
      - "127.0.0.1:3100:3000"
```

**« Backend injoignable » ou listes vides en erreur** — l'API ne tourne pas ou a planté :
`docker compose logs backend`.

**« Aucune clé OpenAI configurée »** — le backend a redémarré et oublié la clé collée, ou aucune
n'a jamais été fournie. Recolle-la dans **Clé API**, ou mets-la dans `.env`.

**« Clé refusée par OpenAI »** — clé révoquée, mal copiée, ou compte sans crédit. Vérifie-la
sur platform.openai.com.

**Une vidéo reste en erreur au téléchargement** — vidéo privée, supprimée, réservée aux
membres ou bloquée dans ta région. YouTube change aussi régulièrement ses protections : après
un moment sans mise à jour, `docker compose build --no-cache backend` récupère la dernière
version de `yt-dlp`.

### Configuration

Les réglages se passent en variables d'environnement au backend (section `environment` de
`docker-compose.yml`). Les valeurs par défaut conviennent pour un usage normal.

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | Clé OpenAI. Facultative si elle est collée dans l'interface |
| `SUMMARY_MODEL` | `gpt-4o-mini` | Modèle du résumé et des notes |
| `TRANSCRIPTION_MODEL` | `gpt-transcribe` | Modèle de transcription (`whisper-1` accepté) |
| `TRANSCRIPTION_LANGUAGES` | `["fr","en"]` | Langues attendues dans l'audio |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Modèle de la recherche sémantique |
| `MAX_CHUNK_MB` | `24` | Taille max d'un morceau d'audio envoyé (limite API : 25 Mo) |
| `MAX_CHUNK_SECONDS` | `2100` | Durée max d'un morceau d'audio |
| `MAX_TRANSCRIPT_CHARS` | `400000` | Troncature de la transcription avant résumé |
| `SUBPROCESS_TIMEOUT` | `1800` | Délai max d'un téléchargement ou découpage, en secondes |
| `DATABASE_URL` | `postgresql+asyncpg://cerebro:cerebro@localhost:5432/cerebro` | Connexion Postgres |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origines autorisées à appeler l'API |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Adresse de l'API vue par le navigateur (frontend) |

### Sous le capot

| Brique | Technologie |
| --- | --- |
| Interface | Next.js 16 (App Router, TypeScript, Tailwind, SWR) |
| API | FastAPI (Python 3.12), SQLAlchemy async, Alembic |
| Base | Postgres 16 + pgvector |
| Téléchargement | yt-dlp (+ deno), ffmpeg |
| IA | OpenAI : `gpt-transcribe`, `gpt-4o-mini`, `text-embedding-3-small` |

Le pipeline d'une vidéo (`backend/app/services/`) :

1. **Téléchargement** de l'audio avec yt-dlp, avec le titre, la chaîne et la description.
2. **Découpage** avec ffmpeg en morceaux bornés en taille *et* en durée : 24 Mo peuvent contenir
   bien plus d'une heure d'audio peu dense, au-delà de ce qui a été vérifié complet.
3. **Transcription** morceau par morceau. Le titre et la description sont passés au modèle
   comme mots-clés : il y trouve l'orthographe exacte des outils et noms cités. Un
   avertissement est journalisé si le texte obtenu est anormalement court pour la durée —
   signe d'une troncature silencieuse.
4. **Résumé** structuré (résumé court, points clés, tags, niveau).
5. **Embedding** du résumé, stocké dans pgvector pour la recherche par similarité cosinus.

Les notes détaillées sont générées à part, à la première ouverture d'une vidéo.

#### API

Documentation interactive complète sur http://localhost:8000/docs.

| Méthode | Route | Rôle |
| --- | --- | --- |
| `POST` | `/api/links` | Ajoute une URL YouTube et lance le traitement |
| `GET` | `/api/links` | Liste les vidéos (filtre `collection_id`) |
| `GET` | `/api/links/{id}` | Détail d'une vidéo, transcription et notes incluses |
| `POST` | `/api/links/{id}/digest` | Rend les notes, en les générant au premier appel |
| `PUT` | `/api/links/{id}/collections` | Assigne les collections d'une vidéo |
| `POST` | `/api/links/{id}/retry` | Relance une vidéo en erreur |
| `DELETE` | `/api/links/{id}` | Supprime une vidéo |
| `GET/POST/PATCH/DELETE` | `/api/collections` | Gestion des collections |
| `GET` | `/api/search?q=` | Recherche sémantique |
| `GET/PUT/DELETE` | `/api/settings/openai-key` | État, pose et oubli de la clé collée |

L'API n'a pas d'authentification : c'est acceptable parce qu'elle n'écoute qu'en local. Ne
l'expose pas sur un réseau — n'importe qui pourrait lire tes données ou remplacer la clé.

### Développement

Le code est monté dans les conteneurs : backend et frontend se rechargent à chaque
modification, sans rebuild. Un rebuild n'est nécessaire qu'après un changement de dépendances
(`requirements.txt`, `package.json`).

#### Tests

Le backend a une suite pytest (`backend/tests/`) qui couvre les fonctions du pipeline (lecture
des URL YouTube, extraction des mots-clés, découpage audio), l'estimation du temps de
traitement, le texte embeddé et la gestion de la clé OpenAI. Elle tourne sans base ni accès
réseau : aucun vrai appel à OpenAI n'est fait.

```bash
cd backend
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

Le frontend n'a pas de tests ; il est vérifié par le typage et le build :

```bash
cd frontend
npm ci
npm run typecheck
npm run build
```

La CI GitHub Actions (`.github/workflows/ci.yml`) lance les deux à chaque push et pull request
sur `dev` ; le badge en haut de cette page en affiche le résultat.

#### Hors Docker

Le backend a besoin de `ffmpeg`, de `deno` (runtime JS requis par yt-dlp) et d'une base
Postgres/pgvector — la plus simple reste celle du Compose :

```bash
docker compose up db

cd backend && pip install -r requirements.txt
DATABASE_URL=postgresql+asyncpg://cerebro:cerebro@localhost:5432/cerebro uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

#### Migrations de schéma

Le schéma est versionné avec Alembic (`backend/migrations/`) et appliqué automatiquement à
chaque démarrage du backend. Après une modification de `backend/app/models.py` :

```bash
cd backend
alembic revision --autogenerate -m "décrit le changement"
```

`alembic.ini` ne contient pas d'URL : elle est lue dans `DATABASE_URL`, comme pour le backend.

### Roadmap — version SaaS

1. **Socle multi-utilisateur.** Passer d'un usage mono-compte à l'isolation par utilisateur :
   authentification, cloisonnement des données et du corpus, gestion des secrets propres à
   chaque compte. C'est la couture qui conditionne tout le reste.
2. **Industrialisation du traitement.** Sortir l'ingestion du processus web : file d'attente
   durable, workers dédiés, reprise après échec, idempotence. Aujourd'hui un redémarrage perd
   les traitements en vol.
3. **Économie unitaire.** Réduire le coût marginal d'une ingestion : sources d'acquisition
   alternatives, pré-filtrage avant les étapes payantes, mise en cache des résultats
   intermédiaires. C'est ce qui décide si le modèle tarifaire tient à l'échelle.
4. **Récupération augmentée.** Exploiter le corpus accumulé plutôt que chaque document
   isolément : indexation vectorielle, recherche hybride, génération appuyée sur les sources
   (RAG). La valeur croît avec le volume déjà ingéré.
5. **Exploitation.** Métrage à l'usage, quotas, observabilité et traçabilité des coûts par
   compte. Sans ça, la facturation repose sur des estimations plutôt que sur des mesures.
