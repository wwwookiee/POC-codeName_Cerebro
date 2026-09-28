"""Pose une clé OpenAI factice avant tout import de `app.*`.

`openai_api_key` est facultative — la clé peut aussi être collée dans
l'interface — mais les tests du pipeline construisent un client : une valeur
d'environnement leur évite de dépendre de l'état du module `openai_key`. Le
fichier `.env` ne dépanne pas ici, `pydantic-settings` le résolvant depuis le
répertoire courant alors qu'il vit à la racine du dépôt, pas dans `backend/`.

Aucun appel réseau n'est fait par les tests : la valeur n'a pas à être valide,
et `openai_client()` ne construit son client qu'à l'appel, jamais à l'import.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "cle-factice-pour-les-tests")
