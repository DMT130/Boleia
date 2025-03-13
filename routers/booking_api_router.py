from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
from database import get_db
import models as routers
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from shapely.wkb import loads as wkb_loads
from geoalchemy2.shape import to_shape
from routers.user_auth_api_router import get_current_active_user, check_admin_rights, get_current_user

router = APIRouter()

@router.post("/bookings/", response_model=schemas.BookingPublic, status_code=status.HTTP_201_CREATED)
def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    booking_data = booking.dict()
    booking_data['pickup_location'] = utils.to_wkt(booking_data['pickup_location'], "POINT")
    booking_data['dropoff_location'] = utils.to_wkt(booking_data['dropoff_location'], "POINT")
    booking_data['passenger_id'] = current_user.id
    
    db_booking = routers.Booking(**booking_data)
    try:
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return {
                    "id": db_booking.id,
                    "ride_id": db_booking.ride_id,
                    "passenger_id": db_booking.passenger_id,
                    "seats_booked": db_booking.seats_booked,
                    "status": db_booking.status,
                    "pickup_location": list(to_shape(db_booking.pickup_location).coords)[0],
                    "dropoff_location": list(to_shape(db_booking.dropoff_location).coords)[0]
                }
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/bookings/", response_model=List[schemas.BookingPublic])
def read_bookings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    try:
        bookings = db.query(routers.Booking).filter(routers.Booking.passenger_id == current_user.id).offset(skip).limit(limit).all()

        return [{
                    "id": db_booking.id,
                    "ride_id": db_booking.ride_id,
                    "passenger_id": db_booking.passenger_id,
                    "seats_booked": db_booking.seats_booked,
                    "status": db_booking.status,
                    "pickup_location": list(to_shape(db_booking.pickup_location).coords)[0],
                    "dropoff_location": list(to_shape(db_booking.dropoff_location).coords)[0]
                } for db_booking in bookings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/bookings/{booking_id}", response_model=schemas.BookingPublic)
def read_booking(booking_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    try:
        db_booking = db.query(routers.Booking).filter(routers.Booking.id == booking_id).first()
        if db_booking is None:
            raise HTTPException(status_code=404, detail="Booking not found")
        db_ride = db.query(routers.Ride).filter(routers.Ride.id == db_booking.ride_id).first()
        if current_user.id not in [db_booking.passenger_id, db_ride.driver_id]:
            raise HTTPException(status_code=403, detail="You can only update your own rides")
        return {
                    "id": db_booking.id,
                    "ride_id": db_booking.ride_id,
                    "passenger_id": db_booking.passenger_id,
                    "seats_booked": db_booking.seats_booked,
                    "status": db_booking.status,
                    "pickup_location": list(to_shape(db_booking.pickup_location).coords)[0],
                    "dropoff_location": list(to_shape(db_booking.dropoff_location).coords)[0]
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.put("/bookings/{booking_id}", response_model=schemas.BookingPublic)
def update_booking(booking_id: int, booking: schemas.BookingUpdate, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    db_booking = db.query(routers.Booking).filter(routers.Booking.id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    db_ride = db.query(routers.Ride).filter(routers.Ride.id == db_booking.ride_id).first()
    if current_user.id not in [db_booking.passenger_id, db_ride.driver_id]:
        raise HTTPException(status_code=403, detail="You can only update your own rides")

    booking_data = booking.dict(exclude_unset=True)

    # Atualiza os campos de localização corretamente
    if "pickup_location" in booking_data and booking_data["pickup_location"]:
        db_booking.pickup_location = utils.to_wkt(booking_data["pickup_location"], "POINT")
    if "dropoff_location" in booking_data and booking_data["dropoff_location"]:
        db_booking.dropoff_location = utils.to_wkt(booking_data["dropoff_location"], "POINT")

    # Atualiza os demais campos
    for key, value in booking_data.items():
        if key not in {"pickup_location", "dropoff_location"}:  # Já tratados acima
            setattr(db_booking, key, value)

    try:
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)

        # Retorno formatado para `BookingPublic`
        return schemas.BookingPublic(
            id=db_booking.id,
            ride_id=db_booking.ride_id,
            passenger_id=db_booking.passenger_id,
            seats_booked=db_booking.seats_booked,
            status=db_booking.status,
            pickup_location=list(to_shape(db_booking.pickup_location).coords)[0] if db_booking.pickup_location else None,  # Convertendo POINT para [lat, lon]
            dropoff_location=list(to_shape(db_booking.dropoff_location).coords)[0] if db_booking.dropoff_location else None  # Convertendo POINT para [lat, lon]
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error. Please check your input data.")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/bookings/{booking_id}", response_model=dict)
def delete_booking(booking_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    db_booking = db.query(routers.Booking).filter(routers.Booking.id == booking_id).first()
    if db_booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.id != db_booking.passenger_id:
         raise HTTPException(status_code=403, detail="You can only delete your own bookings")
    try:
        db.delete(db_booking)
        db.commit()
        return {"message": "Booking deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")