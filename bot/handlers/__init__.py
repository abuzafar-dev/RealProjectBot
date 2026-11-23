from aiogram import F, Router
from aiogram.enums import ChatType

from bot.handlers import errors, settings, start, tasks, tools


def get_router() -> Router:
    router = Router(name='root')
    # Shaxsiy yordamchi: guruhda vazifalar va eslatmalar aralashib ketadi, shuning uchun
    # faqat shaxsiy chat xabarlari qayta ishlanadi
    router.message.filter(F.chat.type == ChatType.PRIVATE)
    # settings tasks'dan oldin: «⚙️ Sozlamalar» matni tez qo'shishga (vazifa nomiga) tushmasin
    router.include_routers(start.router, settings.router, tools.router, tasks.router, errors.router)
    return router
