# app/routers/v1/guard.py
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.core.websocket import ws_hub
from app.models.owner import Owner
from app.core.base import ConfirmPayload, OwnerRequest, OwnerResponse, SlotResponse, Vehicle
from app.models.slot import ParkingSlot
from app.models.parking_log import ParkingLog
from app.models.pricing import Pricing
from app.db.session import get_session
from app.core.security import ws_authenticate
from app.routers.deps import isGuard
from app.models.vehicle_type import VehicleType


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/guard", tags=["Guard"])

# ------------------------------------------------------------------ #
#  WebSocket — Guard UI                                                #
# ------------------------------------------------------------------ #


@router.websocket("/ws")
async def guard_ws(ws: WebSocket):
    """
    WebSocket endpoint for the Guard UI.
    - On connect: receives detector status + any pending detection (replay)
    - Receives: { type: "confirm", direction, plate, vehicle_type_id, owner_id }
    - Sends:    { type: "detection", plate, direction, image_b64, owner }
                { type: "detector_status", online }
                { type: "resume" } (after confirm saved successfully)
                { type: "error", message } (lot full, no open session, etc.)
    """

    await ws_authenticate(ws)
    await ws_hub.connect_guard(ws)

    try:
        while True:
            await ws.receive_text()

    except WebSocketDisconnect:
        await ws_hub.disconnect_guard()
    except Exception as e:
        logger.error(f"Guard WS error: {e}", exc_info=True)
        await ws_hub.disconnect_guard()


# ------------------------------------------------------------------ #
#  HTTP — Plate Lookup                                     #
# ------------------------------------------------------------------ #

@router.get("/lookup")
async def lookup_plate(plate: str, db: Session = Depends(get_session)):
    """
    Called by guard UI in manual mode when guard types a plate number.
    Returns owner details if found, or found=False if new vehicle.
    """
    owner = db.exec(
        select(Owner).where(Owner.plate_number == plate)
    ).first()

    if owner:
        return {
            "found": True,
            "owner": {
                "id": owner.id,
                "name": owner.name,
                "phone_number": owner.phone_number,
                "vehicle_type_id": owner.vehicle_type_id,
            }
        }

    return {"found": False, "owner": None}


# exit plate lookup
@router.get("/exit/lookup")
async def lookupExit(plate: str, db: Session = Depends(get_session), _: dict = Depends(isGuard)):
    """Read-only. Fires automatically once a valid plate is typed/scanned."""
    log = db.exec(
        select(ParkingLog).where(
            ParkingLog.vehicle_plate == plate,
            ParkingLog.is_active == True
        )
    ).first()

    if not log:
        return {"found": False}

    slot = db.get(ParkingSlot, log.slot_id)
    if not slot or not slot.is_occupied:
        logger.error(
            f"Exit lookup mismatch: plate={plate} slot_id={log.slot_id}")
        return {"found": False, "error": "data_mismatch"}

    vehicle_type = db.get(VehicleType, log.vehicle_id)


    now = _utcnow()

    return {
        "found": True,
        "plate": log.vehicle_plate,
        "name": log.name,
        "vehicle_type": vehicle_type.vehicle_type if vehicle_type else "Unknown",
        "phone_number": log.phone_number if log else None,
        "check_in_time": log.check_in_time,
        "duration_minutes": round((now - log.check_in_time).total_seconds() / 60, 1),
        "slot_id": log.slot_id,
        "display_slot": slot.display_slot,
    }


