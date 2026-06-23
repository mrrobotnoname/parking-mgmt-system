from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from typing import List


from app.routers.deps import isAdmin
from app.db.session import get_session
from app.core.security import validate_password, encryptPassword

from app.models.user import User
from app.models.vehicle_type import VehicleType
from app.core.base import GetSlots, Guard, GuardRespond, GuardUpdate, Vehicle, ParkingGridSetup, FloorSlotConfig
from app.models.slot import ParkingSlot


router = APIRouter(
    prefix="/api/v1/admin",
    dependencies=[Depends(isAdmin)]
)


@router.get("/")
def admin():
    return "welcom to the admin"


# =============================================Guard haddling fucntions ===========================================
# ===== Create the guard acoount ====
@router.post("/guard/add")
def create_guard_account(data: Guard, db: Session = Depends(get_session)):
    user = db.exec(select(User)
                   .where(User.username == data.username)
                   .where(User.role == "guard")).first()

    # username validation
    if user and user is not None:
        raise HTTPException(status_code=409, detail="username already taken")

    # password validation
    if not validate_password(data.password):
        raise HTTPException(
            status_code=400,
            detail="Password is not strong please enter another password"
        )

    new_user = User(
        username=data.username,
        password=encryptPassword(data.password),
        name=data.name,
        phone_number=data.phone_number,
        role="guard"
    )
    try:
        db.add(new_user)
        db.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=409, detail="phone number should be unique")

    return f"Guard:{data.name} added to the system."

# ====== get all the guard acoounts ====


@router.get("/guards", response_model=List[GuardRespond])
def get_guards(db: Session = Depends(get_session)):
    guards: tuple = db.exec(select(User).where(User.role == "guard")).all()
    return guards

# === delete the guard accounts


@router.delete("/guard/{guard_id}")
def deleteGuard(guard_id: int, db: Session = Depends(get_session)):
    result = db.exec(select(User).where(User.role == "guard").where(
        User.user_id == guard_id)).first()

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Guard not found"
        )

    db.delete(result)
    db.commit()
    return {
        "message": f"Guard: {result.username} was deleted successfuly!"
    }


# ==== modify guard accounts =======
@router.patch("/guard/{guard_id}")
def editGuard(
    data: GuardUpdate,
    guard_id: int,
    db: Session = Depends(get_session)
):
    guard = db.exec(select(User).where(
        User.user_id == guard_id).where(User.role == "guard")).first()

    if not guard:
        raise HTTPException(
            status_code=404,
            detail="No guard found!"
        )
    if data.username is not None:
        exsist = db.exec(select(User).where(
            User.username == data.username)).first()

        if exsist:
            raise HTTPException(
                status_code=409,
                detail="username already taken."
            )
        guard.username = data.username
    if data.name is not None:
        guard.name = data.name

    if data.password is not None:
        if not validate_password(data.password):
            return {
                "message": "The password is too week try another one!"
            }
        guard.password = encryptPassword(data.password)
    if data.phone_number is not None:
        exsist = db.exec(select(User).where(
            User.phone_number == data.phone_number).where(User.role == "guard")).first()

        if exsist is not None:
            raise HTTPException(
                code=409,
                detail="phone number already exist"
            )
        guard.phone_number = data.phone_number
    try:
        db.add(guard)
        db.commit()
        db.refresh(guard)
        return "update successfuly"
    except:
        return "Somthing went wrong please try again"


# ==================================================================================

# ===================== Vehicle & Pricing Configuration ===================

@router.get("/vehicle-types", response_model=List[Vehicle])
def getVehicle(db: Session = Depends(get_session)):

    vehicle = db.exec(select(VehicleType)).all()

    return vehicle


@router.post("/vehicle-types")
def addVehicle(data: Vehicle, db: Session = Depends(get_session)):
    exist = db.exec(select(VehicleType)
                    .where(VehicleType.vehicle_type == data.vehicle_type)).first()

    if exist:
        raise HTTPException(
            status_code=404,
            detail="vehicle type alredy exist."
        )
    vehicle = VehicleType(vehicle_type=data.vehicle_type)
    db.add(vehicle)
    db.commit()

    return {
        "message": f"{data.vehicle_type} added to the system."
    }


@router.delete("/vehicle-types/{vehicle_id}")
def deleteVehicle(vehicle_id: int, db: Session = Depends(get_session)):

    vehicle = db.get(VehicleType, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=404,
            details="Vehicle not found!"
        )
    db.delete(vehicle)
    db.commit()
    return {
        "message": f"{vehicle.vehicle_type} was deleted."
    }

# ==================================================================================

# ================ Parking slot managemet =======================#

@router.get("/parking-grid",response_model=List[GetSlots])
def getSlots(db:Session=Depends(get_session)):

    slots = db.exec(select(ParkingSlot)).all()

    if not slots:
        raise HTTPException(
            status_code=404,
            detail="No parking slots are configured."
        )

    # Map DB models to the response shape expected by GetSlots
    result = [
        {
            "slot_id": s.id,
            "slot": s.display_slot,
            "is_accessible": s.is_accessible,
            "is_occupied": s.is_occupied,
            "vehicle_type_id": s.vehicle_type_id
        }
        for s in slots
    ]
    return result


