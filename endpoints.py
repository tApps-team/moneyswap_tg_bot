from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from db.base import Base
from db.base import db_dependency


test_router = APIRouter(prefix='/test')


@test_router.get('/test_d')
async def test_directions(request: Request,
                          session: db_dependency):
    Direction = Base.classes.no_cash_direction

    query = await session.execute(select(Direction.valute_from_id,
                                         Direction.valute_to_id))

    print(query.fetchall())

    return 22


@test_router.get('/test_locust')
async def test_directions(request: Request,
                          session: db_dependency,
                          base: str = None):
    ExchangeDirection = Base.classes.no_cash_exchangedirection
    Direction = Base.classes.no_cash_direction
    Valute = Base.classes.general_models_valute


    # print(NoCashExchangeDirections)
    query = await session.execute(select(Valute,
                                         Direction,
                                         ExchangeDirection)\
                                    .join(Direction, Valute.code_name == Direction.valute_from_id)\
                                    .join(ExchangeDirection, Direction.id == ExchangeDirection.direction_id)\
                                    .where(ExchangeDirection.is_active == True,
                                           Direction.valute_from_id == base))
                                    # .distinct(Direction.valute_from_id))
    
    # print(query)
    # print(query.fetchall())
    # print(len(query.fetchall()))
    # print(22)
    for r in query.fetchall():
        for i in range(3): 
            print(r[i].__dict__)
    #     break

    return {'status': 'success'}