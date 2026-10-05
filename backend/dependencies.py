from backend.models.session_store import SessionStore, session_store


def get_store() -> SessionStore:
    return session_store
