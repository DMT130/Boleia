# App Porpuse
Carpooling app named Boleia. I will allow drivers to rent for the ride vacant seat to fellow coleges, students or ather people that is going at the same direction.

# App Feature
1. User Registration --Pending
    - Make it mobile first registration
    - For drivers, driver license is mandatory
    - use Face detection model to validate bow faces from ID and Driver license and get customer photo and validate agains the previou two if applicable.
    - add filed for id number and driver license number. Make it simple
2. User ride posting -- Done -- Tested
       Price Calculation
    1. Get rout from front end;
    2. cut the rout with current car location
3. Ride search using, direction, time, rout path and price --Pending
4. pay the ride with mpesa (the driver is only paid after the ride finishs) and collect fees -- Done --Not Tested
5. Price Calculator --Pending


# SEARCH OF RIDES

1. USER INPUT TO THE MAP HIS DESTINATION, THE MAPBOX GENERATE A ROUTE
2. THE MAPBOX SEND A POST REQUEST TO BACKEND WITH:
    1.1. PASSAGER_START_LOCATION
    1.2. PASSAGER_END_LOCATION
    1.3. PASSAGER_ROUTE (WAYPOINT)
3. FINDING PONTENTIAL RAUTES
    1. SEARCH ALL ACTIVE ROUTES
    2. CHECK SIMILARITY OF THE ROUTES AND GIVE A SIMILARITY SCORE
    3. GET THE CAR AZIMOTH TO MAKE SURE IS HEADING TOWARD THE PASSAGER
    4. MEKE SURE THE CAR IS BEHIND THE PASSAGER BY:
    async def search_best_raute(car_current_location, car_route, passager_current_location, passager_route)
       1. clip passager_route by passager_location and car_end_location if car_route is longer else leave it
       2. clip car_route by car_current_location and car_end_location if car_end_location if car_route is longer else clip it by passanger end location
       3. compare the similarity of cliped_passager_route with cliped_car_route
       4. calculate the lenght of cliped_passager_route and cliped_car_route
       5. select the routes with hight similarity score where cliped_car_route is longer than cliped_passager_route which indicate that the car is behind
       5. return the best car raute where the customer can book
