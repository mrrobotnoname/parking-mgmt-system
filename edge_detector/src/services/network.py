# src/services/network.py
import httpx
import cv2
import logging
import os
from config.settings import BACKEND_URL

class CloudNetworkDispatcher:
    def __init__(self):
        # Industrial persistent client connection pool
        self.client = httpx.AsyncClient(timeout=10.0,trust_env=False)

    async def send_to_backend(self, plate_text: str, direction: str, cropped_img):
        """Transmits the extracted plate data to the cloud FastAPI backend."""
        
        if cropped_img is None or cropped_img.size == 0:
            logging.error("❌ Network Dispatcher received an empty or invalid image crop. Skipping save.")
            return


        _, buffer = cv2.imencode('.jpg', cropped_img)
        img_bytes = buffer.tobytes()

        payload = {
            "plate": plate_text,
            "direction": direction
        }
        files = {
            "image": ("plate.jpg", img_bytes, "image/jpeg")
        }

        logging.info(f"Transmitting Event payload to Cloud Server -> "
                     f"Box: {plate_text} | Dir: {direction}")
        
        try:
            # This request holds the Edge Node execution process until the cloud backend responds
            response = await self.client.post(BACKEND_URL, data=payload, files=files)
            
            if response.status_code == 200:
                logging.info("✅ Cloud Verification Complete. Remote gate authorized.")
            else:
                logging.error(f"⚠️ Server returned error response status: {response.status_code}")
        except Exception as e:
            logging.critical(f"❌ Network unreachable connection timeout error: {e}")