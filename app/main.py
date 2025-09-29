from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.router_main import api_router
from app.retriever.llm_manager import llm_manager
from app.retriever.load_file_thread import load_file_thread
from app.retriever.query_answers import query_answers

app = FastAPI(
    title="BoringChatbot",
    openapi_url="/api/v1/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    llm_manager.load()
    load_file_thread.load()
    query_answers.load()
