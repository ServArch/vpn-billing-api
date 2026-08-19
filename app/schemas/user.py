
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    telegram_id: int   # mb should we use BigInt?? or is it only need in sqlalchemy and databases?
    username: str | None = None

class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None = None
    subscription_expires_at: datetime | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
