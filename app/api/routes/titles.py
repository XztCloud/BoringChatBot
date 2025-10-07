import uuid
from typing import List

from app.api.deps import SessionDep, CurrentUser, CurrentTitle
from fastapi import APIRouter, HTTPException

from app.db_model import TitleCreate, TitleUpdate, TitleInfoUpdate, LoadConfig
from app.db_option import get_title_by_name, create_title, get_title_by_id, get_all_files_by_title_id, \
    get_load_config_by_user_id

router = APIRouter(prefix="/titles", tags=["titles"])


@router.post("/create")
def create_title_request(
        *, session: SessionDep, title_create: TitleCreate, current_user: CurrentUser):
    """
    Create a new title
    :param session:
    :param title_create:
    :param current_user:
    :return:
    """
    title = get_title_by_name(session=session, user_id=current_user.id, title_name=title_create.title_name)
    if title:
        raise HTTPException(
            status_code=409, detail="Title with this name already exists"
        )
    title = TitleUpdate(**title_create.dict(), user_id=current_user.id)
    print(f'title: {title}')
    # 获取当前用户下第一个 load_llm_config id
    load_config = get_load_config_by_user_id(session=session, user_id=current_user.id)
    load_config_id = load_config.id if load_config else None
    print(f'load_config_id: {load_config_id}')
    title = create_title(session=session, title_create=title, load_config_id=load_config_id)
    return title


@router.patch("/me")
def update_me(*, session: SessionDep, new_title: TitleInfoUpdate, current_user: CurrentUser):
    """
    更新当前title信息
    :param session:
    :param new_title:
    :param current_user:
    :return:
    """
    cur_title = get_title_by_id(session=session, user_id=current_user.id, title_id=new_title.id)
    if not cur_title:
        raise HTTPException(
            status_code=404, detail="Title with this id not exists"
        )

    if new_title.title_name:
        existing_title = get_title_by_name(session=session, user_id=current_user.id, title_name=new_title.title_name)
        if existing_title and existing_title.id != new_title.id:
            raise HTTPException(
                status_code=409, detail="Title with this name already exists"
            )
    title_in = TitleCreate(**new_title.dict())
    title_data = title_in.model_dump(exclude_unset=True)
    cur_title.sqlmodel_update(title_data)
    session.add(cur_title)
    session.commit()
    session.refresh(cur_title)
    return cur_title


@router.get("/{title_id}/files")
def get_files_by_title_id(*, session: SessionDep, cur_title: CurrentTitle) -> List[str]:
    """
    获取当前title下所有文件
    :param session:
    :param cur_title:
    :return:
    """
    files = get_all_files_by_title_id(session=session, title_id=cur_title.id)
    return files


@router.delete("/{title_id}")
def delete_title(*, session: SessionDep, cur_title: CurrentTitle):
    """
    删除title
    :param cur_title:
    :param session:
    :return:
    """
    session.delete(cur_title)
    session.commit()
    return {"msg": "success"}