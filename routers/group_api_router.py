from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
from database import get_db
import models as routers
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

router = APIRouter()

@router.post("/groups/", response_model=schemas.GroupPublic, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    db_group = routers.Group(**group.dict())
    try:
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        return db_group
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/groups/", response_model=List[schemas.GroupPublic])
def read_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        groups = db.query(routers.Group).offset(skip).limit(limit).all()
        return groups
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/groups/{group_id}", response_model=schemas.GroupPublic)
def read_group(group_id: int, db: Session = Depends(get_db)):
    try:
        db_group = db.query(routers.Group).filter(routers.Group.id == group_id).first()
        if db_group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        return db_group
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/groups/{group_id}", response_model=schemas.GroupPublic)
def update_group(group_id: int, group: schemas.GroupUpdate, db: Session = Depends(get_db)):
    db_group = db.query(routers.Group).filter(routers.Group.id == group_id).first()
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    group_data = group.dict(exclude_unset=True)
    for key, value in group_data.items():
        setattr(db_group, key, value)

    try:
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        return db_group
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/groups/{group_id}", response_model=dict)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    db_group = db.query(routers.Group).filter(routers.Group.id == group_id).first()
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    try:
        db.delete(db_group)
        db.commit()
        return {"message": "Group deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")