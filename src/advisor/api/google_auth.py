from __future__ import annotations

from google.auth.transport import requests
from google.oauth2 import id_token

from src.advisor.api.auth_store import get_google_client_ids


def verify_google_credential(credential: str) -> dict:
    client_ids = get_google_client_ids()
    if not client_ids:
        raise RuntimeError("GOOGLE_CLIENT_ID is missing in the backend environment.")

    last_error: Exception | None = None
    request = requests.Request()
    for client_id in client_ids:
        try:
            return id_token.verify_oauth2_token(credential, request, audience=client_id)
        except Exception as exc:  # pragma: no cover - provider error surface varies
            last_error = exc

    raise RuntimeError(f"Google OAuth verification failed: {last_error}")
