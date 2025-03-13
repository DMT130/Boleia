from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import schemas, utils
from database import get_db
import models as routers
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

router = APIRouter()

@router.post("/group_members/", response_model=schemas.GroupMemberPublic, status_code=status.HTTP_201_CREATED)
def create_group_member(group_member: schemas.GroupMemberCreate, db: Session = Depends(get_db)):
    db_group_member = routers.GroupMember(**group_member.dict())
    try:
        db.add(db_group_member)
        db.commit()
        db.refresh(db_group_member)
        return db_group_member
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/group_members/", response_model=List[schemas.GroupMemberPublic])
def read_group_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        group_members = db.query(routers.GroupMember).offset(skip).limit(limit).all()
        return group_members
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/group_members/{group_member_id}", response_model=schemas.GroupMemberPublic)
def read_group_member(group_member_id: int, db: Session = Depends(get_db)):
    try:
        db_group_member = db.query(routers.GroupMember).filter(routers.GroupMember.id == group_member_id).first()
        if db_group_member is None:
            raise HTTPException(status_code=404, detail="Group member not found")
        return db_group_member
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/group_members/{group_member_id}", response_model=schemas.GroupMemberPublic)
def update_group_member(group_member_id: int, group_member: schemas.GroupMemberUpdate, db: Session = Depends(get_db)):
    db_group_member = db.query(routers.GroupMember).filter(routers.GroupMember.id == group_member_id).first()
    if db_group_member is None:
        raise HTTPException(status_code=404, detail="Group member not found")

    # In this case, update and create schemas are the same.
    # So, we can just update the existing object with the new data.
    group_member_data = group_member.dict(exclude_unset=True)
    for key, value in group_member_data.items():
        setattr(db_group_member, key, value)

    try:
        db.add(db_group_member)
        db.commit()
        db.refresh(db_group_member)
        return db_group_member
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/group_members/{group_member_id}", response_model=dict)
def delete_group_member(group_member_id: int, db: Session = Depends(get_db)):
    db_group_member = db.query(routers.GroupMember).filter(routers.GroupMember.id == group_member_id).first()
    if db_group_member is None:
        raise HTTPException(status_code=404, detail="Group member not found")
    try:
        db.delete(db_group_member)
        db.commit()
        return {"message": "Group member deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")