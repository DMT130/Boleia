from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
from database import get_db
import models as routers
from shapely.wkb import loads as wkb_loads
from sqlalchemy.exc import IntegrityError
from geoalchemy2.shape import to_shape
from sqlalchemy import select, func
from shapely.wkb import loads as wkb_loads
from shapely.wkt import loads as wkt_loads, dumps as wkt_dumps
from routers.user_auth_api_router import get_current_active_user, check_admin_rights, get_current_user

router = APIRouter()

@router.post("/rides/", response_model=schemas.RidePublic, status_code=status.HTTP_201_CREATED)
def create_ride(ride: schemas.RideCreate, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    ride_data = ride.dict()
    ride_data['start_location'] = utils.to_wkt(ride_data['start_location'], "POINT")
    ride_data['end_location'] = utils.to_wkt(ride_data['end_location'], "POINT")
    ride_data['waypoints'] = utils.to_wkt(ride_data['waypoints'], "LINESTRING")
    ride_data['driver_id'] = current_user.id
    
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
def update_ride(ride_id: int, ride: schemas.RideUpdate, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    db_ride = db.query(routers.Ride).filter(routers.Ride.id == ride_id).first()
    if db_ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    if current_user.id != db_ride.driver_id:
         raise HTTPException(status_code=403, detail="You can only update your own rides")
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
def delete_ride(ride_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_active_user)):
    db_ride = db.query(routers.Ride).filter(routers.Ride.id == ride_id).first()
    if db_ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    if current_user.id != db_ride.driver_id:
         raise HTTPException(status_code=403, detail="You can only delete your own rides")
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
    

from sqlalchemy import select, func, case, text, cast
from geoalchemy2.types import Geography
from geoalchemy2.functions import (
    ST_LineSubstring,
    ST_LineLocatePoint,
    ST_HausdorffDistance,
    ST_DWithin,
    ST_Length,
    ST_EndPoint,
    ST_Contains
)

# Configuration
BASE_FUEL_PRICE = 86  # Price per liter
FUEL_CONSUMPTION_FACTOR = 0.1  # Liters per km per engine size unit
MAX_DISTANCE_METERS = 500  # Maximum pickup distance

@router.post("/rides/search/", 
             status_code=status.HTTP_200_OK, 
             response_model=List[schemas.RidePublic])
async def search_best_route(
    passenger_search: schemas.SearchBestRoute,
    limit: int = 3,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Find best matching rides with:
    - Route similarity comparison
    - Proposed dropoff point
    - Shared distance calculation
    - Price estimation
    """
    try:
        # Convert input to WKT with validation
        passenger_loc = utils.to_wkt(passenger_search.passenger_current_location, "POINT")
        passenger_route = utils.to_wkt(passenger_search.passenger_route, "LINESTRING")
        passenger_end = func.ST_EndPoint(passenger_route)

        # Main query for candidate rides
        rides_query = (
            select(
                routers.Ride.id,
                routers.Ride.waypoints,
                routers.Ride.current_location,
                routers.Ride.vehicle_id,

                # Proposed dropoff logic
                case(
                    [
                        (
                            ST_Contains(routers.Ride.waypoints, passenger_end),
                            passenger_end
                        )
                    ],
                    else_=ST_EndPoint(
                        ST_LineSubstring(
                            routers.Ride.waypoints,
                            ST_LineLocatePoint(routers.Ride.waypoints, 
                                             routers.Ride.current_location),
                            1.0
                        )
                    )
                ).label('proposed_dropoff'),

                # Shared route calculation
                ST_Length(
                    cast(
                        ST_LineSubstring(
                            routers.Ride.waypoints,
                            ST_LineLocatePoint(routers.Ride.waypoints, 
                                             routers.Ride.current_location),
                            ST_LineLocatePoint(routers.Ride.waypoints, 
                                             case(
                                                 [
                                                     (
                                                         ST_Contains(routers.Ride.waypoints, passenger_end),
                                                         passenger_end
                                                     )
                                                 ],
                                                 else_=ST_EndPoint(routers.Ride.waypoints)
                                             ))
                        ),
                        Geography
                    )
                ).label('shared_distance'),

                # Route similarity score
                (1 / (1 + ST_HausdorffDistance(
                    ST_LineSubstring(
                        routers.Ride.waypoints,
                        ST_LineLocatePoint(routers.Ride.waypoints, 
                                         routers.Ride.current_location),
                        1.0
                    ),
                    passenger_route
                ))).label('similarity_score')
            )
            .where(
                routers.Ride.status == 'IN_PROGRESS',
                ST_DWithin(
                    cast(routers.Ride.waypoints, Geography),
                    cast(passenger_loc, Geography),
                    MAX_DISTANCE_METERS
                ),
                ST_LineLocatePoint(routers.Ride.waypoints, routers.Ride.current_location) < 
                ST_LineLocatePoint(routers.Ride.waypoints, passenger_loc)
            )
            .order_by(text("similarity_score DESC"))
            .limit(limit)
        )

        candidate_rides = db.execute(rides_query).fetchall()

        if not candidate_rides:
            return []

        # Batch fetch vehicle details
        vehicle_ids = [ride.vehicle_id for ride in candidate_rides]
        vehicles = db.execute(
            select(routers.Vehicle.id, routers.Vehicle.engine_size)
            .where(routers.Vehicle.id.in_(vehicle_ids))
        ).fetchall()
        vehicle_map = {v.id: v.engine_size for v in vehicles}

        # Process results with price calculation
        results = []
        for ride in candidate_rides:
            engine_size = vehicle_map.get(ride.vehicle_id)
            if not engine_size:
                continue  # Skip rides with missing vehicle data

            # Calculate price using shared distance
            distance_km = ride.shared_distance / 1000
            price = BASE_FUEL_PRICE * distance_km * engine_size * FUEL_CONSUMPTION_FACTOR

            results.append(schemas.RidePublic(
                id=ride.id,
                waypoints=ride.waypoints,
                current_location=ride.current_location,
                proposed_dropoff=ride.proposed_dropoff,
                similarity_score=round(float(ride.similarity_score), 2),
                price_calculate_variables={
                    "distance_km": round(distance_km, 2),
                    "engine_size": engine_size,
                    "fuel_price_per_liter": BASE_FUEL_PRICE,
                    "estimated_price": round(price, 2)
                }
            ))

        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ride search failed: {str(e)}"
        )