from typing import List,Optional

from sqlmodel import Field, SQLModel, Relationship

from app.models.slot import ParkingSlot
from app.models.pricing import Pricing


class VehicleType(SQLModel, tabel=True):
    vehicle_id: int | None = Field(default=None, primary_key=True)
    vehicle_type: str = Field(nullable=False, unique=True)
    slots: List["ParkingSlot"] = Relationship(back_populates="vehicle")

    pricing: Optional[Pricing] = Relationship(back_populates="vehicle_type")