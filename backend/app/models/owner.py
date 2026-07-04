from typing import Optional, List,TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


if TYPE_CHECKING:
    from app.models.parking_log import ParkingLog
    from backend.app.models.vehicle_type import VehicleType


class Owner(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    plate_number: str = Field(unique=True, index=True)
    vehicle_type_id: Optional[int] = Field(default=None, foreign_key="vehicletype.vehicle_id")
    
    phone_number: str = Field(index=True) 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    vehicle_type: Optional["VehicleType"] = Relationship(back_populates="owners")
    logs: List["ParkingLog"] = Relationship(back_populates="owner")

