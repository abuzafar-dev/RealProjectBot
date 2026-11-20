from aiogram import Router

from bot.handlers import errors, start, tasks


def get_router() -> Router:
    router = Router(name='root')
    router.include_routers(start.router, tasks.router, errors.router)
    return router
