from aiogram import Router

from bot.handlers import start, tasks

router = Router()
router.include_routers(start.router, tasks.router)
