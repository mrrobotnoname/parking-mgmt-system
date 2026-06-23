from typing import List, Dict

from pydantic import BaseModel, field_validator, ValidationInfo

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

class GetSlots(BaseModel):
    slot_id: int
    slot : str
    is_accessible: bool
    is_occupied: bool
    vehicle_type_id:int

class FloorSlotConfig(BaseModel):
    floor_number: int
    total_slots: int
    accessible_slots: int
    vehicle_distribution: Dict[str, int]  # e.g., {"bikes": 20, "cars": 20, "other": 10}

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
            raise ValueError("Number of floor configs must match num_of_floors")
        return v