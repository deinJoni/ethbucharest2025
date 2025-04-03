from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from models.wallet import Wallet, WalletCreate, WalletResponse, RiskProfile

router = APIRouter(
    prefix="/wallets",
    tags=["wallets"]
)

class RiskProfileUpdate(BaseModel):
    address: str
    risk_profile: RiskProfile

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
    Get information about a specific wallet including risk profile if available
    """
    wallet = db.query(Wallet).filter(Wallet.address == address).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with address {address} not found"
        )
    return wallet

@router.put("/risk-profile", response_model=WalletResponse)
def update_risk_profile(update_data: RiskProfileUpdate, db: Session = Depends(get_db)):
    """
    Update the risk profile for a specific wallet
    
    Example request body:
    {
        "address": "0xabc123...",
        "risk_profile": "High Risk, High Reward"
    }
    
    Valid risk_profile values: 
    - "High Risk, High Reward" (for HIGH_RISK)
    - "Balanced & Strategic" (for BALANCED)
    - "Safe & Steady" (for SAFE)
    """
    wallet = db.query(Wallet).filter(Wallet.address == update_data.address).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet with address {update_data.address} not found"
        )
    
    wallet.risk_profile = update_data.risk_profile
    db.commit()
    db.refresh(wallet)
    
    return wallet
