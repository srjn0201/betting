# Project Overview

This project is a backend for a cricket betting application, built with FastAPI, SQLAlchemy, and PostgreSQL. It provides user authentication, role-based access control, user management, and transaction handling.

## File Descriptions and Contents

### `app/__init__.py`
*Description: This empty file serves to mark the `app` directory as a Python package, allowing its modules to be imported using absolute paths (e.g., `from app import models`).*
```python

```

### `app/crud.py`
*Description: This file contains the Create, Read, Update, and Delete (CRUD) operations for interacting with the database models. It abstracts direct database queries, providing functions to manage users, roles, calculate user balances, retrieve user transactions, create new transactions, and fetch user bets. This separation of concerns keeps database logic isolated from the API endpoints.*
```python
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
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


# Transaction CRUD
def get_user_transactions(db: Session, user_id: int):
    return db.query(models.Transaction).filter(
        or_(
            models.Transaction.sender_id == user_id,
            models.Transaction.recipient_id == user_id
        )
    ).order_by(models.Transaction.timestamp.desc()).all()

def create_transaction(db: Session, transaction: schemas.TransactionCreate) -> models.Transaction:
    """Creates a new transaction record in the database."""
    db_transaction = models.Transaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


# Bet CRUD
def get_user_bets(db: Session, user_id: int):
    return db.query(models.Bet).filter(models.Bet.user_id == user_id).order_by(models.Bet.id.desc()).all()

def create_bet(db: Session, bet: schemas.BetCreate, user_id: int) -> models.Bet:
    """
    Creates a new bet record in the database.
    """
    db_bet = models.Bet(
        **bet.model_dump(), 
        user_id=user_id,
        status='ACTIVE'  # Bets are always active when created
    )
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)
    return db_bet
```

### `app/database.py`
*Description: This file is responsible for setting up the database connection using SQLAlchemy. It loads the database URL from environment variables, creates the engine, and defines `SessionLocal` for managing database sessions and `Base` for declarative model definitions. This centralizes database configuration.*
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
*Description: This is the main entry point for the FastAPI application. It initializes the FastAPI app instance and includes various API routers (e.g., for users, transactions, testing, and bets). This file acts as the central orchestrator for the API, bringing together different functional modules.*
```python
from fastapi import FastAPI
from .routers import users, transactions, test, bets

# models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include routers
app.include_router(users.auth_router) # For /token
app.include_router(users.user_router) # For /users
app.include_router(transactions.router) # For /transactions
app.include_router(test.router) # For /test
app.include_router(bets.router) # For /bets

@app.get("/")
def read_root():
    return {"message": "Welcome to the Cricket Betting App"}
```

### `app/models.py`
*Description: This file defines the SQLAlchemy ORM models that map to the database tables. It includes models for `User`, `Role`, `Transaction`, `Bet`, and `TokenBlocklist`, establishing relationships between them. This defines the structure of the data stored in the database.*
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
*Description: This file defines Pydantic models, which are used for data validation, serialization, and deserialization throughout the API. These schemas ensure that incoming request data and outgoing response data conform to expected structures and types, improving data integrity and API reliability. It includes schemas for Users, Roles, Transactions, Bets, and Token handling, as well as a detailed `UserDetailsResponse` for administrative purposes.*
```python
from pydantic import BaseModel, ConfigDict
from typing import Optional , List
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


# --- Bet Schemas ---
class Bet(BaseModel):
    id: int
    fixture_id: int
    market_name: str
    odds: float
    stake: float
    status: str # Consider using an Enum here in the future
    model_config = ConfigDict(from_attributes=True)


class BetCreate(BaseModel):
    fixture_id: int
    market_name: str
    odds: float
    stake: float




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




# --- Admin/Test Schemas ---
class UserDetailsResponse(BaseModel):
    profile: User
    balance: float
    children: List[User]
    transactions: List[Transaction]
    bets: List[Bet]
```

