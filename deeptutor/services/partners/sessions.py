"""Lightweight JSONL conversation store for partner sessions.

One JSONL file per session key (``telegram:12345``, ``web:<session_id>``,
``partner:<id>`` …) under ``data/partners/<id>/sessions/``. This is the
partner-side replacement for the deleted engine's SessionManager: it only
has to hand the chat agent loop an OpenAI-format ``conversation_history``
and back the history API, so a flat append-only file per session is enough.
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from pathlib import Path
import threading
from typing import Any

from deeptutor.partners.helpers import safe_filename

logger = logging.getLogger(__name__)

_HISTORY_MAX_MESSAGES = 40
_HISTORY_MAX_CHARS = 24_000
_ARCHIVE_PREFIX = "_archived_"


class PartnerSessionStore:
    """Append-only JSONL persistence for one partner's conversations."""

    def __init__(self, sessions_dir: Path) -> None:
        self._dir = sessions_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def _path(self, session_key: str) -> Path:
        return self._dir / f"{safe_filename(session_key) or 'default'}.jsonl"

    @staticmethod
    def is_archived_key(session_key: str) -> bool:
        return safe_filename(session_key).startswith(_ARCHIVE_PREFIX)

    # ── write ─────────────────────────────────────────────────────

    def append(
        self,
        session_key: str,
        role: str,
        content: str,
        *,
        channel: str = "",
        sender_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if channel:
            record["channel"] = channel
        if sender_id:
            record["sender_id"] = sender_id
        if metadata:
            record["metadata"] = metadata
        line = json.dumps(record, ensure_ascii=False)
        with self._write_lock:
            with open(self._path(session_key), "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def clear(self, session_key: str) -> bool:
        path = self._path(session_key)
        if not path.exists():
            return False
        path.unlink()
        return True

    def archive(self, session_key: str) -> dict[str, Any] | None:
        """Move the current session file aside and return its archive summary.

        The active key remains reusable: after archiving ``telegram:42``, new
        messages write to ``telegram_42.jsonl`` while the old file is kept as a
        separate archived session that can still be inspected through the
        history API by using the returned ``session_key``.
        """
        path = self._path(session_key)
        if not path.exists():
            return None
        records = self._read_records(session_key)
        if not records:
            return None

        safe_key = safe_filename(session_key) or "default"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_key = f"{_ARCHIVE_PREFIX}{stamp}_{safe_key}"
        archive_path = self._path(archive_key)
        suffix = 1
        while archive_path.exists():
            archive_key = f"{_ARCHIVE_PREFIX}{stamp}_{suffix}_{safe_key}"
            archive_path = self._path(archive_key)
            suffix += 1

        with self._write_lock:
            if not path.exists():
                return None
            path.replace(archive_path)

        return self._session_summary(archive_path)

    # ── read ──────────────────────────────────────────────────────

    def _read_records(self, session_key: str) -> list[dict[str, Any]]:
        path = self._path(session_key)
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(data, dict) and data.get("role") and data.get("content"):
                        records.append(data)
        except OSError:
            logger.exception("Failed to read partner session %s", session_key)
        return records

    def conversation_history(
        self,
        session_key: str,
        *,
        max_messages: int = _HISTORY_MAX_MESSAGES,
        max_chars: int = _HISTORY_MAX_CHARS,
    ) -> list[dict[str, str]]:
        """Return trailing history in OpenAI message format, budget-capped."""
        records = self._read_records(session_key)
        window = [
            {"role": str(r["role"]), "content": str(r["content"])}
            for r in records[-max_messages:]
            if r.get("role") in {"user", "assistant"}
        ]
        total = 0
        kept: list[dict[str, str]] = []
        for message in reversed(window):
            total += len(message["content"])
            if kept and total > max_chars:
                break
            kept.append(message)
        kept.reverse()
        return kept

    def messages(self, session_key: str, *, limit: int = 100) -> list[dict[str, Any]]:
        """Raw records (role/content/timestamp/...) for the history API."""
        return self._read_records(session_key)[-limit:]

    def merged_messages(
        self, *, limit: int = 100, include_archived: bool = False
    ) -> list[dict[str, Any]]:
        """All sessions' records merged chronologically (recent-activity view)."""
        merged: list[tuple[str, int, dict[str, Any]]] = []
        sequence = 0
        for path in sorted(self._dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime):
            if not include_archived and self.is_archived_key(path.stem):
                continue
            key = path.stem
            for record in self._read_records(key):
                merged.append((str(record.get("timestamp", "")), sequence, record))
                sequence += 1
        merged.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in merged[-limit:]]

    def _session_summary(self, path: Path) -> dict[str, Any]:
        records = self._read_records(path.stem)
        last = records[-1] if records else {}
        archived = self.is_archived_key(path.stem)
        return {
            "session_key": path.stem,
            "message_count": len(records),
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "last_message": str(last.get("content", ""))[:200],
            "archived": archived,
        }

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            self._session_summary(path)
            for path in sorted(
                self._dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
            )
        ]


__all__ = ["PartnerSessionStore"]
