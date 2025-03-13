from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
from database import get_db
import models as routers
from shapely.wkb import loads as wkb_loads
from sqlalchemy.exc import IntegrityError
from geoalchemy2.shape import to_shape
from shapely.wkb import loads as wkb_loads
from shapely.wkt import loads as wkt_loads, dumps as wkt_dumps

router = APIRouter()

@router.post("/rides/", response_model=schemas.RidePublic, status_code=status.HTTP_201_CREATED)
def create_ride(ride: schemas.RideCreate, db: Session = Depends(get_db)):
    ride_data = ride.dict()
    ride_data['start_location'] = utils.to_wkt(ride_data['start_location'], "POINT")
    ride_data['end_location'] = utils.to_wkt(ride_data['end_location'], "POINT")
    ride_data['waypoints'] = utils.to_wkt(ride_data['waypoints'], "LINESTRING")
    
    db_ride = routers.Ride(**ride_data)

    try:
        db.add(db_ride)
        db.commit()
        db.refresh(db_ride)
        return {
            "id": db_ride.id,
            "start_location": list(to_shape(db_ride.start_location).coords)[0],  # Convert POINT
            "end_location": list(to_shape(db_ride.end_location).coords)[0],  # Convert POINT
            "waypoints": list(to_shape(db_ride.waypoints).coords) if db_ride.waypoints else None,  # Convert LINESTRING
            "departure_time": db_ride.departure_time,
            "available_seats": db_ride.available_seats,
            "price_per_seat": db_ride.price_per_seat,
            "status": db_ride.status,
            "is_recurring": db_ride.is_recurring,
        }
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/rides/", response_model=List[schemas.RidePublic])
def read_rides(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        rides = db.query(routers.Ride).offset(skip).limit(limit).all()
        
        if not rides:
            return []  # Retorna lista vazia se não houver viagens

        return [{
            "id": ride.id,
            "start_location": list(wkb_loads(bytes(ride.start_location.data)).coords)[0],  # Convert POINT
            "end_location": list(wkb_loads(bytes(ride.end_location.data)).coords)[0],  # Convert POINT
            "waypoints": list(wkb_loads(bytes(ride.waypoints.data)).coords) if ride.waypoints else None,  # Convert LINESTRING
            "departure_time": ride.departure_time,
            "available_seats": ride.available_seats,
            "price_per_seat": ride.price_per_seat,
            "status": ride.status,
            "is_recurring": ride.is_recurring,
        } for ride in rides]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/rides/{ride_id}", response_model=schemas.RidePublic)
def read_ride(ride_id: int, db: Session = Depends(get_db)):
    try:
        db_ride = db.query(routers.Ride).filter(routers.Ride.id == ride_id).first()
        if db_ride is None:
            raise HTTPException(status_code=404, detail="Ride not found")
        return {
            "id": db_ride.id,
            "start_location": list(wkb_loads(bytes(db_ride.start_location.data)).coords)[0],  # Convert POINT
            "end_location": list(wkb_loads(bytes(db_ride.end_location.data)).coords)[0],  # Convert POINT
            "waypoints": list(wkb_loads(bytes(db_ride.waypoints.data)).coords) if db_ride.waypoints else None,  # Convert LINESTRING
            "departure_time": db_ride.departure_time,
            "available_seats": db_ride.available_seats,
            "price_per_seat": db_ride.price_per_seat,
            "status": db_ride.status,
            "is_recurring": db_ride.is_recurring,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/rides/{ride_id}", response_model=schemas.RidePublic)
def update_ride(ride_id: int, ride: schemas.RideUpdate, db: Session = Depends(get_db)):
    db_ride = db.query(routers.Ride).filter(routers.Ride.id == ride_id).first()
    if db_ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")

    ride_data = ride.dict(exclude_unset=True)

    # Tratamento especial para localização
    if "start_location" in ride_data:
        db_ride.start_location = wkt_dumps(wkt_loads(ride_data["start_location"]))  # Convertendo WKT
    if "end_location" in ride_data:
        db_ride.end_location = wkt_dumps(wkt_loads(ride_data["end_location"]))  # Convertendo WKT
    if "waypoints" in ride_data:
        db_ride.waypoints = wkt_dumps(wkt_loads(ride_data["waypoints"])) if ride_data["waypoints"] else None  # Convertendo WKT

    # Atualiza os demais campos
    for key, value in ride_data.items():
        if key not in {"start_location", "end_location", "waypoints"}:  # Já tratamos esses campos
            setattr(db_ride, key, value)

    try:
        db.add(db_ride)
        db.commit()
        db.refresh(db_ride)

        # Retorna a resposta formatada corretamente
        return {
            "id": db_ride.id,
            "start_location": list(wkb_loads(bytes(db_ride.start_location.data)).coords)[0],  # Convert POINT
            "end_location": list(wkb_loads(bytes(db_ride.end_location.data)).coords)[0],  # Convert POINT
            "waypoints": list(wkb_loads(bytes(db_ride.waypoints.data)).coords) if db_ride.waypoints else None,  # Convert LINESTRING
            "departure_time": db_ride.departure_time,
            "available_seats": db_ride.available_seats,
            "price_per_seat": db_ride.price_per_seat,
            "status": db_ride.status,
            "is_recurring": db_ride.is_recurring,
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error. Please check your input data.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/rides/{ride_id}", response_model=dict)
def delete_ride(ride_id: int, db: Session = Depends(get_db)):
    db_ride = db.query(routers.Ride).filter(routers.Ride.id == ride_id).first()
    if db_ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    try:
        db.delete(db_ride)
        db.commit()
        return {"message": "Ride deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")