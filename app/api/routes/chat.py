import uuid

from app.api.deps import SessionDep, CurrentUser, CurrentTitle
from starlette.responses import StreamingResponse
from fastapi import APIRouter

from app.retriever.query_answers import global_query_answers_cache, QueryAnswers
from app.utils.user_base_model import BaseResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def get_query_answers(current_user: CurrentUser, current_title: CurrentTitle):
    """
    获取查询对象
    :param current_title:
    :param current_user:
    :return:
    """
    user_id = current_user.id
    if user_id in global_query_answers_cache:
        query_answers = global_query_answers_cache[user_id]
        query_answers.reload_if_needed()
    else:
        query_answers = QueryAnswers(user_id=user_id, title_id=current_title.id)
        query_answers.load()
        global_query_answers_cache[user_id] = query_answers
    return query_answers


@router.get("/once/{title_id}/{question}", response_model=BaseResponse)
async def query(current_user: CurrentUser, current_title: CurrentTitle, question: str):
    """
    提问
    :param current_title:
    :param current_user:
    :param question:
    :return:
    """
    response_model = BaseResponse(code="000000", msg="success")
    query_answers = get_query_answers(current_user=current_user, current_title=current_title)
    response_model.msg = await query_answers.query(question)
    return response_model


@router.get("/stream/{title_id}/{question}")
async def query_stream(current_user: CurrentUser, current_title: CurrentTitle, question: str):
    """
    提问，流式回答
    :param current_title:
    :param current_user:
    :param question:
    :return: StreamingResponse
    """
    query_answers = get_query_answers(current_user=current_user, current_title=current_title)

    return StreamingResponse(query_answers.event_generator(question), media_type="text/event-stream")
