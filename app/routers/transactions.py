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
