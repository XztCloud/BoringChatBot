import uuid

from app.api.deps import SessionDep, CurrentUser
from fastapi import APIRouter, HTTPException
from app.api.routes.info import SUPPER_USER_ID
from app.db_model import QueryConfigCreate, LoadConfigCreate, LoadConfigUserUpdate, LoadConfigBase
from app.db_option import upload_query_config, get_query_config_by_id, get_all_query_config_by_user_id, \
    create_load_config, get_load_config_by_id, get_all_load_config_by_user_id
from app.utils.user_base_model import TaskConfig, LLmConfig

router = APIRouter(prefix="/configure", tags=["configure"])


@router.post("/query/upload")
async def send_config(session: SessionDep, current_user: CurrentUser, config: LLmConfig):
    """
    发送配置信息
    :param current_user:
    :param session:
    :param config:
    :return:
    """
    query_llm_config = upload_query_config(session=session, user_id=current_user.id, query_config=config)
    return query_llm_config


@router.delete("/query/delete/{query_config_id}")
async def delete_query(session: SessionDep, current_user: CurrentUser, query_config_id: uuid.UUID):
    """
    删除查询
    :param query_config_id:
    :param session:
    :param current_user:
    :return:
    """
    try:
        query_config = get_query_config_by_id(session=session, user_id=current_user.id, query_config_id=query_config_id)
        if query_config is None:
            raise HTTPException(status_code=404, detail="query_config not found")
        session.delete(query_config)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "success"}


@router.get("/query/list")
async def get_query_list(session: SessionDep, current_user: CurrentUser):
    """
    获取查询配置列表
    :param session:
    :param current_user:
    :return:
    """
    return get_all_query_config_by_user_id(session=session, user_id=current_user.id)


@router.post("/load_config/upload")
async def upload_load_config(session: SessionDep, current_user: CurrentUser, config: LoadConfigUserUpdate):
    """
    上传加载配置
    :param session:
    :param current_user:
    :param config:
    :return:
    """
    load_config_base = LoadConfigBase(**config.dict())
    load_config_create = LoadConfigCreate(**config.dict(), user_id=current_user.id,
                                          config_hash=str(hash(load_config_base)))
    load_config = create_load_config(session=session, load_llm_config=load_config_create)
    return load_config


@router.delete("/load_config/delete/{load_config_id}")
async def delete_load_config(session: SessionDep, current_user: CurrentUser, load_config_id: uuid.UUID):
    """
    删除加载配置
    :param session:
    :param current_user:
    :param load_config_id:
    :return:
    """
    load_config = get_load_config_by_id(session=session, user_id=current_user.id, load_config_id=load_config_id)
    session.delete(load_config)
    session.commit()
    return {"message": "success"}


@router.get("/load_config/list")
async def get_load_config_list(session: SessionDep, current_user: CurrentUser):
    """
    获取加载配置列表
    :param session:
    :param current_user:
    :return:
    """
    return get_all_load_config_by_user_id(session=session, user_id=current_user.id)
