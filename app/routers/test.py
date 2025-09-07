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
