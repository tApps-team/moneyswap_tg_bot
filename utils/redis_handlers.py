from aiogram import Router, types, Bot, F

from sqlalchemy import insert, select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards import new_create_kb_for_exchange_admin_review

from db.base import Base



grade_dict = {
    '1': 'Положительный',
    '0': 'Нейтральный',
    '-1': 'Отрицательный',
}

async def new_send_review_notification_to_exchange_admin(user_id: int,
                                                  exchange_id: int,
                                                  review_id: int,
                                                  session: AsyncSession,
                                                  bot: Bot):
    Review = Base.classes.general_models_review
    Exchange = Base.classes.general_models_exchanger

    query = (
        select(
            Review,
            Exchange,
        )\
        .select_from(Review)\
        .join(Exchange,
              Review.exchange_id == Exchange.id)\
        .where(Review.id == review_id)
    )
    async with session as _session:
        res = await _session.execute(query)

        review_data = res.fetchall()

    if not review_data:
        print(f'ERROR, REVIEW NOT FOUND BY GIVEN "review_id" {review_id}')
        return
    else:
        review, exchange = review_data[0]
    
    # if review.grade == '1':
    #     _grade = 'Положительный'
    # elif review.grade == '0':
    #     _grade = 'Нейтральный'
    # elif review.grade == '-1':
    #     _grade = 'Отрицательный'
    _grade = grade_dict.get(review.grade)

    _text = f'💬 Новый отзыв на прикрепленный обменник {exchange.name}\n\n<b>Оценка:</b> {_grade}'

    if review.transaction_id:
        _text += f'\n<b>Номер транзакции:</b> {review.transaction_id}\n\n📌 Просим вас оперативно отреагировать — ситуация находится на контроле администрации <b>MoneySwap</b>.'

    _text += '\n\nПерейти к отзыву можно по кнопке ниже👇'

    _kb = new_create_kb_for_exchange_admin_review(exchange_id=exchange_id,
                                                  review_id=review_id)
    try:
        await bot.send_message(chat_id=user_id,
                               text=_text,
                               reply_markup=_kb.as_markup())
        update_query = (
            update(
                Review
            )\
            .values(has_send_to_admin=True)\
            .where(
                Review.id == review_id,
            )
        )
        async with session as _session:
            await _session.execute(update_query)
            await _session.commit()
        print(f'SEND TO EXCHANGE ADMIN REVIEW NOTIFICATION {_text}')
    except Exception as ex:
        print(f'ERROR WITH TRY SEND MESSAGE TO EXCHANGE ADMIN REVIEW NOTIFICATION {_text}', ex)