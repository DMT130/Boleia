from pydantic import BaseModel, EmailStr, Field, StringConstraints
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    DRIVER = "DRIVER"
    PASSENGER = "PASSENGER"
    BOTH = "BOTH"
    ADMIN = "ADMIN"

class RideStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

#Users
class UserBase(BaseModel):
    full_name: str
    email: str
    phone: str
    nuit: Optional[str] = None
    identity_id: str
    driver_license: str
    electricity_buill_id: str

class UserCreate(UserBase):
    password: str
    
class UserActivation(BaseModel):
    user_is_verified: Optional[bool] = None

class UserDocumentsActivation(BaseModel):
    documents_is_verified: Optional[bool] = None
    
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[Annotated[str, StringConstraints(max_length=100)]] = None
    phone: Optional[Annotated[str, StringConstraints(max_length=20)]] = None
    nuit: Optional[Annotated[str, StringConstraints(max_length=100)]] = None
    identity_id: Optional[Annotated[str, StringConstraints(max_length=100)]] = None
    driver_license: Optional[Annotated[str, StringConstraints(max_length=100)]] = None
    electricity_buill_id: Optional[Annotated[str, StringConstraints(max_length=100)]] = None


class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    role: UserRole = UserRole.BOTH
    updated_at: Optional[datetime] = None
    user_is_verified: Optional[bool] = False
    documents_is_verified: Optional[bool] = False

    class Config:
        orm_mode = True

class User(UserInDBBase):
    pass

class UserWithHashedPassword(UserInDBBase):
    hashed_password: str

