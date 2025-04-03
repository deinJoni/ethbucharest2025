from pydantic import BaseModel
from fastapi import APIRouter
from core.config import settings
from core.token_metrics import get_token_metrics

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/token-metrics",
    tags=["token-metrics"],
)

class TokenRequest(BaseModel):
    token_id: str

@router.post("/ai-report")
async def test(request: TokenRequest):
    return get_token_metrics(request.token_id)
