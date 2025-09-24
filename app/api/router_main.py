from fastapi import APIRouter

from app.api.routes import files, chat, info

api_router = APIRouter()
api_router.include_router(files.router)
api_router.include_router(chat.router)
api_router.include_router(info.router)