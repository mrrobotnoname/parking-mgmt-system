

from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.owner import Owner


class ParkingLog(SQLModel, table=True):
    """
    Tracks every single check-in and check-out transaction.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    vehicle_plate: str = Field(index=True)
    name:str
    phone_number: Optional[str] = Field(default=None)
    check_in_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    check_out_time: Optional[datetime] = Field(default=None)
    fee_charged: Optional[float] = Field(default=None)
    payment_method: Optional[str] = Field(default=None)
    payment_status: Optional[str] = Field(default=None)
    is_active:bool

    slot_id: int = Field(foreign_key="parkingslot.id")
    vehicle_id: int = Field(foreign_key="vehicletype.vehicle_id")
    
    owner_id: Optional[int] = Field(default=None, foreign_key="owner.id")


    owner: Optional["Owner"] = Relationship(back_populates="logs")
