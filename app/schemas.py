from pydantic import BaseModel, ConfigDict
from typing import Optional

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

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