@router.post("/entry", status_code=status.HTTP_201_CREATED)
async def setParking(
    payload: ConfirmPayload,
    db: Session = Depends(get_session),
    _: dict = Depends(isGuard)
):
    slot = db.get(ParkingSlot, payload.slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.is_occupied = True

    # 2. Create the Session record
    new_session = ParkingLog(
        vehicle_plate=payload.plate,
        name=payload.name,
        phone_number = payload.phone_number,
        check_in_time=_utcnow(),  
        is_active=True,
        vehicle_id=payload.vehicle_type_id,
        slot_id=slot.id,
    )

    db.add(new_session)
    db.add(slot)
    db.commit()

    await ws_hub.resume()

    return {"status": "success"}



@router.get("/assign-slot")
async def previewSlot(vehicle_type_id: int, is_accessible: bool = False, db: Session = Depends(get_session), _: dict = Depends(isGuard)):
    slot = find_available_slot(vehicle_type_id, db, is_accessible)
    if not slot:
        return {"found": False, "slot": None}
    return {"found": True, "slot": {"id": slot.id, "display_slot": slot.display_slot}}


@router.get("/slots", response_model=list[SlotResponse])
async def getParking(_: dict = Depends(isGuard), db: Session = Depends(get_session)):
    slots = db.exec(select(ParkingSlot)).all()
    result = []
    for s in slots:
        log = None
        if s.is_occupied:
            log = db.exec(
                select(ParkingLog).where(
                    ParkingLog.slot_id == s.id,
                    ParkingLog.is_active == True
                )
            ).first()

        result.append(SlotResponse(
            slot_id=s.id,
            slot_number=s.slot_number,
            floor=s.floor,
            display_slot=s.display_slot,
            is_occupied=s.is_occupied,
            is_accessible=s.is_accessible,
            vehicle_type_id=s.vehicle_type_id,
            vehicle_type=s.vehicle_type.vehicle_type if s.vehicle_type else "Unknown",
            occupant_plate=log.vehicle_plate if log else None,
            occupant_name=log.name if log else None,
            occupant_phone=log.phone_number if log else None,
            check_in_time=log.check_in_time if log else None,
        ))
    return result



# ------------------------------------------------------------------ #
#  Exit Logic                                                          #
# ------------------------------------------------------------------ #


@router.get("/exit/calculate")
async def calculateExitFee(plate: str, db: Session = Depends(get_session), _: dict = Depends(isGuard)):
    """Read-only. Fires on the guard's 'Calculate' click."""
    log = db.exec(
        select(ParkingLog).where(
            ParkingLog.vehicle_plate == plate,
            ParkingLog.is_active == True
        )
    ).first()
    if not log:
        raise HTTPException(
            status_code=404, detail="No active session found for this plate")

    now = _utcnow()
    fee = _calculate_fee(log, now, db)
    print(fee)

    log.fee_charged = fee
    log.check_out_time = now

    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "plate": log.vehicle_plate,
        "duration_minutes": round((now - log.check_in_time).total_seconds() / 60, 1),
        "fee": fee,
    }


async def _handle_exit(plate: str, db: Session) -> dict:
    log = db.exec(
        select(ParkingLog).where(
            ParkingLog.vehicle_plate == plate,
            ParkingLog.is_active == True
        )
    ).first()
    if not log:
        raise HTTPException(
            status_code=404, detail="No active session found for this plate")

    slot = db.get(ParkingSlot, log.slot_id)
    if not slot or not slot.is_occupied:
        raise HTTPException(
            status_code=409, detail="Session/slot state mismatch")

    now = _utcnow()

    log.is_active = False
    db.add(log)

    slot.is_occupied = False
    db.add(slot)

    db.commit()
    return{
        "plate": log.vehicle_plate,
        "check_out_time": log.check_out_time,
        "fee": log.fee_charged,
    }


def _calculate_fee(log: ParkingLog, check_out: datetime,db) -> float:
    duration_minutes = (check_out - log.check_in_time).total_seconds() / 60
    pricing = db.exec(select(Pricing).where(
        Pricing.vehicle_type_id == log.vehicle_id)).first()
    if not pricing:
        return 0.0
    if duration_minutes >= pricing.threshold_minutes:
        return round(pricing.fixed_rate, 2)
    price =  round((duration_minutes / 60) * pricing.hourly_rate, 2)
    
    return price if(price>pricing.hourly_rate) else pricing.hourly_rate
    


