from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from . import crud, models, schemas, security
from .database import SessionLocal, engine

# This command creates the database tables, 
# but we are now using the initialize_database.py script.
# models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints ---

@app.post("/token", response_model=schemas.Token)
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


@app.get("/")
def read_root():
    return {"message": "Welcome to the Cricket Betting App"}


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if role exists
    db_role = crud.get_role_by_name(db, role_name=user.role)
    if not db_role:
        raise HTTPException(status_code=400, detail=f"Role '{user.role}' does not exist")

    # Check if parent user exists
    if user.parent_username:
        db_parent = crud.get_user_by_username(db, username=user.parent_username)
        if not db_parent:
            raise HTTPException(status_code=400, detail=f"Parent user '{user.parent_username}' not found")

    created_user = crud.create_user(db=db, user=user)
    if created_user is None:
        raise HTTPException(status_code=400, detail="Could not create user")
        
    return created_user