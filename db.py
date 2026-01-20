from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings
from models import Base

# Отримуємо виправлений URL через метод, який ми додали в config.py
# Це гарантує використання драйвера asyncpg замість psycopg2
engine = create_async_engine(settings.get_db_url(), echo=False)

async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db():
    """Ініціалізація бази даних (створення таблиць)"""
    async with engine.begin() as conn:
        # Створює всі таблиці, описані в models.py, якщо їх ще немає
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    """Отримати асинхронну сесію для роботи з БД"""
    async with async_session_maker() as session:
        yield session