### `app/security.py`
*Description: This file provides utilities for security-related operations, including password hashing using `bcrypt` and JSON Web Token (JWT) creation and verification. It ensures secure user authentication and authorization within the application.*
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
*Description: This script is designed for initial database setup. It creates all necessary tables based on the SQLAlchemy models and seeds the database with predefined roles (admin, master, dealer, player) and initial admin/master user accounts. It also includes logic to create an initial coin deposit for the admin user, ensuring a consistent starting state for the application's database.*
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
        parent_user_id=None
    )
    session.add(admin_user)
    session.flush()

    # 2. Create Master User
    master_role = session.query(Role).filter_by(name='master').one()
    master_user = User(
        username="master",
        hashed_password=security.get_password_hash("masterpassword"),
        role_id=master_role.id,
        parent_user_id=admin_user.id
    )
    session.add(master_user)
    
    # --- ADD THIS LOGIC ---
    # 3. Create the Admin's initial deposit
    print("Creating initial 1,000,000 coin deposit for admin...")
    admin_deposit = Transaction(
        sender_id=None,  # No sender, as it's a system deposit
        recipient_id=admin_user.id,
        amount=1000000,
        transaction_type="SYSTEM_DEPOSIT"
    )
    session.add(admin_deposit)
    # -----------------------
    
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

### `app/routers/transactions.py`
*Description: This router defines API endpoints related to financial transactions, specifically for transferring coins between users. It includes logic for validating sender permissions, recipient existence, and sufficient balance, ensuring that coin transfers adhere to the application's business rules.*
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..routers.users import get_current_user, get_db, ROLE_HIERARCHY

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/transfer", status_code=status.HTTP_201_CREATED)
def transfer_coins(transfer_request: schemas.CoinTransferRequest, db: Session = Depends(get_db), sender: models.User = Depends(get_current_user)):
    """Transfers coins from the authenticated user to a recipient."""
    
    # 1. Players cannot transfer coins
    if sender.role.name == 'player':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Players are not allowed to transfer coins."
        )

    # 2. Find recipient
    recipient = crud.get_user_by_username(db, username=transfer_request.recipient_username)
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient user '{transfer_request.recipient_username}' not found."
        )

    # 3. Enforce hierarchy
    sender_level = ROLE_HIERARCHY.get(sender.role.name)
    if sender.role.name != 'admin': # Admins can transfer to anyone
        if recipient.parent_user_id != sender.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only transfer coins to users you have created."
            )

    # 4. Check balance
    sender_balance = crud.get_user_balance(db, user_id=sender.id)
    if sender_balance < transfer_request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance."
        )

    # 5. Create debit and credit transactions
    debit_tx = schemas.TransactionCreate(
        sender_id=sender.id,
        recipient_id=recipient.id,
        amount=transfer_request.amount,
        transaction_type='TRANSFER_DEBIT'
    )
    credit_tx = schemas.TransactionCreate(
        sender_id=sender.id,
        recipient_id=recipient.id,
        amount=transfer_request.amount,
        transaction_type='TRANSFER_CREDIT'
    )
    
    db.add(models.Transaction(**debit_tx.model_dump()))
    db.add(models.Transaction(**credit_tx.model_dump()))
    db.commit()

    return {"message": f"Successfully transferred {transfer_request.amount} coins to {recipient.username}."}
```

### `app/routers/users.py`
*Description: This router handles user-related API endpoints, including user authentication (login), user creation, and retrieving user information (e.g., current user details, children users). It integrates with security utilities for JWT handling and enforces role-based access control for user management actions.*
```python
from typing import List
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from .. import crud, models, schemas, security
from ..database import SessionLocal

# --- Reusable Dependencies & Configuration ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Role hierarchy definition
ROLE_HIERARCHY = {
    "admin": 1,
    "master": 2,
    "dealer": 3,
    "player": 4
}

def get_db():
    """Dependency to get a DB session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """Dependency to get the current user from a JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# --- Router Definitions ---

# Router for authentication related endpoints (/token)
auth_router = APIRouter(tags=["Authentication"])

# Router for user management endpoints (/users)
# All endpoints in this router will be protected by the get_current_user dependency.
user_router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# --- Authentication Endpoint ---

