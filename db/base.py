# from sqlalchemy.ext.automap import automap_base
# from sqlalchemy.engine import create_engine
# from sqlalchemy.orm import sessionmaker

# from config import db_url


# Base = automap_base()

# engine = create_engine(db_url,
#                        echo=True)

# # Base.prepare(engine, reflect=True)
# Base.prepare(autoload_with=engine)

# session = sessionmaker(engine, expire_on_commit=False)

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import db_url, async_db_url  # пример: 'postgresql+asyncpg://user:password@localhost:5432/dbname'

# Создаём базу для автомаппинга
Base = automap_base()

# Создаём асинхронный движок
engine = create_async_engine(
    async_db_url,
    echo=True,
    future=True
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