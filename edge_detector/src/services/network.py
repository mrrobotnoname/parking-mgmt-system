# src/services/network.py
import asyncio
import base64
import json
import logging
import cv2
import websockets
from websockets.exceptions import ConnectionClosed

RETRY_DELAYS = [2, 5, 10, 30]  # seconds between reconnect attempts


class CloudNetworkDispatcher:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.websocket = None
        self._decision_future: asyncio.Future | None = None
        self._listener_task: asyncio.Task | None = None

    # ------------------------------------------------------------------ #
    #  Connection                                                          #
    # ------------------------------------------------------------------ #

    async def connect(self):
        """Connect to server with retry backoff. Starts persistent listener."""
        for attempt, delay in enumerate(RETRY_DELAYS + [60]):
            try:
                logging.info(f"Connecting to backend (attempt {attempt + 1}): {self.ws_url}")
                self.websocket = await websockets.connect(self.ws_url)
                logging.info("Backend connection established.")

                # Start persistent inbound listener
                if self._listener_task:
                    self._listener_task.cancel()
                self._listener_task = asyncio.create_task(self._persistent_listener())
                return

            except Exception as e:
                logging.warning(f"Connection failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)

        logging.error("Could not connect to backend after all retries.")

    async def _reconnect(self):
        """Called when connection drops unexpectedly."""
        logging.warning("Backend disconnected. Attempting reconnect...")
        await self.connect()

    # ------------------------------------------------------------------ #
    #  Persistent Listener                                                 #
    # ------------------------------------------------------------------ #

    async def _persistent_listener(self):
        """
        Always-on inbound reader. Handles both:
        - sync messages on connect
        - resume messages after guard confirms
        """
        try:
            async for raw in self.websocket:
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "sync":
                    # Server tells us current enabled state on connect
                    enabled = data.get("enabled", True)
                    logging.info(f"Sync received from server. Detection enabled: {enabled}")
                    # If server says we're still blocked (e.g. after detector restart
                    # mid-session), the pipeline's BLOCKED state already handles it.
                    # Nothing to do here unless you want to force-resume:
                    if enabled and self._decision_future and not self._decision_future.done():
                        self._decision_future.set_result({"status": "SYNC_RESUME"})

                elif msg_type == "resume":
                    logging.info("Resume signal received from server.")
                    if self._decision_future and not self._decision_future.done():
                        self._decision_future.set_result({"status": "CONFIRMED"})

        except ConnectionClosed:
            logging.warning("WebSocket connection closed.")
            await self._reconnect()
        except Exception as e:
            logging.error(f"Listener error: {e}", exc_info=True)
            await self._reconnect()

    # ------------------------------------------------------------------ #
    #  Detection                                                           #
    # ------------------------------------------------------------------ #

    async def send_detection_and_wait(self, plate: str, direction: str, crop) -> dict:
        """
        Sends detection payload to server, blocks pipeline,
        waits for resume signal or timeout.
        """
        if not self.websocket or self.websocket.close_code is None:
            await self._reconnect()

        # Encode image
        _, buffer = cv2.imencode('.jpg', crop)
        image_b64 = base64.b64encode(buffer).decode('utf-8')

        # Set up future — persistent listener will resolve it
        self._decision_future = asyncio.get_running_loop().create_future()

        payload = {
            "type": "detection",
            "plate": plate,
            "direction": direction,
            "image_b64": image_b64
        }

        await self.websocket.send(json.dumps(payload))
        logging.info(f"Detection sent [{plate} / {direction}]. Pipeline halted, awaiting guard...")

        try:
            decision = await asyncio.wait_for(
                asyncio.shield(self._decision_future),
                timeout=60.0
            )
            logging.info(f"Pipeline unblocked. Status: {decision.get('status')}")
            return decision

        except asyncio.TimeoutError:
            logging.warning("No guard response within 60s. Auto-resuming.")
            return {"status": "TIMEOUT_AUTO_RESUME"}

        finally:
            self._decision_future = None