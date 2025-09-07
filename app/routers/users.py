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
