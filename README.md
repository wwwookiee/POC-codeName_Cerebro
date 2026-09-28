# Cerebro

Outil de veille personnel : tu colles l'URL d'une vidéo YouTube, Cerebro la transcrit, en tire
un résumé structuré et des notes de lecture, et te permet ensuite de retrouver n'importe quelle
vidéo en posant une question en langage naturel.

**Cerebro tourne en local, sur ta machine.** Il n'y a ni déploiement, ni comptes, ni serveur
distant : une base Postgres, une API et une interface web démarrent dans Docker, et seuls les
appels à l'API OpenAI (transcription, résumé, recherche) sortent de ta machine. C'est un outil
mono-utilisateur, pensé pour être lancé quand tu en as besoin.

## Sommaire

- [Démarrage rapide](#démarrage-rapide)
- [La clé OpenAI](#la-clé-openai)
- [Utilisation](#utilisation)
- [Arrêter, relancer, repartir de zéro](#arrêter-relancer-repartir-de-zéro)
- [Dépannage](#dépannage)
- [Configuration](#configuration)
- [Sous le capot](#sous-le-capot)
- [Développement](#développement)

## Démarrage rapide

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

## La clé OpenAI

Deux façons de la fournir, au choix.

### Dans l'interface — pour tester

Onglet **Clé API** (http://localhost:3000/settings) : colle la clé, **Enregistrer**. Le backend
la vérifie auprès d'OpenAI avant de l'accepter — une clé invalide est refusée tout de suite, pas
au milieu d'un traitement. L'encart passe alors à « Clé active …xxxx — collée ici ».

- La clé reste **en mémoire du backend** : jamais écrite en base ni sur disque.
- Elle **disparaît au redémarrage** du backend : il faudra la recoller.
- L'interface et l'API n'en montrent jamais que les 4 derniers caractères.
- **Oublier** la retire ; Cerebro retombe alors sur la clé du fichier `.env`, s'il y en a une.
- Tant qu'elle est posée, elle a priorité sur celle du `.env`.

### Dans `.env` — pour ne plus y penser

Crée un fichier `.env` à la racine du projet :

```
OPENAI_API_KEY=sk-...
```

Docker Compose le lit au lancement ; la clé survit alors aux redémarrages. L'onglet **Clé API**
l'affiche comme « lue dans OPENAI_API_KEY ». Le fichier est ignoré par git.

## Utilisation

### Ajouter une vidéo

Dans **Flux**, colle une URL YouTube (ou clique sur *Coller depuis le presse-papiers*) puis
**Ajouter**. Tous les formats d'URL YouTube sont acceptés ; une vidéo déjà ajoutée est refusée.

Le traitement part en tâche de fond : télécharger l'audio, le transcrire, le résumer, l'indexer
pour la recherche. Le badge de la carte passe de *En attente* à *Traitement…*, avec le temps
écoulé et une estimation du temps restant (qui s'affine au fil des vidéos traitées). La page se
rafraîchit seule ; le badge disparaît quand c'est fini. Compte grossièrement quelques minutes
pour une vidéo d'une demi-heure.

Une fois traitée, la carte affiche le titre, la chaîne, un résumé court, les points clés et des
tags.

### Lire les notes

Clique sur le titre d'une vidéo pour ouvrir sa page. À la première ouverture, Cerebro génère
des **notes** : un bloc « À retenir », puis le propos découpé en sections à puces — une par
élément quand la vidéo énumère des choses. Elles se lisent en 5 minutes au plus, moins si la
vidéo dit peu, et sont conservées : les ouvertures suivantes sont instantanées.

La transcription complète est disponible sur la même page. L'URL sous le titre ramène à la
vidéo.

### Ranger en collections

Sur une carte, **+ Collection** assigne la vidéo à une ou plusieurs collections — tu peux en
créer une à la volée. L'onglet **Collections** permet de créer, renommer et supprimer les
collections, et d'en consulter le contenu. Dans le Flux, le menu déroulant filtre par
collection.

### Rechercher

Clique sur la loupe en haut à droite et décris ce que tu cherches, en langage naturel :
*« la vidéo qui parlait de pgvector »*, *« comment structurer un monorepo »*. La recherche
porte sur le sens des résumés, pas sur les mots exacts ; les vidéos les plus proches remontent
avec leur score de similarité.

### Quand un traitement échoue

La carte passe en erreur et affiche la cause (vidéo privée, audio illisible, clé refusée…).
Le bouton **Relancer** recommence le traitement depuis le début. Supprimer la vidéo puis la
rajouter revient au même.

### Coût

Tout passe par ta clé OpenAI. La transcription domine : environ **0,0045 $ par minute de
vidéo**, soit ~0,14 $ pour une vidéo d'une demi-heure. Le résumé, les notes et la recherche
coûtent une fraction de centime.

## Arrêter, relancer, repartir de zéro

```bash
docker compose down          # arrête tout ; tes vidéos et collections sont conservées
docker compose up            # relance (ajoute --build après une mise à jour du code)
docker compose down -v       # arrête ET efface la base : toutes les données sont perdues
```

Les données vivent dans le volume Docker `pgdata`. Un traitement en cours au moment d'un arrêt
est perdu : la vidéo passe en erreur (« Traitement interrompu par un redémarrage du serveur »)
et se relance d'un clic.

## Dépannage

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

## Configuration

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

## Sous le capot

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

### API

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

## Développement

Le code est monté dans les conteneurs : backend et frontend se rechargent à chaque
modification, sans rebuild. Un rebuild n'est nécessaire qu'après un changement de dépendances
(`requirements.txt`, `package.json`).

### Hors Docker

Le backend a besoin de `ffmpeg`, de `deno` (runtime JS requis par yt-dlp) et d'une base
Postgres/pgvector — la plus simple reste celle du Compose :

```bash
docker compose up db

cd backend && pip install -r requirements.txt
DATABASE_URL=postgresql+asyncpg://cerebro:cerebro@localhost:5432/cerebro uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

### Migrations de schéma

Le schéma est versionné avec Alembic (`backend/migrations/`) et appliqué automatiquement à
chaque démarrage du backend. Après une modification de `backend/app/models.py` :

```bash
cd backend
alembic revision --autogenerate -m "décrit le changement"
```

`alembic.ini` ne contient pas d'URL : elle est lue dans `DATABASE_URL`, comme pour le backend.
