from enum import Enum


class EventNotificatonEnum(str, Enum):
    # REVIEW_OWNER = 'review_owner'
    REVIEW_EXCHANGE_ADMIN = 'review_exchange_admin'
    COMMENT_OWNER = 'comment_owner'
    COMMENT_EXCHANGE_ADMIN = 'comment_exchange_admin'
    # ADMIN_COMMENT = 'admin_comment'