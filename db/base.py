from typing import Annotated

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from fastapi import Depends

from config import db_url, sync_db_url


Base = automap_base()

engine = create_engine(sync_db_url,
                       echo=True)

Base.prepare(autoload_with=engine)
# Base.prepare(engine, reflect=True)

# engine.dispose()

# (print(Base))
# print(Base.__dict__)
# print(Base.metadata.__dict__)

async_engine = create_async_engine(db_url, echo=True)

# Base.prepare(engine, reflect=True)

session = sessionmaker(engine, expire_on_commit=False)

async_session = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_async_session():
    async with async_session() as session:
        yield session


db_dependency = Annotated[AsyncSession, Depends(get_async_session)]