import os
import hashlib
import uuid
from typing import List, Optional
from sqlmodel import select, Session
from app.api.deps import SessionDep, engine
from app.db_model import File, FileCreate, DocumentChunk, User, UserCreate, Title, TitleCreate, TitleUpdate, \
    QueryConfig, QueryConfigCreate, LoadConfigCreate, LoadConfig
from app.security import get_password_hash
from app.utils.user_base_model import LLmConfig


def get_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def calculate_file_hash(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    计算大文件的 SHA256 哈希
    :param file_path: 文件路径
    :param chunk_size: 每次读取的字节数，默认 1MB
    :return: 十六进制哈希字符串
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_file(session: SessionDep, file_create: FileCreate):
    db_obj = File.model_validate(file_create)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_file_by_hash(*, session: SessionDep, file_hash: str, title_id: uuid.UUID) -> File | None:
    statement = select(File).where(File.file_hash == file_hash, File.title_id == title_id)
    session_file = session.exec(statement).first()
    return session_file


def get_file_by_name(*, session: SessionDep, filename: str, title_id: uuid.UUID) -> File | None:
    statement = select(File).where(File.filename == filename, File.title_id == title_id)
    session_file = session.exec(statement).first()
    return session_file


def get_all_files_by_title_id(session: SessionDep, title_id: uuid.UUID) -> List[str]:
    statement = select(File).where(File.title_id == title_id)
    session_files = session.exec(statement).all()
    file_name_list = []
    for session_file in session_files:
        file_name_list.append(os.path.basename(session_file.filename))
    return file_name_list


def save_doc_chunk(doc_id_list: List[str], parent_doc_id: int) -> None:
    with Session(engine) as session:
        for doc_id in doc_id_list:
            chunk = DocumentChunk(chroma_doc_id=doc_id, document_id=parent_doc_id)
            session.add(chunk)
        session.commit()


def create_user(*, session: SessionDep, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user_config(*, session: SessionDep, user: User) -> User:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def get_user_by_id(*, session: Session, user_id: uuid.UUID) -> User | None:
    statement = select(User).where(User.id == user_id)
    session_user = session.exec(statement).first()
    return session_user


def create_title(*, session: SessionDep, title_create: TitleUpdate, load_config_id: Optional[uuid.UUID]) -> Title:
    db_obj = Title.model_validate(title_create, update={"load_config_id": load_config_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_title_by_name(*, session: SessionDep, user_id: uuid.UUID, title_name: str) -> Title | None:
    statement = select(Title).where(
        Title.user_id == user_id,
        Title.title_name == title_name
    )
    session_title = session.exec(statement).first()
    return session_title


def get_title_by_id(*, session: SessionDep, user_id: uuid.UUID, title_id: uuid.UUID) -> Title | None:
    statement = select(Title).where(
        Title.user_id == user_id,
        Title.id == title_id
    )
    session_title = session.exec(statement).first()
    return session_title


def get_titles_by_user(*, session: SessionDep, user_id: uuid.UUID) -> List[Title]:
    statement = select(Title).where(Title.user_id == user_id)
    session_titles = session.exec(statement).all()
    return session_titles


def create_llm_query_config(*, session: SessionDep, query_llm_config: QueryConfigCreate) -> LLmConfig:
    db_obj = QueryConfig.model_validate(query_llm_config)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_load_config(*, session: SessionDep, load_llm_config: LoadConfigCreate) -> LoadConfig:
    db_obj = LoadConfig.model_validate(load_llm_config)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_load_config_by_user_id(*, session: SessionDep, user_id: uuid.UUID) -> LoadConfig | None:
    statement = select(LoadConfig).where(LoadConfig.user_id == user_id)
    session_load_config = session.exec(statement).first()
    return session_load_config


def upload_query_config(*, session: SessionDep, user_id: uuid.UUID, query_config: LLmConfig) -> QueryConfig:
    db_obj = QueryConfig.model_validate(query_config, update={"user_id": user_id})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_query_config_by_id(*, session: SessionDep, user_id: uuid.UUID, query_config_id: uuid.UUID) -> QueryConfig | None:
    statement = select(QueryConfig).where(
        QueryConfig.user_id == user_id,
        QueryConfig.id == query_config_id
        )
    session_query_config = session.exec(statement).first()
    return session_query_config


def get_all_query_config_by_user_id(*, session: SessionDep, user_id: uuid.UUID) -> List[QueryConfig]:
    statement = select(QueryConfig).where(QueryConfig.user_id == user_id)
    session_query_configs = session.exec(statement).all()
    return session_query_configs


def get_load_config_by_id(session, user_id, load_config_id):
    statement = select(LoadConfig).where(
        LoadConfig.user_id == user_id,
        LoadConfig.id == load_config_id
    )
    return session.exec(statement).first()


def get_all_load_config_by_user_id(*, session: SessionDep, user_id) -> List[LoadConfig]:
    statement = select(LoadConfig).where(LoadConfig.user_id == user_id)
    session_load_configs = session.exec(statement).all()
    return session_load_configs
