from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr

from core.database import Base

class Wallet(Base):
    __tablename__ = "wallets"
    
    address = Column(String, primary_key=True, index=True)
    user_username = Column(String, ForeignKey("users.username"), nullable=False)
    user = relationship("User", back_populates="wallets")
    
class User(Base):
    __tablename__ = "users"
    
    username = Column(String, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")

# Pydantic models for request/response handling
class WalletBase(BaseModel):
    address: str
    
class UserBase(BaseModel):
    username: str
    
class UserCreate(UserBase):
    password: str
    wallet_addresses: list[str] = None
    
class UserLogin(BaseModel):
    username: str
    password: str
    
class UserResponse(UserBase):
    wallets: list[WalletBase] = []
    
    model_config = {
        "from_attributes": True 
    }

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    username: str = None
