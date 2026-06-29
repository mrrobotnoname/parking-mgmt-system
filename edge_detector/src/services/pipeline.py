# src/services/pipeline.py
import asyncio
from datetime import datetime, timezone
import logging
import cv2
import numpy as np
from src.state import ApplicationState
from src.services.motion import MotionShieldService
from src.services.detector import PlateDetectorService
from src.services.ocr import OcrService
# Your new single-websocket dispatcher
from src.services.network import CloudNetworkDispatcher
from config.settings import BACKEND_WS_URL


async def processing_pipeline_loop(
    state: ApplicationState,
    detector: PlateDetectorService,
    ocr: OcrService
):
    motion_shield = MotionShieldService()

    # 1. Initialize our single WebSocket network dispatcher pointing to the camera client endpoint

    network = CloudNetworkDispatcher(ws_url=BACKEND_WS_URL)

    logging.info("Detection loop started. Connecting network socket...")
    try:
        await network.connect()
    except Exception as e:
        logging.error(
            f"Initial backend connection failed, loop will attempt reconnecting: {e}")

    while True:
        # State Gatekeeper check
        if state.system_mode == "BLOCKED":
            await asyncio.sleep(0.5)
            continue

        frame = state.current_frame
        if frame is None:
            await asyncio.sleep(0.1)
            continue

        # Light Motion Shield Check
        if not motion_shield.has_movement(frame):
            await asyncio.sleep(0.1)
            continue

        # Physical motion confirmed, run vehicle identification
        plate_spotted, box, crop = detector.detect_dominant_vehicle(
            frame, state)

        if plate_spotted:
            if state.is_same_vehicle(box):
                state.add_box_to_history(box)
                state.update_vehicle_location(box)

                # 2. Tracking threshold hit: halt the loop and contact the guard
                if len(state.box_area_history) >= 3:
                    direction = state.calculate_direction()

                    # Run light OCR pre-processing steps
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    processed_crop = clahe.apply(gray)

                    text = ocr.extract_text(processed_crop)

                    logging.warning(
                        f"🚨 VEHICLE SPOTTED: [{text}] driving {direction}. Halting pipeline...")
                    state.system_mode = "BLOCKED"
                    state.pending_plate = text

                    try:
                        # 3. THIS IS THE CONNECTION POINT.
                        # This line single-handedly sends the message, waits for the guard, or times out after 1 min.
                        decision = await network.send_detection_and_wait(
                            plate=text,
                            direction=direction,
                            crop=crop
                        )

                        status = decision.get("status")
                        if status == "TIMEOUT_AUTO_RESUME":
                            logging.warning("Pipeline auto-resumed after guard timeout.")
                        else:
                            logging.info(f"Pipeline unblocked. Guard resolution status: {status}")

                    except Exception as exc:
                        logging.error(f"Network processing failed: {exc}")
                    finally:
                        # 4. Cleanup and resume frame processing parameters
                        state.system_mode = "MONITORING"
                        state.reset_tracking()
                else:
                    await asyncio.sleep(0.05)
            else:
                state.add_box_to_history(box)
                state.update_vehicle_location(box)
                await asyncio.sleep(0.05)
        else:
            if state.last_plate_location is not None:
                state.reset_tracking()
            await asyncio.sleep(0.3)