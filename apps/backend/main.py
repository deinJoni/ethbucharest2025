import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import items, users, auth, token_metrics
from core.config import settings
from core.database import create_tables
from routes.wallet import router as wallet_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI backend for ETH Bucharest 2025",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
create_tables()

# Include routers
app.include_router(wallet_router)
app.include_router(token_metrics.router)

@app.get("/")
async def root():
    return {"message": "Welcome to ETH Bucharest 2025 API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
