from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import db_url, async_db_url

# Создаём базу для автомаппинга
Base = automap_base()


engine = create_async_engine(
    async_db_url,
    pool_size=10,          # число постоянных соединений в пуле
    max_overflow=20,       # доп. соединения при пиках нагрузки
    pool_timeout=30,       # таймаут ожидания соединения
    echo=True,            # можно поставить True для логов SQL
)

# Асинхронная сессия
async_session_maker = sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# Рефлексия схемы (требует отдельного подключения)
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.prepare(autoload_with=sync_conn))
    print("✅ Database schema reflected successfully.")

# Пример получения сессии
async def get_session():
    async with async_session_maker() as session:
        yield session