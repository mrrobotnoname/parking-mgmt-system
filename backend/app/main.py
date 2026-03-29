import _asyncio
from fastapi import FastAPI
from contextlib import contextmanager
from .managers.vision import VisionManager



@contextmanager
async def lifespan(app: FastAPI):
    print("Loading the Model")
    vision = VisionManager(model_path="../best_openvino_model")
    yield
    
    print("sutting down")

app = FastAPI(lifespan=lifespan)

    