class UserPublic(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    identity_id: str
    nuit: str
    electricity_buill_id: str
    driver_license: Optional[str] = None
    role: UserRole
    user_is_verified: bool
    documents_is_verified: bool
    profile_image: Optional[str] = None
    identity_id_file: Optional[str] = None
    driver_license_file: Optional[str] = None
    electricity_buill_file: Optional[str] = None

    class Config:
        orm_mode = True


#Vehicle
class VehicleBase(BaseModel):
    make: str = Field(None, max_length=50)
    model: str = Field(None, max_length=50)
    year: int
    color: str = Field(None, max_length=20)
    license_plate: str = Field(..., max_length=20)
    capacity: int
    engine_size: float
    insurance_document: str
    car_registraction_file: str
    car_owership_file: str
    car_photos: List[str]  # Updated to a list

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    make: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    year: Optional[int] = None
    color: Optional[str] = Field(None, max_length=20)
    license_plate: Optional[str] = Field(None, max_length=20)
    capacity: Optional[int] = None
    engine_size: Optional[float] = None
    insurance_document: Optional[str] = None
    car_registraction_file: Optional[str] = None
    car_owership_file: Optional[str] = None
    car_photos: Optional[List[str]] = None  # Allow updating photos

class VehicleInDBBase(VehicleBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Vehicle(VehicleInDBBase):
    pass

class VehiclePublic(BaseModel):
    id: int
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    capacity: int
    engine_size: float
    insurance_document: str
    car_registraction_file: str
    car_owership_file: str
    car_photos: List[str]  # Include in public schema

    class Config:
        orm_mode = True


#Ride
class RideBase(BaseModel):
    start_location:List[float]
    end_location:List[float]
    waypoints: Optional[List[List[float]]] = None
    departure_time: datetime
    available_seats: int
    price_per_seat: float
    status: RideStatus = RideStatus.SCHEDULED
    is_recurring: bool = False
    recurring_pattern: Optional[Annotated[str, StringConstraints(max_length=50)]] = None

class RideCreate(RideBase):
    driver_id: int
    vehicle_id: int

class RideUpdate(BaseModel):
    start_location: Optional[List[float]] = None
    end_location: Optional[List[float]] = None
    waypoints: Optional[List[List[float]]] = None
    departure_time: Optional[datetime] = None
    available_seats: Optional[int] = None
    price_per_seat: Optional[float] = None
    status: Optional[RideStatus] = None
    is_recurring: Optional[bool] = None
    recurring_pattern: Optional[Annotated[str, StringConstraints(max_length=50)]] = None

class RideInDBBase(RideBase):
    id: int
    driver_id: int
    vehicle_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Ride(RideInDBBase):
    pass

class RidePublic(BaseModel):
    id: int
    start_location:List[float]
    end_location:List[float]
    waypoints: Optional[List[List[float]]] = None
    departure_time: datetime
    available_seats: int
    price_per_seat: float
    status: RideStatus
    is_recurring: bool

    class Config:
        orm_mode = True


#Booking
class BookingBase(BaseModel):
    ride_id: int
    passenger_id: int
    seats_booked: int
    status: BookingStatus = BookingStatus.PENDING
    pickup_location: Optional[List[float]] = None
    dropoff_location: Optional[List[float]] = None

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    seats_booked: Optional[int] = None
    status: Optional[BookingStatus] = None
    pickup_location: Optional[List[float]] = None
    dropoff_location: Optional[List[float]] = None

class BookingInDBBase(BookingBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Booking(BookingInDBBase):
    pass

class BookingPublic(BaseModel):
    id: int
    ride_id: int
    passenger_id: int
    seats_booked: int
    status: BookingStatus
    pickup_location: Optional[List[float]] = None
    dropoff_location: Optional[List[float]] = None

    class Config:
        orm_mode = True


#Payment
class PaymentBase(BaseModel):
    booking_id: int
    amount: float
    currency: Optional[Annotated[str, StringConstraints(max_length=3)]] = "MZN"
    payment_method: Optional[Annotated[str, StringConstraints(max_length=50)]] = None
    transaction_id: Optional[Annotated[str, StringConstraints(max_length=255)]] = None
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    currency: Optional[Annotated[str, StringConstraints(max_length=3)]] = None
    payment_method: Optional[Annotated[str, StringConstraints(max_length=50)]] = None
    transaction_id: Optional[Annotated[str, StringConstraints(max_length=255)]] = None
    status: Optional[PaymentStatus] = None

class PaymentInDBBase(PaymentBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Payment(PaymentInDBBase):
    pass

class PaymentPublic(BaseModel):
    id: int
    booking_id: int
    amount: float
    currency: str
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    status: PaymentStatus

    class Config:
        orm_mode = True


# Review Schemas
class ReviewBase(BaseModel):
    ride_id: int
    reviewer_id: int
    reviewee_id: int
    rating: int
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    ride_id: int

class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None

class ReviewInDBBase(ReviewBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Review(ReviewInDBBase):
    pass

class ReviewPublic(BaseModel):
    id: int
    ride_id: int
    reviewer_id: int
    reviewee_id: int
    rating: int
    comment: Optional[str] = None

    class Config:
        orm_mode = True

# Group Schemas
class GroupBase(BaseModel):
    name: Optional[Annotated[str, StringConstraints(max_length=100)]]
    description: Optional[str] = None
    is_verified: bool = False

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[Annotated[str, StringConstraints(max_length=50)]] = None
    description: Optional[str] = None
    is_verified: Optional[bool] = None

class GroupInDBBase(GroupBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class Group(GroupInDBBase):
    pass

class GroupPublic(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_verified: bool

    class Config:
        orm_mode = True

# Group Member Schemas
class GroupMemberBase(BaseModel):
    user_id: int
    group_id: int

class GroupMemberCreate(GroupMemberBase):
    pass

class GroupMemberUpdate(GroupMemberBase):
    pass

class GroupMemberInDBBase(GroupMemberBase):
    id: int
    joined_at: datetime

    class Config:
        orm_mode = True

class GroupMember(GroupMemberInDBBase):
    pass

class GroupMemberPublic(BaseModel):
    id: int
    user_id: int
    group_id: int

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str


#Email confirmation
class EmailConfirmationBase(BaseModel):
    email: EmailStr

class EmailConfirmationCreate(EmailConfirmationBase):
    user_id: int
    confirmation_code: str

class EmailConfirmationRead(EmailConfirmationBase):
    id: int
    user_id: int
    expires_at: datetime
    created_at: datetime
    used: bool

    class Config:
        from_attributes = True  # Enables ORM mode

class EmailConfirmationUpdate(BaseModel):
    used: bool


class SearchBestRoute(BaseModel):

    passanger_current_location: List[float]
    passanger_route: List[List[float]]

class SearchRouteResults(BaseModel):
    ride_id: int
    best_ride_: List[List[float]]
    ride_price: float
