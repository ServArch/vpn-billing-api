from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.endpoints import users, configs, billing, support
from app.db.database import engine
from app.models.core import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="VPN Billing API",
    description="Async VPN billing microservice & RAG-based technical support engine",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(configs.router)
app.include_router(billing.router)
app.include_router(support.router)


@app.get("/ping", tags=["Health"])
async def ping():
    return {"status": "ok", "service": "vpn-billing-api"}
