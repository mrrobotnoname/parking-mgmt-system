from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel, field_validator, ValidationInfo
from sqlmodel import Field

# Object model for guards


class Guard(BaseModel):
    username: str
    password: str
    name: str
    phone_number: str


class GuardRespond(BaseModel):
    user_id: int
    username: str
    name: str
    phone_number: str


class GuardUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    name: str | None = None
    phone_number: str | None = None


# Vehicle_type


class Vehicle(BaseModel):
    vehicle_id: int | None = None
    vehicle_type: str | None = None


# Slots

class SlotResponse(BaseModel):
    slot_id: int
    slot_number: int
    floor: Optional[str]
    display_slot: str
    is_occupied: bool
    is_accessible: bool
    vehicle_type_id: int
    vehicle_type: str
    occupant_plate: Optional[str] = None
    occupant_name: Optional[str] = None
    occupant_phone: Optional[str] = None
    check_in_time: Optional[datetime] = None

class FloorSlotConfig(BaseModel):
    floor_number: int
    total_slots: int
    accessible_slots: int
    # e.g., {"bikes": 20, "cars": 20, "other": 10}
    vehicle_distribution: Dict[str, int]


class ParkingGridSetup(BaseModel):
    num_of_floors: int
    floors_config: List[FloorSlotConfig]

    @field_validator('num_of_floors')
    def validate_floors(cls, v):
        if v < 1:
            raise ValueError("Number of floors must be at least 1")
        return v

    @field_validator('floors_config')
    def validate_floor_count(cls, v, info: ValidationInfo):
        data = info.data or {}
        if 'num_of_floors' in data and len(v) != data['num_of_floors']:
            raise ValueError(
                "Number of floor configs must match num_of_floors")
        return v


class UpdatePricingRequest(BaseModel):
    hourly_rate: float = Field(
        ...,
        description="The hourly rate charged for the vehicle type.",
        gt=0.0
    )
    fixed_rate: float = Field(
        ...,
        description="The maximum capped/fixed rate for the rental.",
        gt=0.0
    )
    threshold_minutes: int = Field(
        ...,
        description="The duration threshold in minutes where pricing transitions from hourly to fixed.",
        ge=0
    )


class ConfirmPayload(BaseModel):          
    plate: str
    name:str
    phone_number:str
    slot_id:int
    vehicle_type_id: int


class OwnerResponse(BaseModel):
    name:str
    phone_number:str
    vehicle:str
    plate_number:str

class OwnerRequest(BaseModel):
    name:str
    plate_number:str
    phone_number:str
    vehicle_type_id:int

