from pydantic import BaseModel

from app.api.deps import SessionDep
from fastapi import APIRouter

from app.retriever.query_answers import query_answers

router = APIRouter(prefix="/chat", tags=["chat"])


class BaseResponse(BaseModel):
    code: str
    msg: str = ""


@router.get("/{question}", response_model=BaseResponse)
async def query(question: str):
    """
    提问
    :param question:
    :return:
    """
    response_model = BaseResponse(code="000000", msg="success")
    response_model.msg = await query_answers.query(question)
    return response_model
