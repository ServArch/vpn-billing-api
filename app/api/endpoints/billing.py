from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.core import Tariff, User, Subscription, SubscriptionStatus, VPNConfig
from app.schemas.billing import (
    TariffCreate,
    TariffResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    UserBillingStatusResponse,
)

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/tariffs", response_model=list[TariffResponse])
async def list_tariffs(db: AsyncSession = Depends(get_db)):
    stmt = select(Tariff).where(Tariff.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/tariffs", response_model=TariffResponse, status_code=status.HTTP_201_CREATED)
async def create_tariff(tariff_in: TariffCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Tariff).where(Tariff.slug == tariff_in.slug)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tariff with this slug already exists")

    tariff = Tariff(**tariff_in.model_dump())
    db.add(tariff)
    await db.commit()
    await db.refresh(tariff)
    return tariff


@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_or_extend_subscription(
    sub_in: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt_user = (
        select(User)
        .options(selectinload(User.configs))
        .where(User.telegram_id == sub_in.telegram_id)
    )
    user_res = await db.execute(stmt_user)
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt_tariff = select(Tariff).where(Tariff.slug == sub_in.tariff_slug, Tariff.is_active == True)
    tariff_res = await db.execute(stmt_tariff)
    tariff = tariff_res.scalar_one_or_none()
    if not tariff:
        raise HTTPException(status_code=404, detail="Active tariff not found")

    now = datetime.now(timezone.utc)
    stmt_active = (
        select(Subscription)
        .where(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at > now,
        )
        .order_by(Subscription.expires_at.desc())
        .limit(1)
    )
    active_sub_res = await db.execute(stmt_active)
    active_sub = active_sub_res.scalar_one_or_none()

    if active_sub:
        base_time = active_sub.expires_at
        expires_at = base_time + timedelta(days=tariff.duration_days)
    else:
        expires_at = now + timedelta(days=tariff.duration_days)

    new_sub = Subscription(
        user_id=user.id,
        tariff_id=tariff.id,
        starts_at=now,
        expires_at=expires_at,
        status=SubscriptionStatus.ACTIVE,
        auto_renew=sub_in.auto_renew,
    )
    db.add(new_sub)

    for cfg in user.configs:
        cfg.is_active = True

    await db.commit()
    await db.refresh(new_sub)
    return new_sub


@router.get("/status/{telegram_id}", response_model=UserBillingStatusResponse)
async def get_user_billing_status(telegram_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(User)
        .options(
            selectinload(User.subscriptions),
            selectinload(User.configs),
        )
        .where(User.telegram_id == telegram_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    active_subs = [s for s in user.subscriptions if s.status == SubscriptionStatus.ACTIVE and s.expires_at > now]
    latest_expiry = max((s.expires_at for s in active_subs), default=None)
    active_configs = [c for c in user.configs if c.is_active]

    return UserBillingStatusResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        is_active=user.is_active,
        has_active_subscription=bool(active_subs),
        subscription_expires_at=latest_expiry,
        active_configs_count=len(active_configs),
        configs=[
            {
                "id": c.id,
                "name": c.config_name,
                "location": c.server_location,
                "protocol": c.protocol,
                "is_active": c.is_active,
            }
            for c in active_configs
        ],
    )
