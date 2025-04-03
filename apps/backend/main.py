import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import items, users, auth
from core.config import settings

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

# Include routers
app.include_router(items.router)
app.include_router(users.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Welcome to ETH Bucharest 2025 API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
