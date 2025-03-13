from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_user = 'postgres'
db_password = 'postgis'
db_host = 'localhost'
db_port = '5432'
db_name = 'boleia'

DATABASE_URL = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

# Create engine with echo=True to log SQL statements (optional, for debugging)
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test connection
try:
    with engine.connect() as connection:
        logger.info("Database connection successful")
except Exception as e:
    logger.error(f"Database connection failed: {str(e)}")