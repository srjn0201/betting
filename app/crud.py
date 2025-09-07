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


# Bet CRUD
def get_user_bets(db: Session, user_id: int):
    return db.query(models.Bet).filter(models.Bet.user_id == user_id).order_by(models.Bet.id.desc()).all()
