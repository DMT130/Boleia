from fastapi import FastAPI
from database import engine, Base
from routers import (user_api_router, booking_api_router, group_api_router,
                     group_member_api_router, review_api_router,
                     rides_api_router, vehicles_api_router, user_auth_api_router
                     #,payment_api_router
                     )

from fastapi.staticfiles import StaticFiles
# Create the database tables
#Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/ProfilePicture", StaticFiles(directory="ProfilePicture"), name="ProfilePicture")
app.mount("/IdentityPicture", StaticFiles(directory="IdentityPicture"), name="IdentityPicture")
app.mount("/DriverPicture", StaticFiles(directory="DriverPicture"), name="DriverPicture")

# Include routers with tags
app.include_router(user_auth_api_router.router, tags=["Login"])
app.include_router(user_api_router.router, tags=["Users"])
app.include_router(vehicles_api_router.router, tags=["Vehicles"])
app.include_router(rides_api_router.router, tags=["Rides"])
app.include_router(booking_api_router.router, tags=["Bookings"])
#app.include_router(payment_api_router.router, tags=["Payments"])
app.include_router(review_api_router.router, tags=["Reviews"])
app.include_router(group_api_router.router, tags=["Group Members"])
app.include_router(group_member_api_router.router, tags=["Groups"])

# Example Health Check Endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "OK"}

# Example root endpoint
@app.get("/", tags=["General"])
def read_root():
    return {"message": "Welcome to the Carpooling API"}