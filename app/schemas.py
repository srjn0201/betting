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
