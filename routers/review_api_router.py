from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
from database import get_db
import models as routers
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

router = APIRouter()

@router.post("/reviews/", response_model=schemas.ReviewPublic, status_code=status.HTTP_201_CREATED)
def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    db_review = routers.Review(**review.dict())
    try:
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        return db_review
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/reviews/", response_model=List[schemas.ReviewPublic])
def read_reviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        reviews = db.query(routers.Review).offset(skip).limit(limit).all()
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/reviews/{review_id}", response_model=schemas.ReviewPublic)
def read_review(review_id: int, db: Session = Depends(get_db)):
    try:
        db_review = db.query(routers.Review).filter(routers.Review.id == review_id).first()
        if db_review is None:
            raise HTTPException(status_code=404, detail="Review not found")
        return db_review
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/reviews/{review_id}", response_model=schemas.ReviewPublic)
def update_review(review_id: int, review: schemas.ReviewUpdate, db: Session = Depends(get_db)):
    db_review = db.query(routers.Review).filter(routers.Review.id == review_id).first()
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    review_data = review.dict(exclude_unset=True)
    for key, value in review_data.items():
        setattr(db_review, key, value)

    try:
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        return db_review
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/reviews/{review_id}", response_model=dict)
def delete_review(review_id: int, db: Session = Depends(get_db)):
    db_review = db.query(routers.Review).filter(routers.Review.id == review_id).first()
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    try:
        db.delete(db_review)
        db.commit()
        return {"message": "Review deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")