# config/settings.py
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(override=True)


# ==== MODEL PARTH =======

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_MODEL_PATH = os.getenv("MODEL_PATH")
MODEL_PATH = str(BASE_DIR / RAW_MODEL_PATH)

# === STREAM CONFIGURATION ===
# Dev Mode (Video File):
VIDEO_SOURCE = os.getenv("CAMERA_URL")
IS_LIVE_STREAM = True

# Production Mode (Uncomment when deploying to physical gate):
# VIDEO_SOURCE = "rtsp://admin:Password123@192.168.1.150:554/h264/ch1/main/av_stream"
# IS_LIVE_STREAM = True

# === CLOUD BACKEND CONFIGURATION ===
BACKEND_URL = os.getenv("BACKEND_URL")

# === REGION OF INTEREST (ROI) FILTERS ===
# Normalized percentages (0.0 to 1.0) relative to any camera resolution
ROI_X_MIN = 0.15
ROI_Y_MIN = 0.20
ROI_X_MAX = 0.85
ROI_Y_MAX = 0.90