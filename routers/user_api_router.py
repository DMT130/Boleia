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
from email_verification import send_verification_email, generate_confirmation_code, check_confirmation_code_match, delete_confirmation_email, get_confirmation_email_by_user_id


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

@router.post("/users/signup", response_model=schemas.UserPublic, status_code=201)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    hashed_password = utils.hash_password(user.password)
    db_user = routers.User(
        full_name=user.full_name,
        email=user.email,
        password=hashed_password,
        phone=user.phone,
        nuit=user.nuit,
        driver_license=user.driver_license,
        identity_id=user.identity_id,
        electricity_buill_id=user.electricity_buill_id
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        _, random_int = await generate_confirmation_code(db=db, user_id=db_user.id)
        sent = await send_verification_email(email=db_user.email, confirmation_code=random_int)
        if sent is True:
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
    

@router.get("/users/generate_user_activation_code/{user_id}", response_model=schemas.UserPublic)
async def get_customer_activation_code(user_id: int, db: Session = Depends(get_db), current_user: schemas.User=Depends(get_current_user)):
    if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only read your own user")
    try:
        db_user = db.query(routers.User).filter(routers.User.id == user_id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if db_user.user_is_verified is False:
            email_conf = get_confirmation_email_by_user_id(db, user_id)
            if email_conf:
                deleted_cof = delete_confirmation_email(db, email_conf)
                if deleted_cof:
                    _, random_int = await generate_confirmation_code(db=db, user_id=db_user.id)
                    sent = await send_verification_email(email=db_user.email, confirmation_code=random_int)
                    if sent is True:
                        return db_user
            else:
                _, random_int = await generate_confirmation_code(db=db, user_id=db_user.id)
                sent = await send_verification_email(email=db_user.email, confirmation_code=random_int)
                if sent is True:
                        return db_user
        else:
            raise HTTPException(status_code=303, detail="user is already activated")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    

@router.patch("/user/activate_user/{user_id}/{confirmation_code}", response_model=schemas.UserPublic)
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




@router.patch("/user/documents_confirmation/{user_id}", response_model=schemas.UserPublic)
def activate_user_documents(
    user_id: int,
    user_sch: schemas.UserDocumentsActivation,
    current_user: schemas.User = Depends(check_admin_rights),  # Move this up
    db: Session = Depends(get_db)
    ):
     if current_user.id != user_id:
         raise HTTPException(status_code=403, detail="You can only activate you own user")
     db_user = db.query(routers.User).filter(routers.User.id == user_id).first()
     if not db_user:
        raise HTTPException(status_code=404, detail="user not found")
     if db_user.profile_image is not None and db_user.identity_id_file is not None and db_user.electricity_buill_file is not None:
        result = active_user(db, user_sch, db_user)
        if result:
            return result
        else:
            raise HTTPException(status_code=403, detail="documents were not confirmed")
     else:
            raise HTTPException(status_code=403, detail="one or more documents are not present")
     

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
    

@router.post("/users/credelect_picture/{user_id}", response_model=schemas.UserPublic)
async def upload_or_update_credelect_picture(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only upload your own file")

    user_data = db.query(routers.User).filter(routers.User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Save the uploaded file
        filename = f"{uuid4()}_{file.filename}"  # Corrigindo erro de referência ao profile_image.filename
        electricity_bill_file_path = Path(UPLOAD_ELECTRICITY_BILL_DIR) / filename
        with open(electricity_bill_file_path, "wb") as buffer:
            buffer.write(await file.read())
        electricity_bill_file = f"CredelectPicture/{filename}"  # Corrigindo URL absoluta

        # Update DB with file path
        user_data.electricity_buill_file = electricity_bill_file
        db.commit()
        db.refresh(user_data)
        return user_data
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/users/driver_license_picture/{user_id}", response_model=schemas.UserPublic)
async def upload_or_update_driver_license_picture(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only upload your own file")

    user_data = db.query(routers.User).filter(routers.User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Save the uploaded file
        filename = f"{uuid4()}_{file.filename}"  # Corrigindo erro de referência ao profile_image.filename
        driver_license_picture_path = Path(UPLOAD_DRIVER_LICENSE_DIR) / filename
        with open(driver_license_picture_path, "wb") as buffer:
            buffer.write(await file.read())
        driver_license_file = f"DriverPicture/{filename}"  # Corrigindo URL absoluta

        # Update DB with file path
        user_data.driver_license_file = driver_license_file
        db.commit()
        db.refresh(user_data)
        return user_data
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/users/profile_image/{user_id}", response_model=schemas.UserPublic)
async def upload_or_update_profile_image(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only upload your own file")

    user_data = db.query(routers.User).filter(routers.User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Save the uploaded file
        filename = f"{uuid4()}_{file.filename}"  # Corrigindo erro de referência ao profile_image.filename
        profile_image_path = Path(UPLOAD_PROFILE_DIR) / filename
        with open(profile_image_path, "wb") as buffer:
            buffer.write(await file.read())
        profile_image = f"ProfilePicture/{filename}"  # Corrigindo URL absoluta

        # Update DB with file path
        user_data.profile_image = profile_image
        db.commit()
        db.refresh(user_data)
        return user_data
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    

@router.post("/users/identity_id/{user_id}", response_model=schemas.UserPublic)
async def upload_or_update_identity_id(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only upload your own file")

    user_data = db.query(routers.User).filter(routers.User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Save the uploaded file
        filename = f"{uuid4()}_{file.filename}"  # Corrigindo erro de referência ao profile_image.filename
        identity_id_file_path = Path(UPLOAD_IDENTITY_DIR) / filename
        with open(identity_id_file_path, "wb") as buffer:
            buffer.write(await file.read())
        identity_id_file = f"IdentityPicture/{filename}"  # Corrigindo URL absoluta

        # Update DB with file path
        user_data.identity_id_file = identity_id_file
        db.commit()
        db.refresh(user_data)
        return user_data
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database integrity error: {e}")
    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")