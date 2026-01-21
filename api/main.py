from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import repositories
from database import engine
from models import Base

app = FastAPI(title="FORGE API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repositories.router)

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "FORGE API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
