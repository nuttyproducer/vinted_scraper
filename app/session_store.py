"""Persist a pasted Vinted session cookie to a local file."""

import json
from pathlib import Path

DEFAULT_PATH = Path.home() / ".vinted_research" / "session.json"


class SessionStore:
    """Store and load a pasted ``access_token_web`` cookie on disk."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path

    def load(self) -> str | None:
        """Return the stored cookie, or ``None`` if missing or corrupt."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get("cookie")
        except (OSError, ValueError):
            return None

    def save(self, cookie: str) -> None:
        """Persist the cookie, raising ``ValueError`` when it is blank."""
        cookie = cookie.strip()
        if not cookie:
            raise ValueError("cookie must not be empty")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"cookie": cookie}), encoding="utf-8")

    def clear(self) -> None:
        """Delete the stored cookie file, if any."""
        try:
            self.path.unlink()
        except OSError:
            pass
