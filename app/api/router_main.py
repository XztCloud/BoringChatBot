from fastapi import APIRouter

from app.api.routes import files, chat, info, configure

api_router = APIRouter()
api_router.include_router(files.router)
api_router.include_router(chat.router)
api_router.include_router(info.router)
api_router.include_router(configure.router)