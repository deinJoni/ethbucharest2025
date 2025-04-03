from fastapi import APIRouter, HTTPException, Depends
from typing import List

from schemas.item import Item, ItemCreate
from core.config import settings

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/items",
    tags=["items"],
)

# In-memory items database for demo
items_db = []

@router.get("/", response_model=List[Item])
async def read_items():
    return items_db

@router.post("/", response_model=Item)
async def create_item(item: ItemCreate):
    new_item = Item(id=len(items_db) + 1, **item.model_dump())
    items_db.append(new_item)
    return new_item

@router.get("/{item_id}", response_model=Item)
async def read_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")
