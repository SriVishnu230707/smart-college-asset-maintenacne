"""One synchronous Engine per process; importing it opens no DB connection."""

import os
from pathlib import Path

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def connection_url() -> URL:
    """Use the existing learner secret and Compose's configurable host port."""
    configured=os.environ.get('COLLEGE_DATABASE_URL_FILE')
    if configured:
        url=make_url(Path(configured).read_text(encoding='utf-8').strip())
        if url.drivername!='postgresql+psycopg':raise ValueError('A psycopg PostgreSQL URL is required')
        return url
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


def pool_settings():
    values={key:int(os.environ.get(env,default)) for key,env,default in [
        ('pool_size','COLLEGE_POOL_SIZE','1'),('max_overflow','COLLEGE_MAX_OVERFLOW','0'),
        ('pool_timeout','COLLEGE_POOL_TIMEOUT','5')]}
    if not 1<=values['pool_size']<=100 or not 0<=values['max_overflow']<=100 or not 1<=values['pool_timeout']<=60:
        raise ValueError('Pool configuration must be finite and within documented bounds')
    return values

# A single slot makes sequential pool reuse easy to observe in this lesson.
# This is a learning configuration, not production pool sizing.
engine = create_engine(
    connection_url(),
    echo=os.environ.get("COLLEGE_SQL_ECHO", "0") == "1",
    hide_parameters=True,
    **pool_settings(),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5, "application_name": "college_step13", "options": "-c timezone=UTC"},
)
