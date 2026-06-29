# app/core/websocket.py
import asyncio
import json
import logging
from typing import Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSHub:
    """
    Central WebSocket hub managing the single detector and single guard connection.
    Holds pending detection in memory — nothing is written to DB until guard confirms.
    """

    def __init__(self):
        self.detector_ws: Optional[WebSocket] = None
        self.guard_ws: Optional[WebSocket] = None

        # In-memory pending detection — cleared on confirm or timeout
        self.pending_detection: Optional[dict] = None

        # Detection enabled flag
        self.enabled: bool = True

        # Auto-resume timeout task
        self._timeout_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ #
    #  Detector Connection                                                 #
    # ------------------------------------------------------------------ #

    async def connect_detector(self, ws: WebSocket):
        await ws.accept()
        self.detector_ws = ws
        logger.info("Detector connected.")

        # Sync current state to detector immediately on connect
        await self._send_detector({
            "type": "sync",
            "enabled": self.enabled
        })

        # If there's a pending detection (detector restarted mid-session)
        # keep the detector blocked — sync already sent enabled=False above

    async def disconnect_detector(self):
        self.detector_ws = None
        logger.warning("Detector disconnected.")

        # Notify guard UI that detector went offline
        await self._send_guard({"type": "detector_status", "online": False})

    # ------------------------------------------------------------------ #
    #  Guard Connection                                                    #
    # ------------------------------------------------------------------ #

    async def connect_guard(self, ws: WebSocket):
        
        await ws.accept()
        self.guard_ws = ws
        logger.info("Guard connected.")

        # Notify guard of detector status
        await self._send_guard({
            "type": "detector_status",
            "online": self.detector_ws is not None
        })

        # If there's a pending detection the guard missed (page refresh), replay it
        if self.pending_detection:
            logger.info("Replaying pending detection to reconnected guard.")
            await self._send_guard({
                "type": "detection",
                **self.pending_detection
            })

    async def disconnect_guard(self):
        self.guard_ws = None
        logger.warning("Guard disconnected.")

    # ------------------------------------------------------------------ #
    #  Detection Flow                                                      #
    # ------------------------------------------------------------------ #

    async def handle_detection(self, data: dict):
        """
        Called when detector sends a detection message.
        - Pauses detector
        - Holds data in memory
        - Pushes to guard UI with owner lookup result attached
        """
        plate = data.get("plate", "")
        direction = data.get("direction", "entry")
        image_b64 = data.get("image_b64")

        # Store pending detection in memory (no DB write)
        self.pending_detection = {
            "plate": plate,
            "direction": direction,
            "image_b64": image_b64,
        }

        # Pause detector
        await self._set_enabled(False)

        # Push to guard UI — owner lookup is done in the router
        # (router has DB session access, hub does not)
        # The router will call push_detection_to_guard() with owner attached
        logger.info(f"Detection received: [{plate}] direction={direction}")

    async def push_detection_to_guard(self, plate: str, direction: str, image_b64: Optional[str], owner: Optional[dict]):
        """
        Called by router after owner lookup — pushes full detection payload to guard.
        Starts auto-resume timeout.
        """
        payload = {
            "type": "detection",
            "plate": plate,
            "direction": direction,
            "image_b64": image_b64,
            "owner": owner,  # None if not found — guard fills in manually
        }

        # Update pending with owner info
        if self.pending_detection:
            self.pending_detection["owner"] = owner

        await self._send_guard(payload)

        # Start 60s auto-resume timeout
        self._cancel_timeout()
        self._timeout_task = asyncio.create_task(self._auto_resume_after_timeout(60))

    # ------------------------------------------------------------------ #
    #  Resume Flow                                                         #
    # ------------------------------------------------------------------ #

    async def resume(self):
        """
        Called after guard confirms — resumes detector and clears pending state.
        """
        self._cancel_timeout()
        self.pending_detection = None
        await self._set_enabled(True)
        logger.info("Detection resumed after guard confirmation.")

    async def _auto_resume_after_timeout(self, seconds: int):
        """
        Auto-resumes detection if guard doesn't act within timeout.
        Silently discards pending detection.
        """
        await asyncio.sleep(seconds)
        logger.warning(f"Guard timeout after {seconds}s — auto-resuming detection.")
        self.pending_detection = None
        await self._set_enabled(True)

    # ------------------------------------------------------------------ #
    #  Internal Helpers                                                    #
    # ------------------------------------------------------------------ #

    async def _set_enabled(self, enabled: bool):
        self.enabled = enabled
        await self._send_detector({"type": "resume" if enabled else "pause"})

    async def _send_detector(self, data: dict):
        if self.detector_ws:
            try:
                await self.detector_ws.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to detector: {e}")
                await self.disconnect_detector()

    async def _send_guard(self, data: dict):
        if self.guard_ws:
            try:
                await self.guard_ws.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to guard: {e}")
                await self.disconnect_guard()

    def _cancel_timeout(self):
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            self._timeout_task = None


# Single shared instance — imported by both routers
ws_hub = WSHub()