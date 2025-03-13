from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
import datetime
from database import get_db
import models as routers
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from mpesa_payment import mpesa_gest_charging
from payout_b2b_mpesa import mpesa_payout_host_with_contract
from payout_b2c_mpesa import mpesa_payout_host_with_number

router = APIRouter()

def create_payment(payment, db):
    db_payment = routers.Payment(**payment.dict())
    try:
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.post("/{user_id}/{bookings_id}/payment/", tags=["Payment Transaction"])
async def create_payment(user_id:int, bookings_id:int, nr_to_charge:str,
                    payment: schemas.PaymentCreate,
                    db: Session = Depends(get_db),
                    #current_user: schemas.User=Depends(get_current_active_user)
                    ):
    
    ride_id = db.query(routers.Booking).filter(routers.Booking.id == bookings_id).ride_id
    ride_price = db.query(routers.Ride).filter(routers.Ride.id == ride_id).price_per_seat
    payment.amount = ride_price
    
    now = datetime.datetime.now()
    credit = None

    trans_id = 'BY'+now.strftime('%Y%m%d%H%M%S')+'CD'

    payment_status = await mpesa_gest_charging(trans_id, nr_to_charge, payment.amount)
    if payment_status.status_code in [200, 201, 202, 203]:
        payment.payment_method = "MPESA"
        payment.transaction_id = trans_id
        payment.status = "PAID"
        credit = create_payment(payment, db)
    else:
        raise HTTPException(status_code=405, detail=payment_status.body)
    
    #Payout
    driver_id = db.query(routers.Ride).filter(routers.Ride.id == ride_id).driver_id
    driver_mpesa_number = db.query(routers.User).filter(routers.User.id == driver_id).phone

    trans_id_2 = 'BY'+now.strftime('%Y%m%d%H%M%S')+'DB'
    payment.amount = payment.amount*0.9
    try:
        debit = await mpesa_payout_host_with_number(trans_id_2, driver_mpesa_number, amount=payment.amount)
    except:
        raise HTTPException(status_code=405, detail='Unamble to payout host')

    if debit.status_code in [200, 201, 202, 203]:
        payment.payment_method = "MPESA"
        payment.transaction_id = trans_id_2
        payment.status = "PAID"
        credit = create_payment(payment, db)
    else:
        raise HTTPException(status_code=405, detail=payment_status.body)
    
    return {'customer_payment': True, 'host_payout': True}


@router.get("/payments/", response_model=List[schemas.PaymentPublic])
def read_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        payments = db.query(routers.Payment).offset(skip).limit(limit).all()
        return payments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/payments/{payment_id}", response_model=schemas.PaymentPublic)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    try:
        db_payment = db.query(routers.Payment).filter(routers.Payment.id == payment_id).first()
        if db_payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        return db_payment
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/payments/{payment_id}", response_model=schemas.PaymentPublic)
def update_payment(payment_id: int, payment: schemas.PaymentUpdate, db: Session = Depends(get_db)):
    db_payment = db.query(routers.Payment).filter(routers.Payment.id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment_data = payment.dict(exclude_unset=True)
    for key, value in payment_data.items():
        setattr(db_payment, key, value)

    try:
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/payments/{payment_id}", response_model=dict)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    db_payment = db.query(routers.Payment).filter(routers.Payment.id == payment_id).first()
    if db_payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    try:
        db.delete(db_payment)
        db.commit()
        return {"message": "Payment deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")