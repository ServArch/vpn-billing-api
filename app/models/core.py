from sqlalchemy import BigInteger, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Связь один-ко-многим (один юзер -> много конфигов)
    configs: Mapped[list["VPNConfig"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class VPNConfig(Base):
    __tablename__ = "vpn_configs" 

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    config_name: Mapped[str] = mapped_column(String(255))
    uuid_key: Mapped[str] = mapped_column(String(255), unique=True)
    server_location: Mapped[str] = mapped_column(String(20), default="germany")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="configs")
