from typing import List, Optional,TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship


if TYPE_CHECKING:
    from app.models.pricing import Pricing
    from app.models.slot import ParkingSlot
    from backend.app.models.owner import Owner

class VehicleType(SQLModel, table=True):
    vehicle_id: int | None = Field(default=None, primary_key=True)
    vehicle_type: str = Field(nullable=False, unique=True)
    

    owners: List["Owner"] = Relationship(back_populates="vehicle_type")
    slots: List["ParkingSlot"] = Relationship(back_populates="vehicle_type")
    pricing: Optional["Pricing"] = Relationship(back_populates="vehicle_type")