@auth_router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = security.authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Management Endpoints ---

@user_router.post("/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    creator_role_level = ROLE_HIERARCHY.get(current_user.role.name)
    new_user_role_level = ROLE_HIERARCHY.get(user.role)

    if not creator_role_level or not new_user_role_level:
        raise HTTPException(status_code=400, detail="Invalid role specified.")

    if creator_role_level >= new_user_role_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a user with this role."
        )

    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_role = crud.get_role_by_name(db, role_name=user.role)
    if not db_role:
        raise HTTPException(status_code=400, detail=f"Role '{user.role}' does not exist")

    user.parent_username = current_user.username

    created_user = crud.create_user(db=db, user=user)
    if created_user is None:
        raise HTTPException(status_code=500, detail="Could not create user.")
        
    return created_user


@user_router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@user_router.get("/me/children", response_model=List[schemas.User])
def read_user_children(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    children = crud.get_user_children(db, user_id=current_user.id)
    return children


@user_router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """An unprotected endpoint to verify router health."""
    return {"status": "ok"}
```

### `app/routers/test.py`
*Description: This router provides an administrative endpoint for retrieving comprehensive details about a specific user, including their profile, balance, children users, transactions, and bets. It is intended for testing and debugging purposes and is restricted to admin users.*
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..routers.users import get_current_user, get_db

router = APIRouter(
    prefix="/test",
    tags=["Testing"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/user-details/{username}", response_model=schemas.UserDetailsResponse)
def get_user_full_details(username: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Provides a complete dump of a user's details. 
    **This is an admin-only endpoint.**
    """
    # 1. Admin-only check
    if current_user.role.name != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )

    # 2. Get the target user
    target_user = crud.get_user_by_username(db, username=username)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found."
        )

    # 3. Gather all related data
    balance = crud.get_user_balance(db, user_id=target_user.id)
    children = crud.get_user_children(db, user_id=target_user.id)
    transactions = crud.get_user_transactions(db, user_id=target_user.id)
    bets = crud.get_user_bets(db, user_id=target_user.id)

    # 4. Assemble and return the response
    response = schemas.UserDetailsResponse(
        profile=target_user,
        balance=balance,
        children=children,
        transactions=transactions,
        bets=bets
    )

    return response
```

### `app/routers/bets.py`
*Description: This router handles API endpoints related to placing bets. It includes logic for validating the user's role (only players can place bets), checking their balance, creating a debit transaction for the stake, and recording the bet. This ensures that betting operations are properly managed and recorded.*
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..routers.users import get_current_user, get_db

router = APIRouter(
    prefix="/bets",
    tags=["Bets"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=schemas.Bet, status_code=status.HTTP_201_CREATED)
def place_bet(bet: schemas.BetCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Places a new bet for the authenticated user."""
    
    # 1. Verify user role is 'player'
    if current_user.role.name != 'player':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users with the 'player' role can place bets."
        )

    # 2. Check player's balance
    balance = crud.get_user_balance(db, user_id=current_user.id)
    if balance < bet.stake:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Current balance: {balance}, required: {bet.stake}"
        )

    # 3. Create debit transaction for the bet stake
    # For this, we need a recipient for the funds, the "house".
    # We will use the primary admin user as the house/system recipient.
    admin_user = crud.get_user_by_username(db, username="admin")
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System admin user not found. Cannot place bet."
        )

    stake_transaction = schemas.TransactionCreate(
        sender_id=current_user.id,
        recipient_id=admin_user.id, # Money goes to the house (admin)
        amount=bet.stake,
        transaction_type='BET_STAKE'
    )
    crud.create_transaction(db, transaction=stake_transaction)

    # 4. Create the bet record
    new_bet = crud.create_bet(db, bet=bet, user_id=current_user.id)

    # 5. Return the newly created bet
    return new_bet
```

### `requirements.txt`
*Description: This file lists the Python dependencies required for the project. It ensures that all necessary libraries and their versions are installed, facilitating consistent development and deployment environments.*
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