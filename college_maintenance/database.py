"""One synchronous Engine per process; importing it opens no DB connection."""

import os
from pathlib import Path

from sqlalchemy import URL, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def connection_url() -> URL:
    """Use the existing learner secret and Compose's configurable host port."""
    secret_file = PROJECT_ROOT / ".local" / "college-learner-password"
    if not secret_file.is_file():
        raise RuntimeError("Start labs/step-02/start.ps1 to create the local learner credential")
    password = secret_file.read_text(encoding="utf-8").rstrip("\r\n")
    if not password:
        raise ValueError("The local learner credential is empty")
    port = int(os.environ.get("COLLEGE_POSTGRES_PORT", "55432"))
    if not 1 <= port <= 65535:
        raise ValueError("COLLEGE_POSTGRES_PORT must be between 1 and 65535")
    return URL.create("postgresql+psycopg", username="college_learner", password=password,
                      host="127.0.0.1", port=port, database="college_learning")


# A single slot makes sequential pool reuse easy to observe in this lesson.
# This is a learning configuration, not production pool sizing.
engine = create_engine(
    connection_url(),
    echo=os.environ.get("COLLEGE_SQL_ECHO", "0") == "1",
    hide_parameters=True,
    pool_size=1,
    max_overflow=0,
    pool_timeout=5,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5, "application_name": "college_step13", "options": "-c timezone=UTC"},
)
