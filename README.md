# Project Overview

This project is a backend for a cricket betting application, built with FastAPI, SQLAlchemy, and PostgreSQL.

## File Descriptions and Contents

### `app/__init__.py`
*Description: This file marks the `app` directory as a Python package.*
```python

```

### `app/crud.py`
*Description: This file contains Create, Read, Update, and Delete (CRUD) operations for interacting with the database, specifically for User and Role models.*
```python
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas, security


# User CRUD
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = security.get_password_hash(user.password)
    
    # Get role object from role name
    db_role = get_role_by_name(db, user.role)
    if not db_role:
        return None # Role not found
        
    # Get parent user object from parent username
    parent_id = None
    if user.parent_username:
        db_parent = get_user_by_username(db, user.parent_username)
        if not db_parent:
            return None # Parent user not found
        parent_id = db_parent.id

    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role_id=db_role.id,
        parent_user_id=parent_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_children(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.parent_user_id == user_id).all()


def get_user_balance(db: Session, user_id: int) -> float:
    """Calculates a user's coin balance by summing their transactions."""
    
    total_credits = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.recipient_id == user_id,
        models.Transaction.transaction_type.in_(['SYSTEM_DEPOSIT', 'TRANSFER_CREDIT'])
    ).scalar() or 0.0

    total_debits = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.sender_id == user_id,
        models.Transaction.transaction_type == 'TRANSFER_DEBIT'
    ).scalar() or 0.0

    return total_credits - total_debits

# Role CRUD
def get_role_by_name(db: Session, role_name: str):
    return db.query(models.Role).filter(models.Role.name == role_name).first()
```

### `app/database.py`
*Description: This file handles the database connection and session management using SQLAlchemy.*
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Get the database URL from the environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable not set. Please create a .env file with DATABASE_URL.")

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for declarative models
Base = declarative_base()
```

### `app/main.py`
*Description: This is the main FastAPI application file, defining the API routes and including other routers.*
```python
from fastapi import FastAPI
from .routers import users, transactions

# models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(users.auth_router) # For /token
app.include_router(users.user_router) # For /users
app.include_router(transactions.router) # For /transactions

@app.get("/")
def read_root():
    return {"message": "Welcome to the Cricket Betting App"}
```

### `app/models.py`
*Description: This file defines the SQLAlchemy models for the database tables, including User, Role, Transaction, Bet, and TokenBlocklist.*
```python
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    parent_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    role = relationship("Role", back_populates="users")
    parent = relationship("User", remote_side=[id], back_populates="children")
    children = relationship("User", back_populates="parent")
    
    sent_transactions = relationship("Transaction", foreign_keys="[Transaction.sender_id]", back_populates="sender")
    received_transactions = relationship("Transaction", foreign_keys="[Transaction.recipient_id]", back_populates="recipient")

    bets = relationship("Bet", back_populates="user")




class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system deposits
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sender")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="recipient")


class BetStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"


class Bet(Base):
    __tablename__ = "bets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fixture_id = Column(Integer, nullable=False)
    market_name = Column(String, nullable=False)
    odds = Column(Float, nullable=False)
    stake = Column(Float, nullable=False)
    status = Column(SQLAlchemyEnum(BetStatus), default=BetStatus.ACTIVE, nullable=False)

    user = relationship("User", back_populates="bets")


class TokenBlocklist(Base):
    __tablename__ = "token_blocklist"
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### `app/schemas.py`
*Description: This file defines Pydantic models (schemas) for data validation and serialization, used for API request and response bodies.*
```python
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# Pydantic models (schemas)

class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: str  # Role name e.g., 'player', 'dealer'
    parent_username: Optional[str] = None

class User(UserBase):
    id: int
    role: Role
    parent_user_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# --- Transaction Schemas ---
class TransactionBase(BaseModel):
    amount: float

class TransactionCreate(TransactionBase):
    sender_id: Optional[int] = None
    recipient_id: int
    transaction_type: str

class Transaction(TransactionBase):
    id: int
    sender_id: Optional[int] = None
    recipient_id: int
    transaction_type: str
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Coin Transfer Schemas ---
class CoinTransferRequest(BaseModel):
    recipient_username: str
    amount: float


# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
```

### `app/security.py`
*Description: This file handles password hashing, JWT token creation, and user authentication logic.*
```python
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import crud, models

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)


# --- JWT Configuration ---
SECRET_KEY = "f5ef9aa5d196e2215208e19993f8e427d1f6fc685ac5fb4fd69aa6e5a34dee00"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# --- User Authentication ---
def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Authenticates a user by checking username and password.
    Returns the user object if successful, otherwise None.
    """
    user = crud.get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# --- JWT Creation ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### `app/scripts/initialize_database.py`
*Description: This script is responsible for initializing the database, creating tables, and seeding initial roles and users.*
```python
from sqlalchemy.orm import sessionmaker

from ..database import engine, Base
from ..models import Role, User, Transaction
from .. import security

def seed_roles(session):
    """Seeds the database with default user roles."""
    print("Seeding roles...")
    roles_to_create = ['admin', 'master', 'dealer', 'player']
    
    for role_name in roles_to_create:
        if not session.query(Role).filter_by(name=role_name).first():
            session.add(Role(name=role_name))
    
    session.commit()
    print("Roles seeded successfully.")

def seed_initial_users(session):
    """Seeds the database with initial admin/master users if none exist."""
    user_count = session.query(User).count()
    if user_count > 0:
        print("Users table is not empty. Skipping initial user seeding.")
        return

    print("Users table is empty. Seeding initial admin and master users...")
    
    # 1. Create Admin User
    admin_role = session.query(Role).filter_by(name='admin').one()
    admin_user = User(
        username="admin",
        hashed_password=security.get_password_hash("adminpassword"),
        role_id=admin_role.id,
        parent_user_id=None  # Admin has no parent
    )
    session.add(admin_user)
    session.flush()  # Flush to assign an ID to admin_user before using it

    # 2. Create Master User
    master_role = session.query(Role).filter_by(name='master').one()
    master_user = User(
        username="master",
        hashed_password=security.get_password_hash("masterpassword"),
        role_id=master_role.id,
        parent_user_id=admin_user.id  # Master's parent is the admin
    )
    session.add(master_user)
    
    session.commit()
    print("Default admin and master users created.")

def initialize_database():
    """Main function to initialize the database."""
    print("--- Starting Database Initialization ---")
    
    # 1. Create all tables
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 2. Seed roles first
        seed_roles(session)
        
        # 3. Seed initial users after roles are created
        seed_initial_users(session)
    finally:
        session.close()
        print("--- Database Initialization Complete ---")

# if __name__ == "__main__":
#     initialize_database()       # 2. Seed roles first
#     seed_roles(session)
        
#         # 3. Seed initial users after roles are created
#     seed_initial_users(session)
#     finally:
#     session.close()
#     print("--- Database Initialization Complete ---")

if __name__ == "__main__":
    initialize_database()
```

### `requirements.txt`
*Description: This file lists the Python dependencies required for the project.*
```
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
python-dotenv
passlib[bcrypt]
python-jose[cryptography]
python-multipart
sqlalchemy-utils
```