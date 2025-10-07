from typing import Any, List

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep, CurrentUser

from app.db_model import UserPublic, UserCreate, UserUpdateMe, Title, QueryConfigCreate, LoadConfigCreate, \
    LoadConfigBase
from app.db_option import get_user_by_email, create_user, get_titles_by_user, create_llm_query_config, \
    create_load_config, update_user_config
from app.retriever.llm_manager import LLmManager, global_query_llm_cache
from app.retriever.query_answers import QueryAnswers
from app.utils.user_base_model import LLmConfig

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/register", response_model=UserPublic)
def register_user(*, session: SessionDep, user_in: UserCreate):
    """
    注册新用户
    :param session:
    :param user_in:
    :return:
    """
    user = get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(session=session, user_create=user_in)
    # 创建默认的 query_llm 配置
    default_query_llm_config = QueryConfigCreate(config_name="default", user_id=user.id, QueryConfigBase=LLmConfig())
    default_query_llm_config = create_llm_query_config(session=session, query_llm_config=default_query_llm_config)

    # 创建默认的 load_llm 配置
    default_load_base_config = LoadConfigBase()
    default_load_llm_config = LoadConfigCreate(config_name="default", user_id=user.id,
                                               config_hash=str(hash(default_load_base_config)),
                                               LoadConfigBase=default_load_base_config)
    load_config = create_load_config(session=session, load_llm_config=default_load_llm_config)
    print(f'load_config: {load_config}')
    user.cur_llm_config_id = default_query_llm_config.id
    update_user_config(session=session, user=user)

    # 创建query llm对象
    query_llm = LLmManager(user_id=user.id)
    query_llm.load_llm(session=session)
    global_query_llm_cache[user.id] = query_llm
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
        *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    更新 name 和 email.
    """

    if user_in.email:
        existing_user = get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.get("/titles", response_model=List[Title])
def get_titles(session: SessionDep, current_user: CurrentUser):
    """
    获取当前用户下所有title
    :param session:
    :param current_user:
    :return: List[Title]
    """
    list_titles = get_titles_by_user(session=session, user_id=current_user.id)
    return list_titles


@router.delete("/me")
def delete_account(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    注销账号
    :param session:
    :param current_user:
    :return:
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return {"msg": "Successfully deleted"}

