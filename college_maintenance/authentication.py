"""Local opaque bearer credentials; no caller-supplied user IDs or roles."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
from college_maintenance.database import PROJECT_ROOT

def authenticate_token(token):
    """Provision SHA-256 token digests out of band in an ignored local file.

    Each value is {actor_id: UUID, expires_at: aware ISO timestamp}. No login,
    public token issuance, or production identity provider is implied here.
    """
    path = Path(os.environ.get('COLLEGE_API_TOKENS_FILE', PROJECT_ROOT/'.local/api-tokens.json'))
    try:
        entries = json.loads(path.read_text(encoding='utf-8'))
        entry = entries[hashlib.sha256(token.encode()).hexdigest()]
        expires = datetime.fromisoformat(entry['expires_at'])
        if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
            return None
        return UUID(entry['actor_id'])
    except (OSError, ValueError, TypeError, KeyError):
        return None
