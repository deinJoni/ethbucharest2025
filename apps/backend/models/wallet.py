from sqlalchemy import Column, String, Enum
import enum
from pydantic import BaseModel, Field
from typing import Optional, Annotated

from core.database import Base

class RiskProfile(str, enum.Enum):
    HIGH_RISK = "HIGH_RISK"
    BALANCED = "BALANCED"
    SAFE = "SAFE"
    
    @classmethod
    def get_display_name(cls, value):
        display_names = {
            cls.HIGH_RISK: "High Risk, High Reward",
            cls.BALANCED: "Balanced & Strategic",
            cls.SAFE: "Safe & Steady"
        }
        return display_names.get(value, str(value))

class Wallet(Base):
    __tablename__ = "wallets"
    
    address = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    risk_profile = Column(Enum(RiskProfile), nullable=True)

# Pydantic models for request/response handling
class WalletBase(BaseModel):
    address: str
    name: Optional[str] = None
    risk_profile: Optional[RiskProfile] = None
    
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
