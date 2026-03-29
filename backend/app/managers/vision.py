import cv2
import torch
from ultralytics import YOLO
import easyocr
import numpy as np

class VisionManager:
    def __int__(self, model_path):
        """Initialize the VisionManager with the specified model path."""
        
        self.model = YOLO(model_path, task="detect")
        self.reader = None
        
    def get_plate_box(self, frame):
        result = self.model.predict(
            source=frame,
            conf=0.5,
            image_size=320,
            device="cpu",
            verbose=False
        )
        if len(result[0].boxes) >0:
            return result[0].boxes.xyxy.cpu().numpy()[0]
        return None
    def extract_text(self, frame, box):
        """crop the image and runs the ORC on the cropped image to extract the text"""
        x1, y1, x2, y2 = map(int, box)
        
        plate_crop = frame[y1:y2, x1:x2]
        
        gray_plate = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
        if self.reader is None:
             print("Initializing EasyOCR reader...")
             self.reader = easyocr.Reader(['en'], gpu=False)
             
        results = self.reader.readtext(gray_plate, detail=0)
        plate_text = "".join(results).upper().replace(" ", "")
        
        return plate_text,plate_crop
    def get_encoded_image(self, image):
        """
        Converts the CV2 crop into a small Base64 string for the Frontend.
        """
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 50])
        import base64
        return base64.b64encode(buffer).decode('utf-8')