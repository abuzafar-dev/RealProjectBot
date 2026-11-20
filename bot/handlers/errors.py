import logging

from aiogram import Router
from aiogram.types import ErrorEvent

router = Router(name='errors')
logger = logging.getLogger(__name__)


@router.errors()
async def error_handler(event: ErrorEvent) -> bool:
    """Kutilmagan xatoni logga yozadi va foydalanuvchiga tushunarli javob beradi."""
    logger.exception(
        'Update %s ni qayta ishlashda xato', event.update.update_id, exc_info=event.exception
    )
    text = "Kutilmagan xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."
    if event.update.callback_query:
        await event.update.callback_query.answer(text, show_alert=True)
    elif event.update.message:
        await event.update.message.answer(text)
    return True
