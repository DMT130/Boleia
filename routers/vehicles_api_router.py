from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
from database import get_db
import models as routers
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from routers.user_auth_api_router import get_current_active_user, check_admin_rights, get_current_user

router = APIRouter()

@router.post("/vehicles/", response_model=schemas.VehiclePublic, status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle: schemas.VehicleCreate, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    #vehicle['owner_id'] = current_user.id
    db_vehicle = routers.Vehicle(**vehicle.dict(), owner_id=current_user.id)
    try:
        db.add(db_vehicle)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/vehicles/", response_model=List[schemas.VehiclePublic])
def read_vehicles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User=Depends(check_admin_rights)):
    try:
        vehicles = db.query(routers.Vehicle).offset(skip).limit(limit).all()
        return vehicles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/vehicles/{vehicle_id}", response_model=schemas.VehiclePublic)
def read_vehicle(vehicle_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    try:
        db_vehicle = db.query(routers.Vehicle).filter(routers.Vehicle.id == vehicle_id).first()
        if db_vehicle is None:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        if current_user.id != db_vehicle.owner_id:
            raise HTTPException(status_code=403, detail="You can only get data from your vehicle")
        return db_vehicle
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/vehicles/{vehicle_id}", response_model=schemas.VehiclePublic)
def update_vehicle(vehicle_id: int, vehicle: schemas.VehicleUpdate, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    db_vehicle = db.query(routers.Vehicle).filter(routers.Vehicle.id == vehicle_id).first()
    if db_vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if current_user.id != db_vehicle.owner_id:
        raise HTTPException(status_code=403, detail="You can only update data from your vehicle")
    vehicle_data = vehicle.dict(exclude_unset=True)
    for key, value in vehicle_data.items():
        setattr(db_vehicle, key, value)

    try:
        db.add(db_vehicle)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/vehicles/{vehicle_id}", response_model=dict)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    db_vehicle = db.query(routers.Vehicle).filter(routers.Vehicle.id == vehicle_id).first()
    if db_vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if current_user.id != db_vehicle.owner_id:
        raise HTTPException(status_code=403, detail="You can only update data from your vehicle")
    try:
        db.delete(db_vehicle)
        db.commit()
        return {"message": "Vehicle deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")