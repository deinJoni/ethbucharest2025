from fastapi import APIRouter, HTTPException, Depends
from typing import List

from schemas.user import User, UserCreate
from core.config import settings

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/users",
    tags=["users"],
)

# In-memory users database for demo
users_db = []

@router.get("/", response_model=List[User])
async def read_users():
    return users_db

@router.post("/", response_model=User)
async def create_user(user: UserCreate):
    new_user = User(id=len(users_db) + 1, **user.model_dump())
    users_db.append(new_user)
    return new_user

@router.get("/{user_id}", response_model=User)
async def read_user(user_id: int):
    for user in users_db:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")
