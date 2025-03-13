from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import models as routers
from typing import List, Optional
import schemas, utils
from database import get_db
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from uuid import uuid4  # To generate unique filenames
import os
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict, Optional
import shutil

UPLOAD_PROFILE_DIR = "ProfilePicture"
UPLOAD_IDENTITY_DIR = "IdentityPicture"
UPLOAD_DRIVER_LICENSE_DIR = "DriverPicture"

router = APIRouter()

from fastapi import Form

@router.post("/users/", response_model=schemas.UserPublic, status_code=201)
async def create_user(
    email: str = Form(...),
    full_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    identity_id: Optional[str] = Form(None),
    driver_license: Optional[str] = Form(None),
    role: schemas.UserRole = Form(...),
    user_is_verified: bool = Form(False),
    documents_is_verified: bool = Form(False),
    hashed_password: str = Form(...),
    profile_image: UploadFile = File(...),
    identity_id_file: UploadFile = File(...),
    driver_license_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # Check if email is already registered
    db_user = db.query(routers.User).filter(routers.User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password_hashed = utils.hash_password(hashed_password)

    if profile_image:
        filename = f"{uuid4()}_{profile_image.filename}"
        profile_path = Path(UPLOAD_PROFILE_DIR) / filename
        with open(profile_path, "wb") as buffer:
            buffer.write(await profile_image.read())
        profile_image_url = f"ProfilePicture/{filename}"  # Corrigindo URL absoluta

    if identity_id_file:
        filename = f"{uuid4()}_{identity_id_file.filename}"
        identity_id_file_path = Path(UPLOAD_IDENTITY_DIR) / filename
        with open(identity_id_file_path, "wb") as buffer:
            buffer.write(await identity_id_file.read())
        identity_id_file_url = f"IdentityPicture/{filename}"  # Corrigindo URL absoluta

    if driver_license_file:
        filename = f"{uuid4()}_{driver_license_file.filename}"  # Corrigindo erro de referência ao profile_image.filename
        driver_license_file_path = Path(UPLOAD_DRIVER_LICENSE_DIR) / filename
        with open(driver_license_file_path, "wb") as buffer:
            buffer.write(await driver_license_file.read())
        driver_license_file_url = f"DriverPicture/{filename}"  # Corrigindo URL absoluta

    # Criar novo usuário
    db_user = routers.User(
        email=email,
        full_name=full_name,
        phone=phone,
        identity_id=identity_id,
        driver_license=driver_license,
        role=role,
        user_is_verified=user_is_verified,
        documents_is_verified=documents_is_verified,
        hashed_password=hashed_password_hashed,
        profile_image=profile_image_url,
        identity_id_file=identity_id_file_url,
        driver_license_file=driver_license_file_url
    ) 

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    

@router.get("/users/", response_model=List[schemas.UserPublic])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        users = db.query(routers.User).offset(skip).limit(limit).all()
        return users
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Internal server error: {e}")

@router.get("/users/{user_id}", response_model=schemas.UserPublic)
def read_user(user_id: int, db: Session = Depends(get_db)):
    try:
        db_user = db.query(routers.User).filter(routers.User.id == user_id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return db_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/users/{user_id}", response_model=schemas.UserPublic)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(routers.User).filter(routers.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = user.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.get("/users/identity_picture/{user_id}")
async def read_identity_picture(user_id: int, db: Session = Depends(get_db)):
    try:
        identity_id_file = db.query(routers.User).filter(routers.User.id == user_id).first()
        identity_id_file = identity_id_file.identity_id_file
        if identity_id_file is None:
            raise HTTPException(status_code=404, detail="identity file not found")
        return FileResponse(identity_id_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    
@router.get("/users/profile_picture/{user_id}")
async def read_identity_picture(user_id: int, db: Session = Depends(get_db)):
    try:
        profile_picture = db.query(routers.User).filter(routers.User.id == user_id).first()
        profile_picture = profile_picture.profile_image
        if profile_picture is None:
            raise HTTPException(status_code=404, detail="identity file not found")
        return FileResponse(profile_picture)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/users/driver_license_picture/{user_id}")
async def read_identity_picture(user_id: int, db: Session = Depends(get_db)):
    try:
        driver_license_picture = db.query(routers.User).filter(routers.User.id == user_id).first()
        driver_license_picture = driver_license_picture.driver_license_file
        if driver_license_picture is None:
            raise HTTPException(status_code=404, detail="driver license picture file not found")
        return FileResponse(driver_license_picture)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/users/{user_id}", response_model=dict)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(routers.User).filter(routers.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        db.delete(db_user)
        db.commit()
        return {"message": "User deleted successfully"}
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.post("/users/login/", response_model=dict)
def login_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(routers.User).filter(routers.User.email == user.email).first()
    if db_user is None or not utils.verify_password(user.hashed_password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Generate a JWT token or session here.
    return {"message": "Login successful"}