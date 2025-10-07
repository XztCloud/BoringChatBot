from fastapi import APIRouter

from app.api.routes import files, chat, info, configure, login, user, titles

api_router = APIRouter()

api_router.include_router(chat.router)
api_router.include_router(info.router)
api_router.include_router(configure.router)
api_router.include_router(login.router)
api_router.include_router(user.router)
api_router.include_router(titles.router)
api_router.include_router(files.router)