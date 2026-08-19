
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.endpoints import users, configs
from app.db.database import engine
from app.models.core import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="VPN Billing API",
    description="REST API for manage VPN users",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(users.router)
app.include_router(configs.router)

@app.get("/ping", tags=["Health"])
async def ping():
    return {"status": "ok", "message": "Server is running!"}
