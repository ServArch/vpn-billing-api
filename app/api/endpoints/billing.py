from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.core import Tariff, User, Subscription, SubscriptionStatus, VPNConfig
from app.schemas.billing import (
    TariffCreate,
    TariffResponse,
    SubscriptionCreate,
    SubscriptionResponse,
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
    stmt_user = select(User).where(User.telegram_id == sub_in.telegram_id)
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

    # ensure all active configs remain enabled
    stmt_configs = select(VPNConfig).where(VPNConfig.user_id == user.id)
    configs_res = await db.execute(stmt_configs)
    for cfg in configs_res.scalars():
        cfg.is_active = True

    await db.commit()
    await db.refresh(new_sub)
    return new_sub
