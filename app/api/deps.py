from typing import Generator, Annotated

from fastapi import Depends
from pydantic import PostgresDsn
from pydantic_core import MultiHostUrl
from sqlalchemy import create_engine
from sqlmodel import Session


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


SessionDep = Annotated[Session, Depends(get_db)]
