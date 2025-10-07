import uuid
from typing import Generator, Annotated

import jwt
from fastapi import Depends, HTTPException, status, Path
from fastapi.security import OAuth2PasswordBearer
from pydantic import PostgresDsn
from pydantic_core import MultiHostUrl
from sqlalchemy import create_engine
from sqlmodel import Session, select

from app.db_model import User, TokenPayload, Title, File
from app.security import ALGORITHM
from app.settings import settings


# type: ignore[prop-decorator]
def get_db_url() -> PostgresDsn:
    result = MultiHostUrl.build(
        scheme='postgresql+psycopg',
        username='postgres',
        password='123456',
        host='127.0.0.1',
        port=5432,
        path='boring_chatbot',
    )
    print(f'result: {result}')
    return result


engine = create_engine(str(get_db_url()))


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login/token")

SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    """
    通过token获取当前用户，token由{"exp": 截止时间戳, "sub": str(user.id)} 生成
    :param session:
    :param token:
    :return:
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        print(f'payload: {payload}')
        token_data = TokenPayload(**payload)
        print(f'token_data: {token_data}')
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    # token_data.sub 的值是user.id
    user = session.get(User, token_data.sub)
    print(f'type user is {type(user)}')
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_title(session: SessionDep, current_user: CurrentUser, title_id: uuid.UUID = Path(...)) -> Title:
    """
    通过title_id获取当前title，title_id由uuid生成
    :param session:
    :param current_user:
    :param title_id: Path表示参数在请求路径中，...表示必传
    :return:
    """
    statement = select(Title).where(
        Title.user_id == current_user.id,
        Title.id == title_id
    )
    title = session.exec(statement).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    return title


CurrentTitle = Annotated[Title, Depends(get_current_title)]


def get_current_file(session: SessionDep, current_title: CurrentTitle, file_id: uuid.UUID = Path(...)) -> File:
    """
    通过file_id获取当前file，file_id由uuid生成
    :param session:
    :param current_title:
    :param file_id: Path表示参数在请求路径中，...表示必传
    :return:
    """
    statement = select(File).where(
        File.title_id == current_title.id,
        File.id == file_id
    )
    file = session.exec(statement).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


CurrentFile = Annotated[File, Depends(get_current_file)]
