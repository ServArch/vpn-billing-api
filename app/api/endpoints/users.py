from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.user import UserCreate, UserResponse
from app.models.core import User
from app.db.database import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Ищем, есть ли уже такой юзер
    stmt = select(User).where(User.telegram_id == user_in.telegram_id)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    # 2. Если есть — выкидываем ошибку (нельзя зарегистрировать дважды)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this telegram_id already exists")

    # 3. Если нет — создаем нового
    new_user = User(
        telegram_id=user_in.telegram_id,
        username=user_in.username
    )

    # 4. Сохраняем в базу
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)  # Обновляем объект, чтобы база вписала ему сгенерированный ID

    return new_user