@router.post("/parking-grid")
def setup_parking_grid(data: ParkingGridSetup, db: Session = Depends(get_session)):
    """
    Setup the entire parking grid with floors and slots.
    
    Process:
    1. Slots 1 to accessible_slots: Accessible (disabled people)
    2. Next slots: Distributed by vehicle type
    
    Example:
    Floor 1: 60 total slots, 10 accessible
    - Slots 1-10: Accessible
    - Slots 11-30: Bikes (20)
    - Slots 31-50: Cars (20)
    - Slots 51-60: Other (10)
    """
    try:
        # Check if slots already exist
        existing_slots = db.exec(select(ParkingSlot)).first()
        if existing_slots:
            raise HTTPException(
                status_code=400,
                detail="Parking grid already exists. Delete existing slots first."
            )
        
        total_slots_created = 0
        
        # Process each floor
        for floor_config in data.floors_config:
            floor_num = floor_config.floor_number
            total_slots = floor_config.total_slots
            accessible_slots = floor_config.accessible_slots
            vehicle_dist = floor_config.vehicle_distribution
            
            # Validate: accessible + vehicle slots = total slots
            vehicle_slots_sum = sum(vehicle_dist.values())
            if accessible_slots + vehicle_slots_sum != total_slots:
                raise HTTPException(
                    status_code=400,
                    detail=f"Floor {floor_num}: Accessible ({accessible_slots}) + Vehicle slots ({vehicle_slots_sum}) must equal total slots ({total_slots})"
                )
            
            # Create floor identifier
            floor_id = f"F{floor_num}"
            
            # 1. Create accessible slots (1 to accessible_slots)
            for slot_num in range(1, accessible_slots + 1):
                # Get a default vehicle type for accessible slots (first available)
                default_vehicle = db.exec(select(VehicleType)).first()
                if not default_vehicle:
                    raise HTTPException(
                        status_code=400,
                        detail="No vehicle types defined. Please add vehicle types first."
                    )
                
                slot = ParkingSlot(
                    floor=floor_id,
                    slot_number=slot_num,
                    is_accessible=True,
                    is_occupied=False,
                    vehicle_type_id=default_vehicle.vehicle_id
                )
                db.add(slot)
                total_slots_created += 1
            
            # 2. Create vehicle type slots
            current_slot_num = accessible_slots + 1
            
            for vehicle_type_name, num_slots in vehicle_dist.items():
                # Get vehicle type ID
                vehicle_type = db.exec(
                    select(VehicleType).where(
                        VehicleType.vehicle_type == vehicle_type_name
                    )
                ).first()
                
                if not vehicle_type:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Vehicle type '{vehicle_type_name}' not found. Please add it first."
                    )
                
                # Create slots for this vehicle type
                for i in range(num_slots):
                    slot = ParkingSlot(
                        floor=floor_id,
                        slot_number=current_slot_num,
                        is_accessible=False,
                        is_occupied=False,
                        vehicle_type_id=vehicle_type.vehicle_id
                    )
                    db.add(slot)
                    current_slot_num += 1
                    total_slots_created += 1
        
        # Commit all slots
        db.commit()
        
        return {
            "message": f"Parking grid setup completed successfully!",
            "num_floors": data.num_of_floors,
            "total_slots_created": total_slots_created,
            "details": {
                f"Floor {config.floor_number}": {
                    "total_slots": config.total_slots,
                    "accessible": config.accessible_slots,
                    "vehicle_distribution": config.vehicle_distribution
                }
                for config in data.floors_config
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error setting up parking grid: {str(e)}"
        )


@router.delete("/parking-grid/clear")
def clear_parking_grid(db: Session = Depends(get_session)):
    """
    Delete all parking slots. Use this before reconfiguring the grid.
    """
    try:
        slots = db.exec(select(ParkingSlot)).all()
        
        if not slots:
            raise HTTPException(
                status_code=404,
                detail="No parking slots to delete."
            )
        
        num_slots = len(slots)
        for slot in slots:
            db.delete(slot)
        
        db.commit()
        
        return {
            "message": f"Parking grid cleared successfully!",
            "slots_deleted": num_slots
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing parking grid: {str(e)}"
        )


@router.get("/parking-grid/template")
def parking_grid_template(db: Session = Depends(get_session)):
    """Return available vehicle types and a default parking-grid template for the UI.
    """
    try:
        vehicle_types = db.exec(select(VehicleType)).all()
        v_names = [v.vehicle_type for v in vehicle_types]

        template = {
            "num_of_floors": 1,
            "floors_config": [
                {
                    "floor_number": 1,
                    "total_slots": 0,
                    "accessible_slots": 0,
                    "vehicle_distribution": {name: 0 for name in v_names}
                }
            ]
        }

        return {"vehicle_types": v_names, "template": template}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building template: {str(e)}")

