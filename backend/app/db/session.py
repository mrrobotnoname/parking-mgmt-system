
from pathlib import Path
from sqlalchemy import inspect, text
from sqlmodel import Session,create_engine,SQLModel
from app import models

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR/ "parking.db"
DB_URI:str =f"sqlite:///{DB_PATH}"



engine = create_engine(DB_URI,connect_args={"check_same_thread": False})

def init_db():
    "Create the table if the tables alredy not in the database"
    SQLModel.metadata.create_all(engine)
    ensure_runtime_columns()

def ensure_runtime_columns():
    inspector = inspect(engine)
    if "parkinglog" in inspector.get_table_names():
        parking_log_columns = {column["name"] for column in inspector.get_columns("parkinglog")}
        with engine.begin() as connection:
            if "payment_method" not in parking_log_columns:
                connection.execute(text("ALTER TABLE parkinglog ADD COLUMN payment_method VARCHAR"))
            if "payment_status" not in parking_log_columns:
                connection.execute(text("ALTER TABLE parkinglog ADD COLUMN payment_status VARCHAR"))
    if "owner" in inspector.get_table_names():
        owner_columns = {column["name"] for column in inspector.get_columns("owner")}
        with engine.begin() as connection:
            if "vehicle_type_id" not in owner_columns:
                connection.execute(text("ALTER TABLE owner ADD COLUMN vehicle_type_id INTEGER"))

def get_session():
    """FastAPI Dependency to provide an isolated database transaction per request."""
    with Session(engine) as session:
        yield session
