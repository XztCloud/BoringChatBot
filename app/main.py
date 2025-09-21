from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.router_main import api_router

app = FastAPI(
    title="BoringChatbot",
    openapi_url="/api/v1/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
)

app.include_router(api_router, prefix="/api/v1", tags=["api"])