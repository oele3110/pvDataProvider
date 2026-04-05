import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, status

from api.auth import decode_token
from api.models import LiveDataPayload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_live(websocket: WebSocket) -> None:
    # Token is passed as a query parameter because the browser WebSocket API
    # does not support custom headers: ws://host/ws?token=<jwt>
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")

    try:
        username = decode_token(token)
    except Exception:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")

    await websocket.accept()
    logger.info("WebSocket client connected: user='%s' remote=%s", username, websocket.client)

    collector = websocket.app.state.collector
    try:
        while True:
            payload = LiveDataPayload(
                timestamp=datetime.now(timezone.utc),
                data=collector.get_live_data(),
            )
            await websocket.send_text(payload.model_dump_json())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: user='%s'", username)
    except Exception:
        logger.exception("WebSocket error for user='%s'", username)
