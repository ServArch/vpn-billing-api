from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

# Путь к нашему локальному файлику базы данных SQLite
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./vpn_service.db"

# Создаем движок. echo=True означает, что все SQL-запросы будут выводиться в терминал.
# Это супер полезно для дебага и понимания, что происходит под капотом.
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Фабрика сессий
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# Эта функция будет выдавать новую сессию БД для каждого запроса к нашему API
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session