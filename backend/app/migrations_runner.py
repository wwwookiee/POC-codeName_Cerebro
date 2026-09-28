"""Application des migrations Alembic au démarrage de l'API.

Le schéma était créé par `Base.metadata.create_all`, qui crée les tables
manquantes mais n'altère jamais une table existante. Les bases nées avant
Alembic n'ont donc pas de table `alembic_version` : on les estampille sur la
révision de référence avant de dérouler les migrations suivantes, sinon la
baseline tenterait de recréer des tables déjà là.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, inspect

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
BASELINE_REVISION = "0001_baseline"


def _config(connection: Connection) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_INI.parent / "migrations"))
    config.attributes["connection"] = connection
    return config


def upgrade_to_head(connection: Connection) -> None:
    """Migre la base jusqu'à la dernière révision. À passer à `run_sync`."""
    tables = set(inspect(connection).get_table_names())
    config = _config(connection)

    if "alembic_version" not in tables and "links" in tables:
        command.stamp(config, BASELINE_REVISION)

    command.upgrade(config, "head")