@router.post("/exit/confirm")
async def confirmExit(plate: str, db: Session = Depends(get_session), _: dict = Depends(isGuard)):
    """Mutating. Same logic _handle_exit uses for the WS/detector path."""
    result = await _handle_exit(plate, db)
    await ws_hub.resume()
    return {"message": "Exit recorded.", **result}


def find_available_slot(
    vehicle_type_id: int,
    db: Session,
    is_accessible_required: bool = False
) -> Optional[ParkingSlot]:

    slot = None

    # 1. If accessible, try to find an accessible slot first
    if is_accessible_required:
        slot = db.exec(
            select(ParkingSlot).where(
                ParkingSlot.is_occupied == False,
                ParkingSlot.is_accessible == True,
                ParkingSlot.vehicle_type_id == vehicle_type_id,
            )
        ).first()

    # 2. If not found (or not requested), look for a normal slot
    if not slot:
        slot = db.exec(
            select(ParkingSlot).where(
                ParkingSlot.is_occupied == False,
                ParkingSlot.is_accessible == False,
                ParkingSlot.vehicle_type_id == vehicle_type_id,
            )
        ).first()

    # 3. Fallback: If still not found, look for any normal slot (regardless of type_id)
    # This matches your original fallback logic
    if not slot:
        slot = db.exec(
            select(ParkingSlot).where(
                ParkingSlot.is_occupied == False,
                ParkingSlot.is_accessible == False,
            )
        ).first()

    return slot



# vehicle data fetching endpoint

@router.get("/vehicles", response_model=List[Vehicle])
def getVehicleTypes(db: Session = Depends(get_session), _: dict = Depends(isGuard)):
    vehicles = db.exec(select(VehicleType)).all()
    return vehicles


#Adiing owners func
@router.get("/daily-users", response_model=List[OwnerResponse])
def getOwners(db=Depends(get_session), _=Depends(isGuard)):
    owners = db.exec(
        select(Owner).options(selectinload(Owner.vehicle_type))
    ).all()
    result = [OwnerResponse(
        name=owner.name,
        phone_number=owner.phone_number,
        vehicle=owner.vehicle_type.vehicle_type if owner.vehicle_type else "Unknown",
        plate_number=owner.plate_number,

    ) for owner in owners]
    return result


@router.post("/daily-users", status_code=status.HTTP_200_OK)
def setOwner(payload: OwnerRequest, db: Session = Depends(get_session), _: dict = Depends(isGuard)):
    owner = Owner(
        name=payload.name,
        plate_number=payload.plate_number,
        vehicle_type_id=payload.vehicle_type,
        phone_number=payload.phone_number

    )

    db.add(owner)
    db.commit()
    return {"message: the owner is added"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


#resume endpoint
@router.post("/resume", status_code=status.HTTP_200_OK)
async def resumeDetector(_: dict = Depends(isGuard)):
    """
    Called by the guard UI when a detection event is denied or skipped.
    Resumes the local AI detector stream.
    """
    await ws_hub.resume()
    return {"status": "success", "message": "Detector stream resumed."}


@router.post("/exit/deny")
async def denyExit(plate: str, db: Session = Depends(get_session), _: dict = Depends(isGuard)):
    """
    Called when a guard denies an exit event.
    Reverts the prematurely saved fee and check-out time back to null, 
    keeping the parking log session active.
    """
    await ws_hub.resume()
    log = db.exec(
        select(ParkingLog).where(
            ParkingLog.vehicle_plate == plate,
            ParkingLog.is_active == True
        )
    ).first()

    if not log:

        raise HTTPException(
            status_code=404, detail="No active session found to revert for this plate"
        )

    # Revert the calculated fields back to null/None
    log.fee_charged = None
    log.check_out_time = None

    db.add(log)
    db.commit()

    # Resume the camera stream

    return {"status": "success", "message": "Database records reverted and detector resumed."}