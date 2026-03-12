"""File watcher for auto-importing new conversation sessions."""

import asyncio
import contextlib
import logging
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
        """Start watching for file changes."""
        self._task = asyncio.create_task(self._watch())

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
                        self._last_import[path_str] = now
                        logger.info(f"Detected change: {path.name}")
                        await self._import_session(path)
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
