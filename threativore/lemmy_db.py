from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from threativore.config import Config
from loguru import logger

# Define the base for the ORM models
Base = declarative_base()

# Define the LocalUser model
class LemmyLocalUser(Base):
    __tablename__ = 'local_user'
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)

# Define the Person model
class LemmyPerson(Base):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True)
    actor_id = Column(String(255), nullable=False, unique=True)

# Database connection string for the second PostgreSQL database with read-only mode
DATABASE_URL = f"postgresql://{Config.lemmy_db_username}:{Config.lemmy_db_password}@{Config.lemmy_db_host}/{Config.lemmy_db_database}?options=-c%20default_transaction_read_only=on"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
Session = sessionmaker(bind=engine)

# Create a session
session = Session()

def get_actor_id_from_email(email):
    # Query the LocalUser table to get the person_id
    local_user = session.query(LemmyLocalUser).filter(LemmyLocalUser.email == email).first()
    if not local_user:
        logger.info(f"LocalUser with person_id {email} not found")
        return None

    # Query the Person table to get the actor_id using the person_id
    person = session.query(LemmyPerson).filter(LemmyPerson.id == local_user.person_id).first()
    if not person:
        return None

    return person.actor_id

