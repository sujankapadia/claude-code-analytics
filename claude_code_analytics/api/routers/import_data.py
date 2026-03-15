"""Import endpoints with SSE progress streaming."""

import asyncio
import json

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from claude_code_analytics.api.app import event_bus
from claude_code_analytics.api.services.event_bus import EventBus
from claude_code_analytics.api.services.import_service import run_import

router = APIRouter(tags=["import"])


@router.post("/import")
async def import_conversations():
    """Run a full import with SSE progress events.

    Returns a text/event-stream with progress and completion events.
    """

    async def event_generator():
        # Subscribe to import events
        queue = await event_bus.subscribe()
        try:
            # Start import in background
            asyncio.create_task(_run_and_signal(event_bus, queue))

            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "import_complete":
                    break
        finally:
            await event_bus.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _run_and_signal(bus: EventBus, _queue: asyncio.Queue):
    """Run import and ensure completion event is sent even on error."""
    try:
        await run_import(bus)
    except Exception as e:
        await bus.publish(
            {
                "type": "import_complete",
                "error": str(e),
                "projects": 0,
                "sessions": 0,
                "messages": 0,
                "tool_uses": 0,
            }
        )
