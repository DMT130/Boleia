from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Enum, Text, JSON, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import enum
from database import Base

# ----- Enums -----
class UserRole(str, enum.Enum):
    DRIVER = "DRIVER"
    PASSENGER = "PASSENGER"
    BOTH = "BOTH"

class RideStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

# ----- Tables -----
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True)
    identity_id = Column(String(100), nullable=False, unique=True)
    driver_license = Column(String(100), nullable=True, unique=True)
    role = Column(Enum(UserRole), default=UserRole.BOTH)
    user_is_verified = Column(Boolean, default=False)
    documents_is_verified = Column(Boolean, default=False)
    profile_image = Column(Text, nullable=True)
    identity_id_file = Column(Text, nullable=True)
    driver_license_file = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    vehicles = relationship("Vehicle", back_populates="owner")
    rides_driven = relationship("Ride", back_populates="driver")
    bookings = relationship("Booking", back_populates="passenger")
    reviews_given = relationship("Review", foreign_keys="Review.reviewer_id", back_populates="reviewer")
    reviews_received = relationship("Review", foreign_keys="Review.reviewee_id", back_populates="reviewee")
    groups = relationship("GroupMember", back_populates="user")

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer)
    color = Column(String(20))
    license_plate = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    insurance_document = Column(String(255))  # URL to document
    created_at = Column(DateTime, server_default=func.now())
    
    owner = relationship("User", back_populates="vehicles")
    rides = relationship("Ride", back_populates="vehicle")

class Ride(Base):
    __tablename__ = "rides"
    
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    start_location = Column(Geometry(geometry_type="POINT", srid=4326))  # Changed to JSONB
    end_location = Column(Geometry(geometry_type="POINT", srid=4326))    # Changed to JSONB
    waypoints = Column(Geometry(geometry_type="LINESTRING", srid=4326))                       # Changed to JSONB for consistency
    departure_time = Column(DateTime, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price_per_seat = Column(Float, nullable=False)
    status = Column(Enum(RideStatus), default=RideStatus.SCHEDULED)
    is_recurring = Column(Boolean, default=False)
    recurring_pattern = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    driver = relationship("User", back_populates="rides_driven")
    vehicle = relationship("Vehicle", back_populates="rides")
    bookings = relationship("Booking", back_populates="ride")
    reviews = relationship("Review", back_populates="ride")  # Add this line
    
    # Indexes
    __table_args__ = (
        Index("ix_rides_departure_status", "departure_time", "status"),
        Index("ix_geo_search", "start_location", "end_location", postgresql_using="gist")
    )

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=False)
    passenger_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seats_booked = Column(Integer, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    pickup_location = Column(Geometry(geometry_type="POINT", srid=4326))  # Custom pickup point
    dropoff_location = Column(Geometry(geometry_type="POINT", srid=4326))  # Custom dropoff point
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    ride = relationship("Ride", back_populates="bookings")
    passenger = relationship("User", back_populates="bookings")
    payment = relationship("Payment", uselist=False, back_populates="booking")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payment_method = Column(String(50))  # "stripe", "paypal", etc.
    transaction_id = Column(String(255))
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now())
    
    booking = relationship("Booking", back_populates="payment")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True)
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships with explicit back_populates
    ride = relationship("Ride", back_populates="reviews")  # Update to match Ride.reviews
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    reviewee = relationship("User", foreign_keys=[reviewee_id], back_populates="reviews_received", overlaps="reviews_received")

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_verified = Column(Boolean, default=False)  # Verified organizations
    created_at = Column(DateTime, server_default=func.now())

class GroupMember(Base):
    __tablename__ = "group_members"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User", back_populates="groups")
    group = relationship("Group")