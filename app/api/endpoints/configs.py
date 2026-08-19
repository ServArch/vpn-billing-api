import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.vpn_config import VpnConfigCreate, VpnConfigResponse
from app.models.core import VPNConfig, User
from app.db.database import get_db

router = APIRouter(prefix="/configs", tags=["VPN Configs"])


@router.post("/", response_model=VpnConfigResponse)
async def create_config(config_in: VpnConfigCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем, существует ли юзер (Foreign Key Validation)
    stmt = select(User).where(User.id == config_in.user_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Генерируем UUID ключ для Xray (он создается на стороне бэкенда, а не юзером)
    new_uuid = str(uuid.uuid4())

    new_config = VPNConfig(
        user_id=config_in.user_id,
        config_name=config_in.config_name,
        server_location=config_in.server_location,
        uuid_key=new_uuid
    )

    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)

    return new_config


@router.get("/user/{user_id}", response_model=list[VpnConfigResponse])
async def get_user_configs(user_id: int, db: AsyncSession = Depends(get_db)):
    # Вытягиваем все активные конфиги конкретного пользователя
    stmt = select(VPNConfig).where(
        VPNConfig.user_id == user_id,
        VPNConfig.is_active == True
    )
    result = await db.execute(stmt)
    return result.scalars().all()