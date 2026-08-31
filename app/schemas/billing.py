from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.models.core import SubscriptionStatus, PaymentStatus


class TariffBase(BaseModel):
    slug: str
    name: str
    duration_days: int = Field(gt=0)
    price_rub: Decimal = Field(gt=0)
    traffic_limit_gb: int | None = None
    device_limit: int = 2


class TariffCreate(TariffBase):
    pass


class TariffResponse(TariffBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreate(BaseModel):
    telegram_id: int
    tariff_slug: str
    auto_renew: bool = False


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    tariff_id: int
    starts_at: datetime
    expires_at: datetime
    status: SubscriptionStatus
    auto_renew: bool

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    telegram_id: int
    amount: Decimal
    currency: str = "RUB"
    external_payment_id: str


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    external_payment_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
