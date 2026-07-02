# app/routers/v1/detector.py
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.core.websocket import ws_hub
from app.models.owner import Owner
from app.db.session import get_session


router = APIRouter(prefix="/api/v1/detector", tags=["Detector"])
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def detector_ws(ws: WebSocket):
    """
    WebSocket endpoint for the local AI detector.
    - On connect: syncs current enabled state
    - Receives: { type: "detection", plate, direction, image_b64 }
    - Sends:    { type: "sync", enabled } on connect
                { type: "resume" } after guard confirms
                { type: "pause" } when detection fires (defensive, detector already blocked)
    """
    await ws_hub.connect_detector(ws)

    # Notify guard that detector is now online
    await ws_hub._send_guard({"type": "detector_status", "online": True})

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "detection":
                # Step 1 — store in memory, pause detector
                await ws_hub.handle_detection(data)

                # Step 2 — owner lookup (needs DB)
                plate = data.get("plate", "")

                await ws_hub.push_detection_to_guard(
                    plate=plate,
                    direction=data.get("direction", "entry"),
                    image_b64=data.get("image_b64"),
                )

    except WebSocketDisconnect:
        await ws_hub.disconnect_detector()
    except Exception as e:
        logger.error(f"Detector WS error: {e}", exc_info=True)
        await ws_hub.disconnect_detector()
