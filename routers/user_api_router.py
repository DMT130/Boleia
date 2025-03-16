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
from routers.user_auth_api_router import get_current_active_user, get_current_user, check_admin_rights
from email_verification import send_verification_email, generate_confirmation_code, check_confirmation_code_match, delete_confirmation_email


UPLOAD_PROFILE_DIR = "ProfilePicture"
UPLOAD_IDENTITY_DIR = "IdentityPicture"
UPLOAD_DRIVER_LICENSE_DIR = "DriverPicture"
UPLOAD_ELECTRICITY_BILL_DIR = "CredelectPicture"

router = APIRouter()

from fastapi import Form

def active_user(db: Session, user: schemas.UserUpdate, user_data: schemas.User):
    user = user.dict(exclude_unset=True)
    for key, value in user.items():
            setattr(user_data, key, value)
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    return user_data

@router.post("/users/", response_model=schemas.UserPublic, status_code=201)
async def create_user(
    email: str = Form(...),
    full_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    identity_id: Optional[str] = Form(None),
    driver_license: Optional[str] = Form(None),
    electricity_buill_id: Optional[str] = Form(None),
    role: schemas.UserRole = Form(...),
    user_is_verified: bool = Form(False),
    documents_is_verified: bool = Form(False),
    hashed_password: str = Form(...),
    profile_image: UploadFile = File(...),
    identity_id_file: UploadFile = File(...),
    driver_license_file: Optional[UploadFile] = File(None),
    electricity_buill_file: Optional[UploadFile] = File(None),
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
    
    if electricity_buill_file:
        filename = f"{uuid4()}_{electricity_buill_file.filename}"  # Corrigindo erro de referência ao profile_image.filename
        electricity_bill_file_path = Path(UPLOAD_ELECTRICITY_BILL_DIR) / filename
        with open(electricity_bill_file_path, "wb") as buffer:
            buffer.write(await electricity_buill_file.read())
        electricity_bill_file = f"CredelectPicture/{filename}"  # Corrigindo URL absoluta

    # Criar novo usuário
    db_user = routers.User(
        email=email,
        full_name=full_name,
        phone=phone,
        identity_id=identity_id,
        driver_license=driver_license,
        electricity_buill_id=electricity_buill_id,
        role=role,
        user_is_verified=user_is_verified,
        documents_is_verified=documents_is_verified,
        hashed_password=hashed_password_hashed,
        profile_image=profile_image_url,
        identity_id_file=identity_id_file_url,
        driver_license_file=driver_license_file_url,
        electricity_buill_file=electricity_bill_file
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        _, random_int = await generate_confirmation_code(db=db, user_id=db_user.id)
        sent = await send_verification_email(email=db_user.email, confirmation_code=random_int)
        if sent is True:
            return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    
@router.patch("/user/confirmation/{user_id}/{confirmation_code}", response_model=schemas.UserPublic)
def activate_user(
    user_id: int,
    confirmation_code: int,
    user_sch: schemas.UserActivation,
    current_user: schemas.User = Depends(get_current_user),  # Move this up
    db: Session = Depends(get_db)
    ):
     if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only activate you own user")
     db_user = db.query(routers.User).filter(routers.User.id == user_id).first()
     if not db_user:
        raise HTTPException(status_code=404, detail="user not found")

     confirmation, confirmation_obj = check_confirmation_code_match(db, user_id=user_id, confirmation_code=confirmation_code)
     if confirmation:
        result = active_user(db, user_sch, db_user)
     else:
         raise HTTPException(status_code=403, detail="The confirmation code does not match")
     deleted_confirmation_code = delete_confirmation_email(db, confirmation_obj)
     if deleted_confirmation_code is True:
         return result
     else:
         raise HTTPException(status_code=403, detail="confirmation code was not deleted")

@router.get("/users/", response_model=List[schemas.UserPublic])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: schemas.User=Depends(check_admin_rights)):
    try:
        users = db.query(routers.User).offset(skip).limit(limit).all()
        return users
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Internal server error: {e}")

@router.get("/users/{user_id}", response_model=schemas.UserPublic)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only read your own user")
    try:
        db_user = db.query(routers.User).filter(routers.User.id == user_id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return db_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.put("/users/{user_id}", response_model=schemas.UserPublic)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only update your own user")
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
async def read_identity_picture(user_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only get you own id card")
    try:
        identity_id_file = db.query(routers.User).filter(routers.User.id == user_id).first()
        identity_id_file = identity_id_file.identity_id_file
        if identity_id_file is None:
            raise HTTPException(status_code=404, detail="identity file not found")
        return FileResponse(identity_id_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    
@router.get("/users/profile_picture/{user_id}")
async def read_profile_picture(user_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only get you own profile picture")
    try:
        profile_picture = db.query(routers.User).filter(routers.User.id == user_id).first()
        profile_picture = profile_picture.profile_image
        if profile_picture is None:
            raise HTTPException(status_code=404, detail="identity file not found")
        return FileResponse(profile_picture)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/users/driver_license_picture/{user_id}")
async def read_driver_license_picture(user_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only get you own driver license picture")
    try:
        driver_license_picture = db.query(routers.User).filter(routers.User.id == user_id).first()
        driver_license_picture = driver_license_picture.driver_license_file
        if driver_license_picture is None:
            raise HTTPException(status_code=404, detail="driver license picture file not found")
        return FileResponse(driver_license_picture)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/users/credelect_picture/{user_id}")
async def read_credelect_picture(user_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only get you own driver license picture")
    try:
        user_data = db.query(routers.User).filter(routers.User.id == user_id).first()
        electricity_buill_file = user_data.electricity_buill_file
        if electricity_buill_file is None:
            raise HTTPException(status_code=404, detail="driver license picture file not found")
        return FileResponse(electricity_buill_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@router.delete("/users/{user_id}", response_model=dict)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only activate your own user")
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