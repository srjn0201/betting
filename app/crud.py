from sqlalchemy.orm import Session
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

# Role CRUD
def get_role_by_name(db: Session, role_name: str):
    return db.query(models.Role).filter(models.Role.name == role_name).first()
