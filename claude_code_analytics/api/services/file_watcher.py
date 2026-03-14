"""File watcher for auto-importing new conversation sessions."""

import asyncio
import contextlib
import logging
import sqlite3
import time
from pathlib import Path

from claude_code_analytics import config
from claude_code_analytics.api.services.event_bus import EventBus

logger = logging.getLogger(__name__)

# Minimum seconds between imports of the same file
_PER_FILE_COOLDOWN = 30.0


class FileWatcher:
    """Watches the Claude conversations directory for new/changed JSONL files."""

    def __init__(self, event_bus: EventBus, debounce_seconds: float = 2.0):
        self.event_bus = event_bus
        self.debounce_seconds = debounce_seconds
        self._task: asyncio.Task | None = None
        self._last_import: dict[str, float] = {}

    async def start(self) -> None:
        """Run catch-up import for missed files, then start watching."""
        await self._catchup_import()
        self._task = asyncio.create_task(self._watch())

    async def _catchup_import(self) -> None:
        """Import any .jsonl files that changed while the app was not running.

        Compares file mtime against the session's last known end_time in the DB.
        New files (not in DB) and files modified after their DB timestamp are imported.
        """
        watch_dir = config.CLAUDE_CODE_PROJECTS_DIR
        if not watch_dir.exists():
            return

        db_path = str(config.DATABASE_PATH)
        if not Path(db_path).exists():
            return

        loop = asyncio.get_event_loop()

        # Build a map of session_id -> last known end_time (as epoch)
        def _get_session_timestamps() -> dict[str, float]:
            from datetime import datetime, timezone

            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT session_id, end_time FROM sessions WHERE end_time IS NOT NULL"
                )
                result = {}
                for session_id, end_time_str in cursor.fetchall():
                    try:
                        dt = datetime.fromisoformat(end_time_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        result[session_id] = dt.timestamp()
                    except (ValueError, AttributeError):
                        pass
                return result
            finally:
                conn.close()

        try:
            session_times = await loop.run_in_executor(None, _get_session_timestamps)
        except Exception:
            logger.exception("Failed to read session timestamps for catch-up")
            return

        # Scan all .jsonl files and find ones that need importing
        stale_files: list[Path] = []
        for project_dir in watch_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for jsonl_file in project_dir.glob("**/*.jsonl"):
                session_id = jsonl_file.stem
                file_mtime = jsonl_file.stat().st_mtime
                db_time = session_times.get(session_id)
                if db_time is None or file_mtime > db_time + 1:
                    stale_files.append(jsonl_file)

        if not stale_files:
            logger.info("Catch-up: all sessions up to date")
            return

        logger.info(f"Catch-up: importing {len(stale_files)} changed session(s)")

        from claude_code_analytics.api.services.import_service import import_single_session

        imported = 0
        now = time.monotonic()
        for path in stale_files:
            try:
                result = await loop.run_in_executor(None, import_single_session, path)
                # Seed cooldown so the watcher doesn't re-import these immediately
                self._last_import[str(path)] = now
                if result:
                    imported += 1
                    await self.event_bus.publish(
                        {
                            "type": "session_imported",
                            "session_id": path.stem,
                            "messages": result[0],
                            "tool_uses": result[1],
                        }
                    )
            except Exception:
                logger.exception(f"Catch-up: failed to import {path.name}")

        logger.info(f"Catch-up: imported {imported} session(s)")

    async def stop(self) -> None:
        """Stop the file watcher."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _watch(self) -> None:
        """Watch loop using watchfiles."""
        try:
            from watchfiles import Change, awatch
        except ImportError:
            logger.warning("watchfiles not installed, file watcher disabled")
            return

        watch_dir = config.CLAUDE_CODE_PROJECTS_DIR
        if not watch_dir.exists():
            logger.warning(f"Watch directory does not exist: {watch_dir}")
            return

        logger.info(f"Watching for changes in {watch_dir}")

        try:
            async for changes in awatch(watch_dir, debounce=int(self.debounce_seconds * 1000)):
                for change_type, path_str in changes:
                    path = Path(path_str)
                    if path.suffix != ".jsonl":
                        continue
                    if change_type in (Change.added, Change.modified):
                        now = time.monotonic()
                        last = self._last_import.get(path_str, 0.0)
                        if now - last < _PER_FILE_COOLDOWN:
                            logger.debug(
                                f"Skipping {path.name} (cooldown, "
                                f"{now - last:.0f}s since last import)"
                            )
                            continue
                        logger.info(f"Detected change: {path.name}")
                        await self._import_session(path)
                        self._last_import[path_str] = time.monotonic()
        except asyncio.CancelledError:
            logger.info("File watcher stopped")
            raise
        except Exception:
            logger.exception("File watcher error")

    async def _import_session(self, path: Path) -> None:
        """Import a single session file in a thread executor."""
        from claude_code_analytics.api.services.import_service import import_single_session

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, import_single_session, path)
            if result:
                await self.event_bus.publish(
                    {
                        "type": "session_imported",
                        "session_id": path.stem,
                        "messages": result[0],
                        "tool_uses": result[1],
                    }
                )
        except Exception:
            logger.exception(f"Failed to import session {path.name}")
