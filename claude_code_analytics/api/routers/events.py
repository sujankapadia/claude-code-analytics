"""Server-Sent Events stream endpoint."""

import asyncio
import json

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from claude_code_analytics.api.app import event_bus

router = APIRouter(tags=["events"])


@router.get("/events")
async def event_stream():
    """SSE stream of real-time events (session imports, etc.)."""

    async def generator():
        queue = await event_bus.subscribe()
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await event_bus.unsubscribe(queue)

    return StreamingResponse(generator(), media_type="text/event-stream")
