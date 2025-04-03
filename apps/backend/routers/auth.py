from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from core.security import verify_password, get_password_hash, create_access_token, oauth2_scheme
from models.user import User, UserCreate, UserResponse, UserLogin, Token, Wallet
import jwt
from core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.username == user_data.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create wallet if address was provided
    if user_data.wallet_address:
        wallet = Wallet(address=user_data.wallet_address)
        db.add(wallet)
        db.commit()
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        wallet_address=user_data.wallet_address
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/connect-wallet")
async def connect_wallet(wallet_address: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if wallet exists
    wallet = db.query(Wallet).filter(Wallet.address == wallet_address).first()
    if not wallet:
        wallet = Wallet(address=wallet_address)
        db.add(wallet)
        
    current_user.wallet_address = wallet_address
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Wallet connected successfully"}
