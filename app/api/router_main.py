from fastapi import APIRouter

from app.api.routes import files, chat

api_router = APIRouter()
api_router.include_router(files.router)
api_router.include_router(chat.router)