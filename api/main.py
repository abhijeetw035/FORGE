import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import repositories, analytics, auth
from database import engine
from models import Base

app = FastAPI(title="FORGE API", version="0.1.0")

# Only the configured browser origins may call the API (comma-separated env var).
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(repositories.router)
app.include_router(analytics.router)

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "FORGE API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
