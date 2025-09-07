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
