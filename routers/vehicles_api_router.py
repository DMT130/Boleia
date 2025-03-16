from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
import os
from pathlib import Path
from uuid import uuid4
from database import get_db
import models as routers
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from routers.user_auth_api_router import get_current_active_user, check_admin_rights, get_current_user

UPLOAD_CAR_PICTURES_DIR = "CarPictures"
UPLOAD_CAR_INSURANCE_DIR = "CarInsurance"
UPLOAD_CAR_OWNERSHIP_DIR = "CarOwnership"
UPLOAD_CAR_REGISTRACTION_DIR = "CarRegistraction"
os.makedirs(UPLOAD_CAR_PICTURES_DIR, exist_ok=True)
os.makedirs(UPLOAD_CAR_INSURANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_CAR_OWNERSHIP_DIR, exist_ok=True)
os.makedirs(UPLOAD_CAR_REGISTRACTION_DIR, exist_ok=True)

router = APIRouter()

@router.post("/vehicles/", response_model=schemas.VehiclePublic, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    make: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    color: str = Form(...),
    license_plate: str = Form(...),
    capacity: int = Form(...),
    engine_size: float = Form(...),
    insurance_document: UploadFile = File(...),
    car_registraction_file: UploadFile = File(...),
    car_owership_file: UploadFile = File(...),
    car_photos: List[UploadFile] = File(...),
    db: Session = Depends(get_db), 
    current_user: schemas.User = Depends(get_current_user)
):
    try:
        # Save the insurance document
        insurance_filename = f"{uuid4()}_{insurance_document.filename}"
        insurance_path = Path(UPLOAD_CAR_INSURANCE_DIR) / insurance_filename
        with open(insurance_path, "wb") as buffer:
            buffer.write(await insurance_document.read())
        insurance_document_url = f"CarInsurance/{insurance_filename}"

        owership_filename = f"{uuid4()}_{car_owership_file.filename}"
        ownership_path = Path(UPLOAD_CAR_OWNERSHIP_DIR) / owership_filename
        with open(ownership_path, "wb") as buffer:
            buffer.write(await car_owership_file.read())
        car_owership_document_url = f"CarOwnership/{owership_filename}"

        registraction_filename = f"{uuid4()}_{car_registraction_file.filename}"
        registraction_path = Path(UPLOAD_CAR_REGISTRACTION_DIR) / registraction_filename
        with open(registraction_path, "wb") as buffer:
            buffer.write(await car_registraction_file.read())
        car_registraction_document_url = f"CarRegistraction/{registraction_filename}"

        # Save car photos
        car_photos_urls = []
        for photo in car_photos:
            filename = f"{uuid4()}_{photo.filename}"
            file_path = Path(UPLOAD_CAR_PICTURES_DIR) / filename
            with open(file_path, "wb") as buffer:
                buffer.write(await photo.read())
            car_photos_urls.append(f"CarPictures/{filename}")

        # Create vehicle entry
        db_vehicle = routers.Vehicle(
            owner_id=current_user.id,
            make=make,
            model=model,
            year=year,
            color=color,
            license_plate=license_plate,
            capacity=capacity,
            engine_size=engine_size,
            car_registraction_file=car_registraction_document_url,
            car_owership_file=car_owership_document_url,
            insurance_document=insurance_document_url,
            car_photos=car_photos_urls  # JSONB-compatible list
        )

        db.add(db_vehicle)
        db.commit()
        db.refresh(db_vehicle)
        return db_vehicle

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

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