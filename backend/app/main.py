from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import init_db
from app.routers.v1 import auth, admin, guard, detector
from dotenv import load_dotenv
import os


load_dotenv(override=True)

app = FastAPI()

ALLOW_ORIGIN = [
    os.getenv("HTTP_URL"),
    os.getenv("WS_URL"),
    os.getenv("WSS_URL")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(admin.router)
app.include_router(detector.router)
app.include_router(guard.router)
