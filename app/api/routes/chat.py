from starlette.responses import StreamingResponse
from fastapi import APIRouter

from app.retriever.query_answers import query_answers
from app.utils.user_base_model import BaseResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/once/{question}", response_model=BaseResponse)
async def query(question: str):
    """
    提问
    :param question:
    :return:
    """
    response_model = BaseResponse(code="000000", msg="success")
    response_model.msg = await query_answers.query(question)
    return response_model


@router.get("/stream/{question}")
async def query_stream(question: str):
    """
    提问，流式回答
    :param question:
    :return: StreamingResponse
    """
    return StreamingResponse(query_answers.event_generator(question), media_type="text/event-stream")
