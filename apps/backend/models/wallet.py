from sqlalchemy import Column, String
from pydantic import BaseModel

from core.database import Base

class Wallet(Base):
    __tablename__ = "wallets"
    
    address = Column(String, primary_key=True, index=True)

# Pydantic models for request/response handling
class WalletBase(BaseModel):
    address: str
    
class WalletCreate(WalletBase):
    pass
    
class WalletResponse(WalletBase):
    model_config = {
        "from_attributes": True 
    }

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    wallet_address: str = None
