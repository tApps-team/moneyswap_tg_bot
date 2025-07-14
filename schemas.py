from pydantic import BaseModel


class ExchangeAdminNotification(BaseModel):
    user_id: int
    text: str