from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.wallet import Wallet, WalletCreate, WalletResponse

router = APIRouter(
    prefix="/wallets",
    tags=["wallets"]
)

@router.post("/", response_model=WalletResponse)
def create_wallet(wallet: WalletCreate, db: Session = Depends(get_db)):
    """
    Create a new wallet or return existing one if the address already exists
    """
    # Check if wallet already exists
    existing_wallet = db.query(Wallet).filter(Wallet.address == wallet.address).first()
    
    if existing_wallet:
        # Return the existing wallet if found
        return existing_wallet
    
    # Create new wallet if it doesn't exist
    new_wallet = Wallet(address=wallet.address)
    db.add(new_wallet)
    db.commit()
    db.refresh(new_wallet)
    
    return new_wallet

@router.get("/{address}", response_model=WalletResponse)
def get_wallet(address: str, db: Session = Depends(get_db)):
    """
    Get information about a specific wallet
    """
    wallet = db.query(Wallet).filter(Wallet.address == address).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with address {address} not found"
        )
    return wallet
